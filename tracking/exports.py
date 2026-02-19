"""
Export functionality for CSU tracking data.
Generates CSV and PDF exports suitable for healthcare providers.

Designed for NHS and clinical use with:
- EAACI/GA²LEN/EuroGuiDerm guideline compliance
- ICD-10/SNOMED-CT coding references
- Treatment response analysis
- Clinical decision support indicators
"""

import csv
import io
import hashlib
from datetime import date, timedelta
from typing import Optional, List, Dict, Tuple
from collections import Counter

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether, ListFlowable, ListItem
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle, Path, Group
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker

from .models import DailyEntry


class CSUExporter:
    """
    Handles export of CSU tracking data in various formats.
    
    Designed for NHS and healthcare provider clinical use with:
    - EAACI/GA²LEN/EuroGuiDerm guideline compliance  
    - Disease severity classification per international standards
    - Treatment response analysis
    - Clinical decision support indicators
    """
    
    # Clinical reference codes
    ICD10_CODE = "L50.1"  # Chronic Urticaria
    ICD10_DESCRIPTION = "Idiopathic urticaria"
    SNOMED_CODE = "402408009"  # Chronic spontaneous urticaria
    
    ITCH_LABELS = {
        0: "None",
        1: "Mild",
        2: "Moderate", 
        3: "Severe",
    }
    
    ITCH_CLINICAL = {
        0: "No pruritus",
        1: "Present but not annoying or troublesome",
        2: "Troublesome but does not interfere with normal daily activity or sleep",
        3: "Severe pruritus, interferes with normal daily activity or sleep",
    }
    
    HIVE_LABELS = {
        0: "None",
        1: "Mild (<20)",
        2: "Moderate (20-50)",
        3: "Severe (>50)",
    }
    
    HIVE_CLINICAL = {
        0: "No wheals",
        1: "Fewer than 20 wheals per 24 hours",
        2: "20-50 wheals per 24 hours",
        3: "More than 50 wheals per 24 hours or large confluent areas",
    }
    
    # UAS7 categories per EAACI/GA²LEN/EuroGuiDerm guidelines
    UAS7_CATEGORIES = [
        (0, 6, "Well Controlled", "#22C55E"),
        (7, 15, "Mild Activity", "#84CC16"),
        (16, 27, "Moderate Activity", "#F59E0B"),
        (28, 42, "Severe Activity", "#EF4444"),
    ]
    
    # Clinical guidance per disease severity
    CLINICAL_GUIDANCE = {
        "Well Controlled": {
            "description": "Disease well controlled on current therapy",
            "recommendation": "Continue current treatment. Consider step-down if stable for ≥3 months.",
            "review_interval": "3-6 months",
        },
        "Mild Activity": {
            "description": "Mild disease activity despite current therapy",
            "recommendation": "Consider optimising H1-antihistamine dose up to 4x licensed dose (off-label).",
            "review_interval": "4-8 weeks",
        },
        "Moderate Activity": {
            "description": "Moderate disease activity requiring treatment escalation",
            "recommendation": "If not responding to updosed H1-antihistamines, consider add-on therapy (omalizumab).",
            "review_interval": "2-4 weeks",
        },
        "Severe Activity": {
            "description": "Severe uncontrolled disease",
            "recommendation": "Urgent specialist referral recommended. Consider omalizumab or cyclosporine if not already initiated.",
            "review_interval": "1-2 weeks",
        },
    }
    
    # Quality of life impact thresholds (based on CU-Q2oL correlation with UAS7)
    QOL_THRESHOLDS = {
        "minimal": (0, 6),
        "mild": (7, 15),
        "moderate": (16, 27),
        "severe": (28, 42),
    }
    
    # QOL impact descriptions
    QOL_DESCRIPTIONS = {
        "minimal": {
            "impact": "Minimal Impact",
            "description": "Disease has minimal impact on daily activities and quality of life.",
            "domains": ["Sleep: Likely unaffected", "Daily activities: Minimal disruption", "Emotional wellbeing: Generally stable"],
        },
        "mild": {
            "impact": "Mild Impact",
            "description": "Some impact on quality of life, particularly during symptom flares.",
            "domains": ["Sleep: Occasionally disturbed", "Daily activities: Minor adjustments needed", "Emotional wellbeing: Mild frustration possible"],
        },
        "moderate": {
            "impact": "Moderate Impact",
            "description": "Noticeable impact on daily life. May affect work, social activities, and sleep.",
            "domains": ["Sleep: Frequently disturbed", "Daily activities: Regular modifications required", "Emotional wellbeing: Anxiety or stress common"],
        },
        "severe": {
            "impact": "Severe Impact",
            "description": "Significant burden on quality of life. Substantial interference with daily functioning.",
            "domains": ["Sleep: Severely impaired", "Daily activities: Major limitations", "Emotional wellbeing: High psychological burden"],
        },
    }
    
    def __init__(self, user, start_date: date, end_date: date, options: dict = None):
        self.user = user
        self.start_date = start_date
        self.end_date = end_date
        self.options = options or {}
        
        # Export options
        self.anonymize = self.options.get("anonymize", False)
        self.include_notes = self.options.get("include_notes", True)
        self.include_antihistamine = self.options.get("include_antihistamine", True)
        self.include_breakdown = self.options.get("include_breakdown", True)
        self.include_clinical_guidance = self.options.get("include_clinical_guidance", True)
        self.report_type = self.options.get("report_type", "quick")  # 'quick' or 'detailed'
        
        # Fetch data
        self.entries = self._fetch_entries()
        self.stats = self._calculate_stats()
        self.patterns = self._analyze_patterns()
        self.treatment_analysis = self._analyze_treatment_response()
        self.qol_assessment = self._assess_quality_of_life()
    
    def _fetch_entries(self):
        """Fetch entries for the date range."""
        return list(DailyEntry.objects.filter(
            user=self.user,
            date__gte=self.start_date,
            date__lte=self.end_date,
        ).order_by("date"))
    
    def _calculate_stats(self):
        """Calculate summary statistics."""
        total_days = (self.end_date - self.start_date).days + 1
        logged_days = len(self.entries)
        missing_days = total_days - logged_days
        adherence_pct = (logged_days / total_days * 100) if total_days > 0 else 0
        
        if self.entries:
            scores = [e.score for e in self.entries]
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            
            itch_scores = [e.itch_score for e in self.entries if e.itch_score is not None]
            hive_scores = [e.hive_count_score for e in self.entries if e.hive_count_score is not None]
            
            avg_itch = sum(itch_scores) / len(itch_scores) if itch_scores else None
            avg_hives = sum(hive_scores) / len(hive_scores) if hive_scores else None
            
            antihistamine_days = sum(1 for e in self.entries if e.took_antihistamine)
        else:
            avg_score = min_score = max_score = 0
            avg_itch = avg_hives = None
            antihistamine_days = 0
        
        # Calculate weekly UAS7 scores
        weekly_uas7 = self._calculate_weekly_uas7()
        
        return {
            "total_days": total_days,
            "logged_days": logged_days,
            "missing_days": missing_days,
            "adherence_pct": adherence_pct,
            "avg_score": avg_score,
            "min_score": min_score,
            "max_score": max_score,
            "avg_itch": avg_itch,
            "avg_hives": avg_hives,
            "antihistamine_days": antihistamine_days,
            "weekly_uas7": weekly_uas7,
        }
    
    def _calculate_weekly_uas7(self):
        """Calculate UAS7 for complete weeks in the range.
        
        If the user has a biologic injection date, weeks are aligned to
        start on the injection weekday.  Otherwise falls back to
        Sunday-anchored calendar weeks.
        """
        from .utils import get_injection_weekday

        weekly_scores = []
        entry_by_date = {e.date: e for e in self.entries}

        # Determine which weekday starts the tracking week
        injection_weekday = get_injection_weekday(self.user)

        if injection_weekday is not None:
            # Align to injection weekday
            current = self.start_date
            while current.weekday() != injection_weekday:
                current -= timedelta(days=1)
        else:
            # Fall back to Sunday-anchored weeks
            current = self.start_date
            while current.weekday() != 6:  # 6 = Sunday
                current -= timedelta(days=1)
        
        while current <= self.end_date:
            week_end = current + timedelta(days=6)
            week_entries = []
            
            for i in range(7):
                day = current + timedelta(days=i)
                if day in entry_by_date:
                    week_entries.append(entry_by_date[day])
            
            if len(week_entries) == 7:
                uas7 = sum(e.score for e in week_entries)
                weekly_scores.append({
                    "week_start": current,
                    "week_end": week_end,
                    "uas7": uas7,
                    "complete": True,
                })
            elif week_entries:
                uas7 = sum(e.score for e in week_entries)
                weekly_scores.append({
                    "week_start": current,
                    "week_end": week_end,
                    "uas7": uas7,
                    "complete": False,
                    "days_logged": len(week_entries),
                })
            
            current += timedelta(days=7)
        
        return weekly_scores
    
    def _analyze_patterns(self) -> Dict:
        """Analyze symptom patterns for clinical insights."""
        if not self.entries:
            return {}
        
        # Day of week analysis
        weekday_scores = {i: [] for i in range(7)}
        for entry in self.entries:
            weekday_scores[entry.date.weekday()].append(entry.score)
        
        weekday_averages = {}
        for day, scores in weekday_scores.items():
            if scores:
                weekday_averages[day] = sum(scores) / len(scores)
        
        # Find worst and best days
        if weekday_averages:
            worst_day = max(weekday_averages.items(), key=lambda x: x[1])
            best_day = min(weekday_averages.items(), key=lambda x: x[1])
        else:
            worst_day = best_day = None
        
        # Score distribution
        score_distribution = Counter(e.score for e in self.entries)
        
        # Symptom-free days (score = 0)
        symptom_free_days = sum(1 for e in self.entries if e.score == 0)
        symptom_free_pct = (symptom_free_days / len(self.entries) * 100) if self.entries else 0
        
        # Severe days (score >= 5)
        severe_days = sum(1 for e in self.entries if e.score >= 5)
        severe_pct = (severe_days / len(self.entries) * 100) if self.entries else 0
        
        # Trend analysis (compare first half vs second half)
        mid_point = len(self.entries) // 2
        if mid_point > 0:
            first_half_avg = sum(e.score for e in self.entries[:mid_point]) / mid_point
            second_half_avg = sum(e.score for e in self.entries[mid_point:]) / (len(self.entries) - mid_point)
            trend = "improving" if second_half_avg < first_half_avg else "worsening" if second_half_avg > first_half_avg else "stable"
            trend_change = second_half_avg - first_half_avg
        else:
            first_half_avg = second_half_avg = self.stats["avg_score"]
            trend = "insufficient_data"
            trend_change = 0
        
        # Consecutive symptom-free days (longest streak)
        max_streak = current_streak = 0
        for entry in self.entries:
            if entry.score == 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        # Flare analysis (consecutive days with score >= 4)
        flare_episodes = []
        current_flare = []
        for entry in self.entries:
            if entry.score >= 4:
                current_flare.append(entry)
            else:
                if len(current_flare) >= 2:  # At least 2 consecutive days
                    flare_episodes.append({
                        "start": current_flare[0].date,
                        "end": current_flare[-1].date,
                        "duration": len(current_flare),
                        "peak_score": max(e.score for e in current_flare),
                        "avg_score": sum(e.score for e in current_flare) / len(current_flare),
                    })
                current_flare = []
        # Check final flare
        if len(current_flare) >= 2:
            flare_episodes.append({
                "start": current_flare[0].date,
                "end": current_flare[-1].date,
                "duration": len(current_flare),
                "peak_score": max(e.score for e in current_flare),
                "avg_score": sum(e.score for e in current_flare) / len(current_flare),
            })
        
        return {
            "weekday_averages": weekday_averages,
            "worst_day": worst_day,
            "best_day": best_day,
            "score_distribution": dict(score_distribution),
            "symptom_free_days": symptom_free_days,
            "symptom_free_pct": symptom_free_pct,
            "severe_days": severe_days,
            "severe_pct": severe_pct,
            "trend": trend,
            "trend_change": trend_change,
            "first_half_avg": first_half_avg,
            "second_half_avg": second_half_avg,
            "longest_remission_streak": max_streak,
            "flare_episodes": flare_episodes,
        }
    
    def _analyze_treatment_response(self) -> Dict:
        """Analyze antihistamine treatment response."""
        if not self.entries or not self.include_antihistamine:
            return {}
        
        with_antihistamine = [e for e in self.entries if e.took_antihistamine]
        without_antihistamine = [e for e in self.entries if not e.took_antihistamine]
        
        if with_antihistamine:
            avg_with = sum(e.score for e in with_antihistamine) / len(with_antihistamine)
            itch_with = [e.itch_score for e in with_antihistamine if e.itch_score is not None]
            hives_with = [e.hive_count_score for e in with_antihistamine if e.hive_count_score is not None]
            avg_itch_with = sum(itch_with) / len(itch_with) if itch_with else None
            avg_hives_with = sum(hives_with) / len(hives_with) if hives_with else None
        else:
            avg_with = avg_itch_with = avg_hives_with = None
        
        if without_antihistamine:
            avg_without = sum(e.score for e in without_antihistamine) / len(without_antihistamine)
            itch_without = [e.itch_score for e in without_antihistamine if e.itch_score is not None]
            hives_without = [e.hive_count_score for e in without_antihistamine if e.hive_count_score is not None]
            avg_itch_without = sum(itch_without) / len(itch_without) if itch_without else None
            avg_hives_without = sum(hives_without) / len(hives_without) if hives_without else None
        else:
            avg_without = avg_itch_without = avg_hives_without = None
        
        # Calculate treatment effect
        if avg_with is not None and avg_without is not None:
            score_reduction = avg_without - avg_with
            reduction_pct = (score_reduction / avg_without * 100) if avg_without > 0 else 0
            
            # Classify response
            if reduction_pct >= 50:
                response_category = "Good Response"
            elif reduction_pct >= 25:
                response_category = "Partial Response"
            elif reduction_pct > 0:
                response_category = "Minimal Response"
            else:
                response_category = "No Response / Refractory"
        else:
            score_reduction = reduction_pct = 0
            response_category = "Insufficient Data"
        
        # Adherence to antihistamine
        if self.entries:
            adherence_rate = len(with_antihistamine) / len(self.entries) * 100
        else:
            adherence_rate = 0
        
        return {
            "days_with_antihistamine": len(with_antihistamine),
            "days_without_antihistamine": len(without_antihistamine),
            "avg_score_with": avg_with,
            "avg_score_without": avg_without,
            "avg_itch_with": avg_itch_with,
            "avg_itch_without": avg_itch_without,
            "avg_hives_with": avg_hives_with,
            "avg_hives_without": avg_hives_without,
            "score_reduction": score_reduction,
            "reduction_pct": reduction_pct,
            "response_category": response_category,
            "adherence_rate": adherence_rate,
        }
    
    def _assess_quality_of_life(self) -> dict:
        """
        Assess quality of life impact based on actual QoL data if available,
        otherwise estimate from symptom data.
        
        Uses actual QoL survey responses (qol_sleep, qol_daily_activities, 
        qol_appearance, qol_mood) when available. Falls back to UAS7 correlation
        with validated QoL instruments (CU-Q2oL, DLQI) for estimation.
        """
        if not self.entries:
            return None
        
        # Check for actual QoL data
        qol_entries = [e for e in self.entries if e.qol_score is not None]
        has_actual_qol_data = len(qol_entries) > 0
        
        if has_actual_qol_data:
            # Use actual QoL data
            avg_qol_score = sum(e.qol_score for e in qol_entries) / len(qol_entries)
            qol_percentage = (avg_qol_score / 16) * 100  # 16 is max score (4 questions x 4 max each)
            
            # Individual domain averages
            sleep_scores = [e.qol_sleep for e in qol_entries if e.qol_sleep is not None]
            activity_scores = [e.qol_daily_activities for e in qol_entries if e.qol_daily_activities is not None]
            appearance_scores = [e.qol_appearance for e in qol_entries if e.qol_appearance is not None]
            mood_scores = [e.qol_mood for e in qol_entries if e.qol_mood is not None]
            
            avg_sleep = sum(sleep_scores) / len(sleep_scores) if sleep_scores else None
            avg_activity = sum(activity_scores) / len(activity_scores) if activity_scores else None
            avg_appearance = sum(appearance_scores) / len(appearance_scores) if appearance_scores else None
            avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else None
            
            # Determine QoL category from actual score (0-16 scale)
            if avg_qol_score <= 3:
                qol_category = "minimal"
            elif avg_qol_score <= 7:
                qol_category = "mild"
            elif avg_qol_score <= 11:
                qol_category = "moderate"
            else:
                qol_category = "severe"
            
            # Map scores to descriptive impact
            def score_to_impact(score):
                if score is None:
                    return "Not assessed"
                if score <= 0.5:
                    return "Not affected"
                elif score <= 1.5:
                    return "Slightly affected"
                elif score <= 2.5:
                    return "Moderately affected"
                elif score <= 3.5:
                    return "Significantly affected"
                else:
                    return "Extremely affected"
            
            sleep_impact = score_to_impact(avg_sleep)
            activity_impact = score_to_impact(avg_activity)
            appearance_impact = score_to_impact(avg_appearance)
            mood_impact = score_to_impact(avg_mood)
            
            qol_info = self.QOL_DESCRIPTIONS.get(qol_category, self.QOL_DESCRIPTIONS["minimal"])
            
            # Estimate DLQI-equivalent score from actual QoL data
            # Our QoL scale is 0-16, DLQI is 0-30; rough linear mapping
            estimated_dlqi = min(30, avg_qol_score * 1.875)
            
            if estimated_dlqi <= 1:
                dlqi_interpretation = "No effect on quality of life"
            elif estimated_dlqi <= 5:
                dlqi_interpretation = "Small effect on quality of life"
            elif estimated_dlqi <= 10:
                dlqi_interpretation = "Moderate effect on quality of life"
            elif estimated_dlqi <= 20:
                dlqi_interpretation = "Very large effect on quality of life"
            else:
                dlqi_interpretation = "Extremely large effect on quality of life"
            
            return {
                "category": qol_category,
                "impact": qol_info["impact"],
                "description": qol_info["description"],
                "data_source": "actual",
                "entries_with_qol": len(qol_entries),
                "total_entries": len(self.entries),
                "avg_qol_score": avg_qol_score,
                "qol_percentage": qol_percentage,
                "domains": {
                    "sleep": {"score": avg_sleep, "impact": sleep_impact},
                    "daily_activities": {"score": avg_activity, "impact": activity_impact},
                    "appearance": {"score": avg_appearance, "impact": appearance_impact},
                    "mood": {"score": avg_mood, "impact": mood_impact},
                },
                "sleep_impact": sleep_impact,
                "activity_impact": activity_impact,
                "estimated_dlqi": estimated_dlqi,
                "dlqi_interpretation": dlqi_interpretation,
            }
        
        # Fall back to estimation from UAS7 correlation
        # Calculate average weekly UAS7 for QoL estimation
        complete_weeks = [w for w in self.stats.get("weekly_uas7", []) if w.get("complete")]
        if complete_weeks:
            avg_uas7 = sum(w["uas7"] for w in complete_weeks) / len(complete_weeks)
        else:
            # Estimate from daily average
            avg_uas7 = self.stats["avg_score"] * 7
        
        # Determine QoL category
        qol_category = "minimal"
        for category, (min_val, max_val) in self.QOL_THRESHOLDS.items():
            if min_val <= avg_uas7 <= max_val:
                qol_category = category
                break
        else:
            if avg_uas7 > 42:
                qol_category = "severe"
        
        qol_info = self.QOL_DESCRIPTIONS.get(qol_category, self.QOL_DESCRIPTIONS["minimal"])
        
        # Calculate specific impact indicators
        sleep_impact = "Unknown"
        activity_impact = "Unknown"
        if self.patterns:
            severe_pct = self.patterns.get("severe_pct", 0)
            if severe_pct >= 30:
                sleep_impact = "Severely affected"
                activity_impact = "Major limitations"
            elif severe_pct >= 15:
                sleep_impact = "Frequently disturbed"
                activity_impact = "Moderate limitations"
            elif severe_pct >= 5:
                sleep_impact = "Occasionally disturbed"
                activity_impact = "Minor adjustments"
            else:
                sleep_impact = "Generally unaffected"
                activity_impact = "Minimal impact"
        
        # Estimate DLQI-equivalent score (rough correlation)
        # DLQI correlates ~0.6 with UAS7; rough estimation: DLQI ≈ UAS7 * 0.5
        estimated_dlqi = min(30, avg_uas7 * 0.5)
        
        if estimated_dlqi <= 1:
            dlqi_interpretation = "No effect on quality of life"
        elif estimated_dlqi <= 5:
            dlqi_interpretation = "Small effect on quality of life"
        elif estimated_dlqi <= 10:
            dlqi_interpretation = "Moderate effect on quality of life"
        elif estimated_dlqi <= 20:
            dlqi_interpretation = "Very large effect on quality of life"
        else:
            dlqi_interpretation = "Extremely large effect on quality of life"
        
        return {
            "category": qol_category,
            "impact": qol_info["impact"],
            "description": qol_info["description"],
            "data_source": "estimated",
            "domains": qol_info["domains"],
            "avg_uas7": avg_uas7,
            "sleep_impact": sleep_impact,
            "activity_impact": activity_impact,
            "estimated_dlqi": estimated_dlqi,
            "dlqi_interpretation": dlqi_interpretation,
        }
    
    def _get_current_disease_category(self) -> Tuple[str, str]:
        """Get current disease activity category based on most recent complete week."""
        complete_weeks = [w for w in self.stats["weekly_uas7"] if w["complete"]]
        if complete_weeks:
            latest_uas7 = complete_weeks[-1]["uas7"]
            for min_val, max_val, label, color in self.UAS7_CATEGORIES:
                if min_val <= latest_uas7 <= max_val:
                    return label, color
        return "Unknown", "#6B7280"
    
    def _generate_report_hash(self) -> str:
        """Generate a verification hash for the report."""
        data_string = f"{self.user.id}:{self.start_date}:{self.end_date}:{len(self.entries)}:{self.stats['avg_score']:.4f}"
        return hashlib.sha256(data_string.encode()).hexdigest()[:16].upper()

    def _get_patient_identifier(self):
        """Get patient identifier (anonymized or real)."""
        if self.anonymize:
            # Generate anonymous ID from user ID
            return f"Patient #{self.user.id:05d}"
        else:
            first_name = self.user.first_name or ""
            last_name = self.user.last_name or ""
            name = f"{first_name} {last_name}".strip()
            if not name:
                name = self.user.username or self.user.email or f"User {self.user.id}"
            return name
    
    def export_csv(self) -> HttpResponse:
        """Generate comprehensive CSV export for healthcare providers."""
        response = HttpResponse(content_type="text/csv")
        
        filename = self._generate_filename("csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Report Header Information
        writer.writerow(["CSU SYMPTOM TRACKING REPORT"])
        writer.writerow(["Generated for NHS/Healthcare Provider Use"])
        writer.writerow([])
        writer.writerow(["CLINICAL REFERENCE"])
        writer.writerow(["ICD-10 Code", self.ICD10_CODE, self.ICD10_DESCRIPTION])
        writer.writerow(["SNOMED-CT Code", self.SNOMED_CODE, "Chronic spontaneous urticaria"])
        writer.writerow([])
        
        # Patient Information
        writer.writerow(["PATIENT INFORMATION"])
        writer.writerow(["Patient Identifier", self._get_patient_identifier()])
        writer.writerow(["Report Date Range", f"{self.start_date.strftime('%d %B %Y')} to {self.end_date.strftime('%d %B %Y')}"])
        writer.writerow(["Report Generated", timezone.now().strftime("%d %B %Y at %H:%M")])
        writer.writerow(["Report Verification Code", self._generate_report_hash()])
        writer.writerow([])
        
        # Executive Summary
        writer.writerow(["EXECUTIVE SUMMARY"])
        category, _ = self._get_current_disease_category()
        writer.writerow(["Current Disease Activity", category])
        writer.writerow(["Tracking Adherence", f"{self.stats['adherence_pct']:.1f}%"])
        writer.writerow(["Average Daily Score", f"{self.stats['avg_score']:.2f} / 6.00"])
        
        if self.patterns:
            writer.writerow(["Symptom-Free Days", f"{self.patterns['symptom_free_days']} ({self.patterns['symptom_free_pct']:.1f}%)"])
            writer.writerow(["Severe Symptom Days", f"{self.patterns['severe_days']} ({self.patterns['severe_pct']:.1f}%)"])
            writer.writerow(["Disease Trend", self.patterns['trend'].title()])
        
        if self.treatment_analysis:
            writer.writerow(["Antihistamine Response", self.treatment_analysis['response_category']])
        writer.writerow([])
        
        # Daily Data Header
        writer.writerow(["DAILY SYMPTOM LOG"])
        headers = ["Date", "Day of Week", "Total Score (0-6)", "Severity Category"]
        if self.include_breakdown:
            headers.extend(["Itch Score (0-3)", "Itch Severity", "Hive Score (0-3)", "Hive Count Category"])
        if self.include_antihistamine:
            headers.append("Antihistamine Taken")
        # Add QoL columns
        headers.extend(["QoL Sleep (0-4)", "QoL Activities (0-4)", "QoL Appearance (0-4)", "QoL Mood (0-4)", "QoL Total (0-16)"])
        if self.include_notes:
            headers.append("Patient Notes")
        
        writer.writerow(headers)
        
        # Data rows with clinical categorization
        for entry in self.entries:
            # Determine severity category
            if entry.score == 0:
                severity = "No Symptoms"
            elif entry.score <= 2:
                severity = "Mild"
            elif entry.score <= 4:
                severity = "Moderate"
            else:
                severity = "Severe"
            
            row = [
                entry.date.strftime("%Y-%m-%d"),
                entry.date.strftime("%A"),
                entry.score,
                severity,
            ]
            
            if self.include_breakdown:
                row.extend([
                    entry.itch_score if entry.itch_score is not None else "",
                    self.ITCH_LABELS.get(entry.itch_score, "") if entry.itch_score is not None else "",
                    entry.hive_count_score if entry.hive_count_score is not None else "",
                    self.HIVE_LABELS.get(entry.hive_count_score, "") if entry.hive_count_score is not None else "",
                ])
            
            if self.include_antihistamine:
                row.append("Yes" if entry.took_antihistamine else "No")
            
            # Add QoL data
            row.extend([
                entry.qol_sleep if entry.qol_sleep is not None else "",
                entry.qol_daily_activities if entry.qol_daily_activities is not None else "",
                entry.qol_appearance if entry.qol_appearance is not None else "",
                entry.qol_mood if entry.qol_mood is not None else "",
                entry.qol_score if entry.qol_score is not None else "",
            ])
            
            if self.include_notes:
                row.append(entry.notes or "")
            
            writer.writerow(row)
        
        writer.writerow([])
        
        # Statistical Summary
        writer.writerow(["STATISTICAL SUMMARY"])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Days in Period", self.stats["total_days"]])
        writer.writerow(["Days with Recorded Data", self.stats["logged_days"]])
        writer.writerow(["Days Missing Data", self.stats["missing_days"]])
        writer.writerow(["Tracking Adherence Rate", f"{self.stats['adherence_pct']:.1f}%"])
        writer.writerow(["Mean Daily Score", f"{self.stats['avg_score']:.2f}"])
        writer.writerow(["Minimum Daily Score", self.stats['min_score']])
        writer.writerow(["Maximum Daily Score", self.stats['max_score']])
        
        if self.stats["avg_itch"] is not None:
            writer.writerow(["Mean Itch Score", f"{self.stats['avg_itch']:.2f}"])
        if self.stats["avg_hives"] is not None:
            writer.writerow(["Mean Hive Score", f"{self.stats['avg_hives']:.2f}"])
        
        writer.writerow([])
        
        # Weekly UAS7 Scores
        if self.stats["weekly_uas7"]:
            writer.writerow(["WEEKLY UAS7 SCORES"])
            writer.writerow(["UAS7 is the validated scoring system recommended by EAACI/GA²LEN/EuroGuiDerm guidelines"])
            writer.writerow(["Week Period", "UAS7 Score", "Disease Activity Category", "Data Completeness"])
            for week in self.stats["weekly_uas7"]:
                if week["complete"]:
                    for min_val, max_val, label, _ in self.UAS7_CATEGORIES:
                        if min_val <= week["uas7"] <= max_val:
                            activity_category = label
                            break
                    completeness = "Complete (7/7 days)"
                else:
                    activity_category = "Incomplete data - interpret with caution"
                    completeness = f"Partial ({week.get('days_logged', 0)}/7 days)"
                
                writer.writerow([
                    f"{week['week_start'].strftime('%d %b %Y')} - {week['week_end'].strftime('%d %b %Y')}",
                    week["uas7"],
                    activity_category,
                    completeness,
                ])
            writer.writerow([])
            
            # UAS7 Reference Guide
            writer.writerow(["UAS7 INTERPRETATION GUIDE"])
            writer.writerow(["Score Range", "Category", "Clinical Interpretation"])
            for min_val, max_val, label, _ in self.UAS7_CATEGORIES:
                guidance = self.CLINICAL_GUIDANCE.get(label, {})
                writer.writerow([f"{min_val}-{max_val}", label, guidance.get("description", "")])
        
        writer.writerow([])
        
        # Treatment Response Analysis
        if self.treatment_analysis and self.include_antihistamine:
            writer.writerow(["ANTIHISTAMINE TREATMENT RESPONSE ANALYSIS"])
            writer.writerow(["Days with Antihistamine", self.treatment_analysis['days_with_antihistamine']])
            writer.writerow(["Days without Antihistamine", self.treatment_analysis['days_without_antihistamine']])
            
            if self.treatment_analysis['avg_score_with'] is not None:
                writer.writerow(["Average Score with Antihistamine", f"{self.treatment_analysis['avg_score_with']:.2f}"])
            if self.treatment_analysis['avg_score_without'] is not None:
                writer.writerow(["Average Score without Antihistamine", f"{self.treatment_analysis['avg_score_without']:.2f}"])
            
            writer.writerow(["Estimated Score Reduction", f"{self.treatment_analysis['reduction_pct']:.1f}%"])
            writer.writerow(["Treatment Response Category", self.treatment_analysis['response_category']])
            writer.writerow(["Medication Adherence Rate", f"{self.treatment_analysis['adherence_rate']:.1f}%"])
            writer.writerow([])
        
        # Pattern Analysis
        if self.patterns:
            writer.writerow(["SYMPTOM PATTERN ANALYSIS"])
            
            # Day of week patterns
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            writer.writerow(["Day of Week", "Average Score"])
            for day_num, avg in self.patterns.get("weekday_averages", {}).items():
                writer.writerow([day_names[day_num], f"{avg:.2f}"])
            
            writer.writerow([])
            writer.writerow(["Longest Symptom-Free Streak", f"{self.patterns['longest_remission_streak']} consecutive days"])
            
            # Flare episodes
            if self.patterns.get("flare_episodes"):
                writer.writerow([])
                writer.writerow(["IDENTIFIED FLARE EPISODES"])
                writer.writerow(["Period", "Duration", "Peak Score", "Average Score During Flare"])
                for flare in self.patterns["flare_episodes"]:
                    writer.writerow([
                        f"{flare['start'].strftime('%d %b')} - {flare['end'].strftime('%d %b %Y')}",
                        f"{flare['duration']} days",
                        flare['peak_score'],
                        f"{flare['avg_score']:.2f}",
                    ])
        
        writer.writerow([])
        
        # Clinical Notes Section
        if self.include_notes:
            entries_with_notes = [e for e in self.entries if e.notes]
            if entries_with_notes:
                writer.writerow(["PATIENT NOTES"])
                writer.writerow(["Date", "Note"])
                for entry in entries_with_notes:
                    writer.writerow([entry.date.strftime("%d %b %Y"), entry.notes])
                writer.writerow([])
        
        # Disclaimer
        writer.writerow(["IMPORTANT CLINICAL DISCLAIMER"])
        writer.writerow(["This report contains patient-recorded symptom data and is provided for informational purposes only."])
        writer.writerow(["Data has not been verified by a healthcare professional and should be reviewed in clinical context."])
        writer.writerow(["This data is not intended as a substitute for professional medical advice, diagnosis, or treatment."])
        writer.writerow(["Scoring methodology follows EAACI/GA²LEN/EuroGuiDerm urticaria guidelines (2021)."])
        writer.writerow([])
        writer.writerow(["Report generated by CSU Tracker Application"])
        writer.writerow(["For healthcare provider use only"])
        
        return response
    
    def export_pdf(self, inline: bool = False) -> HttpResponse:
        """Generate clinical PDF report for NHS/healthcare providers.
        
        Args:
            inline: If True, sets Content-Disposition to 'inline' so the
                    browser renders the PDF in-page (e.g. inside an iframe).
                    If False (default), uses 'attachment' to trigger a download.
        """
        if self.report_type == "detailed":
            return self._export_detailed_pdf(inline=inline)
        else:
            return self._export_quick_pdf(inline=inline)
    
    def _export_quick_pdf(self, inline: bool = False) -> HttpResponse:
        """Generate quick summary PDF - 1-page overview for routine check-ups."""
        response = HttpResponse(content_type="application/pdf")
        
        filename = self._generate_filename("pdf").replace("data_export", "quick_summary")
        disposition = "inline" if inline else "attachment"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=20*mm,
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Colors
        NHS_BLUE = colors.HexColor("#005EB8")
        CLINICAL_GREEN = colors.HexColor("#22C55E")
        CLINICAL_GREY = colors.HexColor("#6B7280")
        
        # Styles
        title_style = ParagraphStyle(
            "QuickTitle", parent=styles["Heading1"],
            fontSize=20, spaceAfter=4, textColor=NHS_BLUE, fontName="Helvetica-Bold",
        )
        section_style = ParagraphStyle(
            "QuickSection", parent=styles["Heading2"],
            fontSize=11, spaceBefore=10, spaceAfter=5, textColor=NHS_BLUE, fontName="Helvetica-Bold",
        )
        normal_style = ParagraphStyle(
            "QuickNormal", parent=styles["Normal"], fontSize=9, spaceAfter=4,
        )
        small_style = ParagraphStyle(
            "QuickSmall", parent=styles["Normal"], fontSize=8, textColor=CLINICAL_GREY,
        )
        
        # Header
        elements.append(Paragraph("CSU SYMPTOM SUMMARY", title_style))
        elements.append(Paragraph("Quick Overview for Healthcare Provider", small_style))
        elements.append(Spacer(1, 6))
        elements.append(HRFlowable(width="100%", thickness=2, color=NHS_BLUE))
        elements.append(Spacer(1, 8))
        
        # Patient & Period Info (in a styled box)
        info_box_style = ParagraphStyle(
            "InfoBox", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#374151"),
        )
        info_data = [
            [
                Paragraph(f"<b>Patient:</b> {self._get_patient_identifier()}", info_box_style),
                Paragraph(f"<b>Period:</b> {self.start_date.strftime('%d %b %Y')} – {self.end_date.strftime('%d %b %Y')}", info_box_style),
                Paragraph(f"<b>Generated:</b> {timezone.now().strftime('%d %b %Y')}", info_box_style),
            ],
        ]
        info_table = Table(info_data, colWidths=[170, 200, 110])
        info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10))
        
        # Status Banner
        category, _ = self._get_current_disease_category()
        
        if category == "Well Controlled":
            status_bg = colors.HexColor("#ECFDF5")
            status_border = colors.HexColor("#22C55E")
            status_text_color = "#166534"
        elif category == "Mild Activity":
            status_bg = colors.HexColor("#F0FDF4")
            status_border = colors.HexColor("#84CC16")
            status_text_color = "#3F6212"
        elif category == "Moderate Activity":
            status_bg = colors.HexColor("#FFFBEB")
            status_border = colors.HexColor("#F59E0B")
            status_text_color = "#92400E"
        elif category == "Severe Activity":
            status_bg = colors.HexColor("#FEF2F2")
            status_border = colors.HexColor("#EF4444")
            status_text_color = "#991B1B"
        else:
            status_bg = colors.HexColor("#F8FAFC")
            status_border = colors.HexColor("#94A3B8")
            status_text_color = "#475569"
        
        status_style = ParagraphStyle(
            "QuickStatus", parent=styles["Normal"],
            fontSize=12, fontName="Helvetica-Bold",
            textColor=colors.HexColor(status_text_color),
            alignment=TA_CENTER,
        )
        status_data = [[Paragraph(f"● Disease Activity: {category}", status_style)]]
        status_table = Table(status_data, colWidths=[480])
        status_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), status_bg),
            ("BOX", (0, 0), (-1, -1), 1, status_border),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(status_table)
        elements.append(Spacer(1, 10))
        
        # Key Metrics (4 cards)
        card_h_style = ParagraphStyle("QH", parent=styles["Normal"], fontSize=7,
                                       textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)
        card_v_style = ParagraphStyle("QV", parent=styles["Normal"], fontSize=16,
                                       fontName="Helvetica-Bold", textColor=colors.HexColor("#1E293B"),
                                       alignment=TA_CENTER)
        card_s_style = ParagraphStyle("QS", parent=styles["Normal"], fontSize=7,
                                       textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER)
        
        metrics_data = [
            [
                Paragraph("MEAN SCORE", card_h_style),
                Paragraph("DAYS TRACKED", card_h_style),
                Paragraph("ADHERENCE", card_h_style),
                Paragraph("SYMPTOM-FREE", card_h_style),
            ],
            [
                Paragraph(f"{self.stats['avg_score']:.1f}", card_v_style),
                Paragraph(f"{self.stats['logged_days']}", card_v_style),
                Paragraph(f"{self.stats['adherence_pct']:.0f}%", card_v_style),
                Paragraph(f"{self.patterns.get('symptom_free_days', 0) if self.patterns else 0}", card_v_style),
            ],
            [
                Paragraph("out of 6.0", card_s_style),
                Paragraph(f"of {self.stats['total_days']} days", card_s_style),
                Paragraph("logging rate", card_s_style),
                Paragraph("days (score 0)", card_s_style),
            ],
        ]
        metrics_table = Table(metrics_data, colWidths=[120, 120, 120, 120])
        metrics_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
            ("LINEAFTER", (0, 0), (2, -1), 0.3, colors.HexColor("#E2E8F0")),
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 10))
        
        # UAS7 Summary
        if self.stats["weekly_uas7"]:
            elements.append(Paragraph("Weekly UAS7 Scores", section_style))
            uas7_data = [["Week", "UAS7", "Status"]]
            for week in self.stats["weekly_uas7"][-4:]:
                status = "Complete" if week["complete"] else f"Partial ({week.get('days_logged', 0)}/7)"
                activity = "Unknown"
                if week["complete"]:
                    for min_val, max_val, label, _ in self.UAS7_CATEGORIES:
                        if min_val <= week["uas7"] <= max_val:
                            activity = label
                            break
                uas7_data.append([
                    f"{week['week_start'].strftime('%d %b')} – {week['week_end'].strftime('%d %b')}",
                    str(week["uas7"]),
                    f"{activity}" if week["complete"] else status,
                ])
            
            uas7_table = Table(uas7_data, colWidths=[160, 60, 150])
            
            # Build style with severity coloring
            uas7_style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), NHS_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
            
            for row_idx, week in enumerate(self.stats["weekly_uas7"][-4:], start=1):
                if week.get("complete"):
                    uas7 = week["uas7"]
                    if uas7 <= 6:
                        row_color = colors.HexColor("#ECFDF5")
                    elif uas7 <= 15:
                        row_color = colors.HexColor("#FFFBEB")
                    elif uas7 <= 27:
                        row_color = colors.HexColor("#FFF7ED")
                    else:
                        row_color = colors.HexColor("#FEF2F2")
                    uas7_style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), row_color))
            
            uas7_table.setStyle(TableStyle(uas7_style_cmds))
            elements.append(uas7_table)
            elements.append(Spacer(1, 10))
        
        # Simple trend chart
        if len(self.entries) >= 2:
            elements.append(Paragraph("Symptom Trend", section_style))
            chart = self._create_simple_trend_chart()
            elements.append(chart)
            elements.append(Spacer(1, 8))
        
        # Footer
        elements.append(Spacer(1, 12))
        elements.append(HRFlowable(width="100%", thickness=1, color=CLINICAL_GREY))
        elements.append(Spacer(1, 6))
        footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=CLINICAL_GREY, alignment=TA_CENTER)
        elements.append(Paragraph(
            f"CSU Tracker Quick Summary • Patient-recorded data • Not verified by healthcare professional • "
            f"For full analysis, generate In-Depth Report",
            footer_style
        ))
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
    
    def _create_simple_trend_chart(self):
        """Create a simple trend chart with smooth curves for quick summary."""
        drawing = Drawing(480, 140)
        
        if len(self.entries) < 2:
            return drawing
        
        chart_left = 40
        chart_bottom = 30
        chart_width = 400
        chart_height = 90
        
        # Background with subtle gradient effect
        drawing.add(Rect(chart_left, chart_bottom, chart_width, chart_height, 
                        fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#E2E8F0"),
                        strokeWidth=0.5))
        
        # Subtle horizontal grid lines
        for i in range(1, 6):
            y = chart_bottom + (i / 6) * chart_height
            drawing.add(Line(chart_left, y, chart_left + chart_width, y,
                           strokeColor=colors.HexColor("#F1F5F9"), strokeWidth=0.4))
        
        # Plot points
        max_entries = min(len(self.entries), 30)
        recent_entries = self.entries[-max_entries:]
        x_step = chart_width / max(1, len(recent_entries) - 1)
        
        # Build coordinate arrays
        points = []
        for i, entry in enumerate(recent_entries):
            x = chart_left + i * x_step
            y = chart_bottom + (entry.score / 6) * chart_height
            points.append((x, y))
        
        # Draw smooth area fill under curve
        if len(points) >= 2:
            area_path = Path()
            area_path.moveTo(points[0][0], chart_bottom)
            area_path.lineTo(points[0][0], points[0][1])
            
            if len(points) >= 3:
                # Use smooth Catmull-Rom spline interpolation
                for i in range(len(points) - 1):
                    p0 = points[max(0, i - 1)]
                    p1 = points[i]
                    p2 = points[min(len(points) - 1, i + 1)]
                    p3 = points[min(len(points) - 1, i + 2)]
                    
                    tension = 0.35
                    cp1x = p1[0] + (p2[0] - p0[0]) * tension
                    cp1y = p1[1] + (p2[1] - p0[1]) * tension
                    cp2x = p2[0] - (p3[0] - p1[0]) * tension
                    cp2y = p2[1] - (p3[1] - p1[1]) * tension
                    
                    # Clamp y values
                    cp1y = max(chart_bottom, min(chart_bottom + chart_height, cp1y))
                    cp2y = max(chart_bottom, min(chart_bottom + chart_height, cp2y))
                    
                    area_path.curveTo(cp1x, cp1y, cp2x, cp2y, p2[0], p2[1])
            else:
                area_path.lineTo(points[1][0], points[1][1])
            
            area_path.lineTo(points[-1][0], chart_bottom)
            area_path.closePath()
            area_path.fillColor = colors.HexColor("#DBEAFE")
            area_path.fillOpacity = 0.4
            area_path.strokeColor = None
            drawing.add(area_path)
        
        # Draw smooth curve line
        if len(points) >= 3:
            line_path = Path()
            line_path.moveTo(points[0][0], points[0][1])
            
            for i in range(len(points) - 1):
                p0 = points[max(0, i - 1)]
                p1 = points[i]
                p2 = points[min(len(points) - 1, i + 1)]
                p3 = points[min(len(points) - 1, i + 2)]
                
                tension = 0.35
                cp1x = p1[0] + (p2[0] - p0[0]) * tension
                cp1y = p1[1] + (p2[1] - p0[1]) * tension
                cp2x = p2[0] - (p3[0] - p1[0]) * tension
                cp2y = p2[1] - (p3[1] - p1[1]) * tension
                
                cp1y = max(chart_bottom, min(chart_bottom + chart_height, cp1y))
                cp2y = max(chart_bottom, min(chart_bottom + chart_height, cp2y))
                
                line_path.curveTo(cp1x, cp1y, cp2x, cp2y, p2[0], p2[1])
            
            line_path.strokeColor = colors.HexColor("#005EB8")
            line_path.strokeWidth = 2
            line_path.fillColor = None
            drawing.add(line_path)
        elif len(points) == 2:
            drawing.add(Line(points[0][0], points[0][1], points[1][0], points[1][1],
                           strokeColor=colors.HexColor("#005EB8"), strokeWidth=2))
        
        # Draw data points with glow effect
        for i, (x, y) in enumerate(points):
            score = recent_entries[i].score
            if score <= 2:
                point_color = colors.HexColor("#22C55E")
            elif score <= 4:
                point_color = colors.HexColor("#F59E0B")
            else:
                point_color = colors.HexColor("#EF4444")
            
            # Outer glow
            drawing.add(Circle(x, y, 5, fillColor=point_color, fillOpacity=0.15, strokeColor=None))
            # Main point
            drawing.add(Circle(x, y, 2.5, fillColor=point_color, strokeColor=colors.white, strokeWidth=0.8))
        
        # Y-axis labels
        for i in [0, 2, 4, 6]:
            y = chart_bottom + (i / 6) * chart_height
            drawing.add(String(chart_left - 12, y - 3, str(i), fontSize=7, fillColor=colors.HexColor("#64748B"),
                              textAnchor="end"))
        
        # X-axis date labels
        if len(recent_entries) > 1:
            label_count = min(5, len(recent_entries))
            step = max(1, (len(recent_entries) - 1) // (label_count - 1))
            for idx in range(0, len(recent_entries), step):
                if idx < len(recent_entries):
                    x = chart_left + idx * x_step
                    date_str = recent_entries[idx].date.strftime("%d %b")
                    drawing.add(String(x, chart_bottom - 12, date_str,
                                      fontSize=6, fillColor=colors.HexColor("#94A3B8"),
                                      textAnchor="middle"))
            # Always show last date
            if (len(recent_entries) - 1) % step != 0:
                x = chart_left + (len(recent_entries) - 1) * x_step
                date_str = recent_entries[-1].date.strftime("%d %b")
                drawing.add(String(x, chart_bottom - 12, date_str,
                                  fontSize=6, fillColor=colors.HexColor("#94A3B8"),
                                  textAnchor="middle"))
        
        # Y-axis title
        drawing.add(String(8, chart_bottom + chart_height / 2, "Score",
                          fontSize=7, fillColor=colors.HexColor("#64748B"),
                          textAnchor="middle"))
        
        return drawing
    
    def _export_detailed_pdf(self, inline: bool = False) -> HttpResponse:
        """Generate comprehensive in-depth clinical PDF report for NHS/healthcare providers."""
        response = HttpResponse(content_type="application/pdf")
        
        filename = self._generate_filename("pdf").replace("data_export", "detailed_report")
        disposition = "inline" if inline else "attachment"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=20*mm,
        )
        
        # Build content
        elements = []
        styles = getSampleStyleSheet()
        
        # Define NHS-appropriate color scheme
        NHS_BLUE = colors.HexColor("#005EB8")
        NHS_DARK_BLUE = colors.HexColor("#003087")
        NHS_LIGHT_BLUE = colors.HexColor("#41B6E6")
        CLINICAL_GREEN = colors.HexColor("#22C55E")
        CLINICAL_AMBER = colors.HexColor("#F59E0B")
        CLINICAL_RED = colors.HexColor("#DC2626")
        CLINICAL_GREY = colors.HexColor("#6B7280")
        
        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=22,
            spaceAfter=6,
            textColor=NHS_BLUE,
            fontName="Helvetica-Bold",
        )
        
        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=4,
            textColor=CLINICAL_GREY,
        )
        
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=6,
            textColor=NHS_DARK_BLUE,
            fontName="Helvetica-Bold",
            borderPadding=(0, 0, 3, 0),
        )
        
        subsection_style = ParagraphStyle(
            "SubsectionHeading",
            parent=styles["Heading3"],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#374151"),
            fontName="Helvetica-Bold",
        )
        
        normal_style = ParagraphStyle(
            "CustomNormal",
            parent=styles["Normal"],
            fontSize=9,
            spaceAfter=4,
            leading=12,
        )
        
        small_style = ParagraphStyle(
            "CustomSmall",
            parent=styles["Normal"],
            fontSize=8,
            textColor=CLINICAL_GREY,
            leading=10,
        )
        
        clinical_note_style = ParagraphStyle(
            "ClinicalNote",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#1E40AF"),
            backgroundColor=colors.HexColor("#EFF6FF"),
            borderPadding=6,
            spaceAfter=6,
        )
        
        # ========== HEADER SECTION ==========
        # NHS-style header
        header_data = [
            [
                Paragraph("<b>CHRONIC URTICARIA</b><br/>SYMPTOM TRACKING REPORT", title_style),
                "",
            ],
        ]
        header_table = Table(header_data, colWidths=[400, 70])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        elements.append(header_table)
        
        elements.append(Paragraph(
            "Patient-Recorded Outcomes for Clinical Review",
            subtitle_style
        ))
        
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=2, color=NHS_BLUE))
        elements.append(Spacer(1, 8))
        
        # ========== PATIENT & REPORT INFO ==========
        info_data = [
            ["Patient:", self._get_patient_identifier(), "Report Period:", f"{self.start_date.strftime('%d %b %Y')} – {self.end_date.strftime('%d %b %Y')}"],
            ["ICD-10:", f"{self.ICD10_CODE} ({self.ICD10_DESCRIPTION})", "Generated:", timezone.now().strftime("%d %b %Y at %H:%M")],
            ["SNOMED-CT:", self.SNOMED_CODE, "Verification:", self._generate_report_hash()],
        ]
        
        info_table = Table(info_data, colWidths=[60, 150, 80, 190])
        info_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#374151")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10))

        # ======================================================================
        # ========== COMPREHENSIVE SUMMARY DASHBOARD (COVER PAGE) ==============
        # ======================================================================
        
        category, category_color = self._get_current_disease_category()
        
        # --- Status Banner ---
        if category == "Well Controlled":
            status_bg = colors.HexColor("#ECFDF5")
            status_border = colors.HexColor("#22C55E")
            status_icon = "●"
            status_text_color = "#166534"
        elif category == "Mild Activity":
            status_bg = colors.HexColor("#F0FDF4")
            status_border = colors.HexColor("#84CC16")
            status_icon = "●"
            status_text_color = "#3F6212"
        elif category == "Moderate Activity":
            status_bg = colors.HexColor("#FFFBEB")
            status_border = colors.HexColor("#F59E0B")
            status_icon = "●"
            status_text_color = "#92400E"
        elif category == "Severe Activity":
            status_bg = colors.HexColor("#FEF2F2")
            status_border = colors.HexColor("#EF4444")
            status_icon = "●"
            status_text_color = "#991B1B"
        else:
            status_bg = colors.HexColor("#F8FAFC")
            status_border = colors.HexColor("#94A3B8")
            status_icon = "○"
            status_text_color = "#475569"
        
        status_banner_style = ParagraphStyle(
            "StatusBanner", parent=styles["Normal"],
            fontSize=14, fontName="Helvetica-Bold",
            textColor=colors.HexColor(status_text_color),
            alignment=TA_CENTER,
        )
        status_detail_style = ParagraphStyle(
            "StatusDetail", parent=styles["Normal"],
            fontSize=9, textColor=colors.HexColor(status_text_color),
            alignment=TA_CENTER,
        )
        
        guidance = self.CLINICAL_GUIDANCE.get(category, {})
        guidance_desc = guidance.get("description", "Assessment pending — insufficient data")
        
        status_data = [
            [Paragraph(f"<font size='18'>{status_icon}</font>&nbsp;&nbsp;Current Status: <b>{category}</b>", status_banner_style)],
            [Paragraph(guidance_desc, status_detail_style)],
        ]
        status_table = Table(status_data, colWidths=[480])
        status_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), status_bg),
            ("BOX", (0, 0), (-1, -1), 1.5, status_border),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(status_table)
        elements.append(Spacer(1, 12))
        
        # --- Key Metrics Cards (4-column layout) ---
        card_header_style = ParagraphStyle(
            "CardHeader", parent=styles["Normal"],
            fontSize=7, textColor=colors.HexColor("#64748B"),
            alignment=TA_CENTER, fontName="Helvetica",
        )
        card_value_style = ParagraphStyle(
            "CardValue", parent=styles["Normal"],
            fontSize=18, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1E293B"),
            alignment=TA_CENTER,
        )
        card_sub_style = ParagraphStyle(
            "CardSub", parent=styles["Normal"],
            fontSize=7, textColor=colors.HexColor("#94A3B8"),
            alignment=TA_CENTER,
        )
        
        # Determine trend arrow
        trend = self.patterns.get("trend", "stable") if self.patterns else "stable"
        trend_change = self.patterns.get("trend_change", 0) if self.patterns else 0
        if trend == "improving":
            trend_arrow = "↓"
            trend_color = "#22C55E"
            trend_label = f"Improving ({abs(trend_change):.1f})"
        elif trend == "worsening":
            trend_arrow = "↑"
            trend_color = "#EF4444"
            trend_label = f"Worsening (+{abs(trend_change):.1f})"
        else:
            trend_arrow = "→"
            trend_color = "#64748B"
            trend_label = "Stable"
        
        # Last UAS7
        complete_weeks = [w for w in self.stats.get("weekly_uas7", []) if w.get("complete")]
        last_uas7 = str(complete_weeks[-1]["uas7"]) if complete_weeks else "—"
        last_uas7_sub = f"of 42 max" if complete_weeks else "No complete week"
        
        metrics_cards = [
            [
                [Paragraph("MEAN DAILY SCORE", card_header_style)],
                [Paragraph(f"{self.stats['avg_score']:.1f}", card_value_style)],
                [Paragraph("out of 6.0", card_sub_style)],
            ],
            [
                [Paragraph("LATEST UAS7", card_header_style)],
                [Paragraph(last_uas7, card_value_style)],
                [Paragraph(last_uas7_sub, card_sub_style)],
            ],
            [
                [Paragraph("TRACKING ADHERENCE", card_header_style)],
                [Paragraph(f"{self.stats['adherence_pct']:.0f}%", card_value_style)],
                [Paragraph(f"{self.stats['logged_days']} of {self.stats['total_days']} days", card_sub_style)],
            ],
            [
                [Paragraph("DISEASE TREND", card_header_style)],
                [Paragraph(f"<font color='{trend_color}'>{trend_arrow}</font>", card_value_style)],
                [Paragraph(f"<font color='{trend_color}'>{trend_label}</font>", card_sub_style)],
            ],
        ]
        
        card_tables = []
        for card_data in metrics_cards:
            card = Table(card_data, colWidths=[112])
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            card_tables.append(card)
        
        cards_row = Table([card_tables], colWidths=[120, 120, 120, 120])
        cards_row.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(cards_row)
        elements.append(Spacer(1, 12))
        
        # --- Summary Statistics Row (6-column with key numbers) ---
        stat_header = ParagraphStyle("StatH", parent=styles["Normal"], fontSize=6.5,
                                     textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER)
        stat_val = ParagraphStyle("StatV", parent=styles["Normal"], fontSize=11,
                                  fontName="Helvetica-Bold", textColor=colors.HexColor("#1E293B"),
                                  alignment=TA_CENTER)
        
        symptom_free = self.patterns.get("symptom_free_days", 0) if self.patterns else 0
        symptom_free_pct = self.patterns.get("symptom_free_pct", 0) if self.patterns else 0
        severe_days = self.patterns.get("severe_days", 0) if self.patterns else 0
        severe_pct = self.patterns.get("severe_pct", 0) if self.patterns else 0
        remission = self.patterns.get("longest_remission_streak", 0) if self.patterns else 0
        flare_count = len(self.patterns.get("flare_episodes", [])) if self.patterns else 0
        
        mini_stats_data = [
            [
                Paragraph("SYMPTOM-FREE", stat_header),
                Paragraph("SEVERE DAYS", stat_header),
                Paragraph("BEST STREAK", stat_header),
                Paragraph("FLARE EPISODES", stat_header),
                Paragraph("MIN SCORE", stat_header),
                Paragraph("MAX SCORE", stat_header),
            ],
            [
                Paragraph(f"<font color='#22C55E'>{symptom_free}</font> <font size='7' color='#94A3B8'>({symptom_free_pct:.0f}%)</font>", stat_val),
                Paragraph(f"<font color='#EF4444'>{severe_days}</font> <font size='7' color='#94A3B8'>({severe_pct:.0f}%)</font>", stat_val),
                Paragraph(f"{remission} <font size='7' color='#94A3B8'>days</font>", stat_val),
                Paragraph(f"{flare_count}", stat_val),
                Paragraph(f"{self.stats['min_score']}", stat_val),
                Paragraph(f"{self.stats['max_score']}", stat_val),
            ],
        ]
        
        mini_stats_table = Table(mini_stats_data, colWidths=[80, 80, 80, 80, 80, 80])
        mini_stats_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, 0), 0.3, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        elements.append(mini_stats_table)
        elements.append(Spacer(1, 12))
        
        # --- Charts Row: Score Distribution + Weekly UAS7 side by side ---
        chart_title_style = ParagraphStyle(
            "ChartTitle", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1E293B"), spaceBefore=2, spaceAfter=4,
        )
        
        dist_chart = self._create_score_distribution_chart()
        uas7_chart = self._create_weekly_uas7_bar_chart()
        
        charts_data = [
            [
                Paragraph("Score Distribution", chart_title_style),
                Paragraph("Weekly UAS7 Scores", chart_title_style),
            ],
            [dist_chart, uas7_chart],
        ]
        charts_table = Table(charts_data, colWidths=[240, 240])
        charts_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(charts_table)
        elements.append(Spacer(1, 8))
        
        # --- Treatment Response Quick Summary (if available) ---
        if self.treatment_analysis and self.treatment_analysis.get("response_category") != "Insufficient Data":
            tx_response = self.treatment_analysis
            response_cat = tx_response["response_category"]
            
            if response_cat == "Good Response":
                tx_color = "#22C55E"
                tx_bg = "#ECFDF5"
            elif response_cat == "Partial Response":
                tx_color = "#F59E0B"
                tx_bg = "#FFFBEB"
            else:
                tx_color = "#EF4444"
                tx_bg = "#FEF2F2"
            
            tx_summary_style = ParagraphStyle(
                "TxSummary", parent=styles["Normal"],
                fontSize=9, textColor=colors.HexColor("#374151"),
            )
            
            adherence_pct = tx_response.get("adherence_rate", 0)
            reduction_pct = tx_response.get("reduction_pct", 0)
            
            tx_quick = [
                [
                    Paragraph(f"<b>H1-Antihistamine Response:</b> <font color='{tx_color}'><b>{response_cat}</b></font>", tx_summary_style),
                    Paragraph(f"<b>Score Reduction:</b> {reduction_pct:.0f}%", tx_summary_style),
                    Paragraph(f"<b>Medication Adherence:</b> {adherence_pct:.0f}%", tx_summary_style),
                ],
            ]
            tx_table = Table(tx_quick, colWidths=[180, 150, 150])
            tx_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(tx_bg)),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(tx_color)),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]))
            elements.append(tx_table)
            elements.append(Spacer(1, 8))
        
        # --- QoL Quick Summary (if available) ---
        if self.qol_assessment:
            qol = self.qol_assessment
            qol_cat = qol.get("category", "minimal")
            
            if qol_cat == "minimal":
                qol_color = "#22C55E"
                qol_bg = "#ECFDF5"
            elif qol_cat == "mild":
                qol_color = "#84CC16"
                qol_bg = "#F0FDF4"
            elif qol_cat == "moderate":
                qol_color = "#F59E0B"
                qol_bg = "#FFFBEB"
            else:
                qol_color = "#EF4444"
                qol_bg = "#FEF2F2"
            
            qol_quick_style = ParagraphStyle(
                "QoLQuick", parent=styles["Normal"],
                fontSize=9, textColor=colors.HexColor("#374151"),
            )
            
            dlqi_text = f"{qol.get('estimated_dlqi', 0):.0f}/30"
            
            qol_quick = [
                [
                    Paragraph(f"<b>Quality of Life:</b> <font color='{qol_color}'><b>{qol['impact']}</b></font>", qol_quick_style),
                    Paragraph(f"<b>Est. DLQI:</b> {dlqi_text}", qol_quick_style),
                    Paragraph(f"<b>{qol.get('dlqi_interpretation', '')}</b>", qol_quick_style),
                ],
            ]
            qol_table = Table(qol_quick, colWidths=[180, 120, 180])
            qol_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(qol_bg)),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(qol_color)),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]))
            elements.append(qol_table)
            elements.append(Spacer(1, 8))
        
        # --- Clinical Guidance Box ---
        if self.include_clinical_guidance and category in self.CLINICAL_GUIDANCE:
            guidance = self.CLINICAL_GUIDANCE[category]
            
            guidance_box_style = ParagraphStyle(
                "GuidanceBox", parent=styles["Normal"],
                fontSize=9, textColor=colors.HexColor("#1E40AF"),
                leading=13,
            )
            
            review_interval = guidance.get("review_interval", "As needed")
            recommendation = guidance.get("recommendation", "")
            
            guidance_content = [
                [
                    Paragraph(
                        f"<b>Clinical Guidance</b> (EAACI/GA²LEN/EuroGuiDerm 2021)<br/><br/>"
                        f"<b>Recommended Action:</b> {recommendation}<br/>"
                        f"<b>Suggested Review Interval:</b> {review_interval}",
                        guidance_box_style
                    ),
                ],
            ]
            guidance_table = Table(guidance_content, colWidths=[480])
            guidance_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3B82F6")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]))
            elements.append(guidance_table)
        
        # --- Summary page footer ---
        elements.append(Spacer(1, 10))
        summary_footer_style = ParagraphStyle(
            "SummaryFooter", parent=styles["Normal"],
            fontSize=7, textColor=CLINICAL_GREY, alignment=TA_CENTER,
        )
        elements.append(Paragraph(
            "This summary is based on patient-recorded data and has not been verified by a healthcare professional. "
            "Detailed analysis including daily logs follows on subsequent pages.",
            summary_footer_style
        ))
        
        # ========== PAGE BREAK — DETAILED SECTIONS BEGIN ==========
        elements.append(PageBreak())
        
        # ========== DETAILED ANALYSIS HEADER ==========
        elements.append(Paragraph("DETAILED CLINICAL ANALYSIS", title_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=NHS_BLUE))
        elements.append(Spacer(1, 10))
        
        # ========== QUALITY OF LIFE ASSESSMENT ==========
        if self.qol_assessment:
            elements.append(Paragraph("QUALITY OF LIFE ASSESSMENT", section_style))
            
            qol = self.qol_assessment
            
            # Show different description based on data source
            if qol.get("data_source") == "actual":
                elements.append(Paragraph(
                    f"QoL assessment based on patient-reported outcomes. "
                    f"Data collected from {qol.get('entries_with_qol', 0)} of {qol.get('total_entries', 0)} logged entries.",
                    small_style
                ))
            else:
                elements.append(Paragraph(
                    "Estimated QoL impact based on symptom severity correlation with validated instruments (CU-Q2oL, DLQI). "
                    "For accurate QoL measurement, validated questionnaires should be administered.",
                    small_style
                ))
            elements.append(Spacer(1, 4))
            
            # QoL Impact box - different layout for actual vs estimated data
            if qol.get("data_source") == "actual" and isinstance(qol.get("domains"), dict):
                # Show detailed domain breakdown for actual data
                qol_data = [
                    ["Overall Impact", "Sleep", "Daily Activities", "Appearance", "Mood"],
                    [
                        qol["impact"],
                        qol["domains"]["sleep"]["impact"],
                        qol["domains"]["daily_activities"]["impact"],
                        qol["domains"]["appearance"]["impact"],
                        qol["domains"]["mood"]["impact"],
                    ],
                ]
                qol_table = Table(qol_data, colWidths=[100, 90, 100, 90, 90])
            else:
                # Use estimated data layout
                qol_data = [
                    ["Overall QoL Impact", "Estimated DLQI", "Sleep Impact", "Daily Activity Impact"],
                    [qol["impact"], f"{qol['estimated_dlqi']:.0f}/30", qol["sleep_impact"], qol["activity_impact"]],
                ]
                qol_table = Table(qol_data, colWidths=[120, 100, 130, 130])
            
            # Color code based on impact level
            if qol["category"] == "minimal":
                impact_color = colors.HexColor("#DCFCE7")
            elif qol["category"] == "mild":
                impact_color = colors.HexColor("#FEF9C3")
            elif qol["category"] == "moderate":
                impact_color = colors.HexColor("#FED7AA")
            else:
                impact_color = colors.HexColor("#FECACA")
            
            qol_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7C3AED")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 1), (-1, 1), impact_color),
            ]))
            elements.append(qol_table)
            elements.append(Spacer(1, 4))
            
            # QoL interpretation
            qol_note_style = ParagraphStyle(
                "QoLNote", parent=styles["Normal"], fontSize=9,
                textColor=colors.HexColor("#7C3AED"), backgroundColor=colors.HexColor("#F5F3FF"),
                borderPadding=6, spaceAfter=6,
            )
            
            if qol.get("data_source") == "actual":
                qol_score_text = f"Average QoL Score: {qol.get('avg_qol_score', 0):.1f}/16 ({qol.get('qol_percentage', 0):.0f}% impact)"
                elements.append(Paragraph(
                    f"<b>Assessment:</b> {qol['description']}<br/>"
                    f"<b>{qol_score_text}</b><br/>"
                    f"<b>DLQI Equivalent:</b> {qol['dlqi_interpretation']}",
                    qol_note_style
                ))
            else:
                elements.append(Paragraph(
                    f"<b>Assessment:</b> {qol['description']}<br/>"
                    f"<b>DLQI Interpretation:</b> {qol['dlqi_interpretation']}",
                    qol_note_style
                ))
            elements.append(Spacer(1, 8))
        
        # ========== UAS7 WEEKLY SCORES ==========
        if self.stats["weekly_uas7"]:
            elements.append(Paragraph("WEEKLY UAS7 SCORES", section_style))
            elements.append(Paragraph(
                "The Urticaria Activity Score (UAS7) is the gold-standard validated outcome measure for chronic urticaria, "
                "calculated as the sum of daily scores over 7 consecutive days (range 0-42).",
                small_style
            ))
            elements.append(Spacer(1, 4))
            
            uas7_header = ["Week Period", "UAS7", "Activity Level", "Data Quality"]
            uas7_data = [uas7_header]
            
            for week in self.stats["weekly_uas7"]:
                if week["complete"]:
                    for min_val, max_val, label, color in self.UAS7_CATEGORIES:
                        if min_val <= week["uas7"] <= max_val:
                            activity_label = label
                            break
                    quality = "✓ Complete"
                else:
                    activity_label = "Incomplete"
                    quality = f"Partial ({week.get('days_logged', 0)}/7)"
                
                uas7_data.append([
                    f"{week['week_start'].strftime('%d %b')} – {week['week_end'].strftime('%d %b')}",
                    str(week["uas7"]),
                    activity_label,
                    quality,
                ])
            
            uas7_table = Table(uas7_data, colWidths=[130, 50, 130, 90])
            
            # Color code rows based on severity
            table_style = [
                ("BACKGROUND", (0, 0), (-1, 0), NHS_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
            
            # Add row coloring based on UAS7 severity
            for row_idx, week in enumerate(self.stats["weekly_uas7"], start=1):
                if week["complete"]:
                    uas7 = week["uas7"]
                    if uas7 <= 6:
                        row_color = colors.HexColor("#DCFCE7")  # Green
                    elif uas7 <= 15:
                        row_color = colors.HexColor("#FEF9C3")  # Light yellow
                    elif uas7 <= 27:
                        row_color = colors.HexColor("#FED7AA")  # Orange
                    else:
                        row_color = colors.HexColor("#FECACA")  # Red
                    table_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), row_color))
            
            uas7_table.setStyle(TableStyle(table_style))
            elements.append(uas7_table)
            elements.append(Spacer(1, 6))
            
            # UAS7 interpretation guide
            guide_data = [
                ["Score", "Category", "Clinical Interpretation"],
                ["0-6", "Well Controlled", "Disease well controlled on current therapy"],
                ["7-15", "Mild Activity", "Consider optimising H1-antihistamine dose"],
                ["16-27", "Moderate Activity", "Consider add-on therapy if H1-antihistamine optimised"],
                ["28-42", "Severe Activity", "Urgent specialist review recommended"],
            ]
            guide_table = Table(guide_data, colWidths=[50, 100, 250])
            guide_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#DCFCE7")),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#FEF9C3")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FED7AA")),
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#FECACA")),
            ]))
            elements.append(guide_table)
            elements.append(Spacer(1, 10))
        
        # ========== TREND CHART ==========
        if len(self.entries) >= 2:
            elements.append(Paragraph("SYMPTOM TREND ANALYSIS", section_style))
            chart = self._create_enhanced_trend_chart()
            elements.append(chart)
            elements.append(Spacer(1, 8))
            
            # Itch vs Hive component breakdown
            if self.include_breakdown:
                has_itch = any(e.itch_score is not None for e in self.entries)
                has_hives = any(e.hive_count_score is not None for e in self.entries)
                if has_itch and has_hives:
                    elements.append(Paragraph("Component Breakdown: Itch vs Hive Scores", subsection_style))
                    itch_hive_chart = self._create_itch_hive_comparison_chart()
                    elements.append(itch_hive_chart)
                    elements.append(Spacer(1, 10))
            else:
                elements.append(Spacer(1, 10))
        
        # ========== TREATMENT RESPONSE ANALYSIS ==========
        if self.treatment_analysis and self.include_antihistamine:
            elements.append(Paragraph("H1-ANTIHISTAMINE TREATMENT RESPONSE", section_style))
            
            tx_data = [
                ["Metric", "With Antihistamine", "Without Antihistamine", "Difference"],
            ]
            
            avg_with = self.treatment_analysis['avg_score_with']
            avg_without = self.treatment_analysis['avg_score_without']
            
            if avg_with is not None and avg_without is not None:
                diff = avg_without - avg_with
                diff_pct = f"({self.treatment_analysis['reduction_pct']:.0f}% reduction)" if diff > 0 else ""
                tx_data.append([
                    "Mean Daily Score",
                    f"{avg_with:.2f}",
                    f"{avg_without:.2f}",
                    f"{diff:+.2f} {diff_pct}",
                ])
            
            tx_data.append([
                "Days Recorded",
                str(self.treatment_analysis['days_with_antihistamine']),
                str(self.treatment_analysis['days_without_antihistamine']),
                "",
            ])
            
            tx_table = Table(tx_data, colWidths=[120, 100, 100, 160])
            tx_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NHS_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(tx_table)
            
            # Response interpretation
            response_cat = self.treatment_analysis['response_category']
            if response_cat == "Good Response":
                interpretation = "Patient demonstrates good response to H1-antihistamine therapy (≥50% symptom reduction)."
            elif response_cat == "Partial Response":
                interpretation = "Partial response to H1-antihistamine. Consider dose escalation up to 4x licensed dose per guidelines."
            elif response_cat == "Minimal Response":
                interpretation = "Minimal response to H1-antihistamine. Consider specialist referral for add-on therapy options."
            elif response_cat == "No Response / Refractory":
                interpretation = "No significant response to H1-antihistamine therapy. Specialist referral recommended for biologic consideration."
            else:
                interpretation = "Insufficient data to assess treatment response. More consistent tracking recommended."
            
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(f"<b>Assessment:</b> {interpretation}", small_style))
            elements.append(Spacer(1, 10))
        
        # ========== FLARE EPISODE ANALYSIS ==========
        if self.patterns and self.patterns.get("flare_episodes"):
            elements.append(Paragraph("IDENTIFIED FLARE EPISODES", section_style))
            elements.append(Paragraph(
                "Flare episodes defined as ≥2 consecutive days with daily score ≥4",
                small_style
            ))
            elements.append(Spacer(1, 4))
            
            flare_data = [["Period", "Duration", "Peak Score", "Mean Score"]]
            for flare in self.patterns["flare_episodes"][:5]:  # Limit to 5
                flare_data.append([
                    f"{flare['start'].strftime('%d %b')} – {flare['end'].strftime('%d %b %Y')}",
                    f"{flare['duration']} days",
                    str(flare['peak_score']),
                    f"{flare['avg_score']:.1f}",
                ])
            
            flare_table = Table(flare_data, colWidths=[150, 80, 80, 80])
            flare_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DC2626")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FEF2F2")),
            ]))
            elements.append(flare_table)
            elements.append(Spacer(1, 10))
        
        # ========== PAGE BREAK FOR DAILY LOG ==========
        elements.append(PageBreak())
        
        # ========== DAILY SYMPTOM LOG ==========
        elements.append(Paragraph("DAILY SYMPTOM LOG", section_style))
        
        # Build table headers
        table_headers = ["Date", "Score"]
        if self.include_breakdown:
            table_headers.extend(["Itch", "Hives"])
        if self.include_antihistamine:
            table_headers.append("Rx")
        if self.include_notes:
            table_headers.append("Notes")
        
        table_data = [table_headers]
        
        for entry in self.entries:
            # Add severity indicator
            if entry.score == 0:
                score_display = "0 ●"
            elif entry.score <= 2:
                score_display = f"{entry.score}"
            elif entry.score <= 4:
                score_display = f"{entry.score}"
            else:
                score_display = f"{entry.score}"
            
            row = [
                entry.date.strftime("%d %b %Y (%a)"),
                str(entry.score),
            ]
            
            if self.include_breakdown:
                row.extend([
                    self.ITCH_LABELS.get(entry.itch_score, "-"),
                    self.HIVE_LABELS.get(entry.hive_count_score, "-"),
                ])
            
            if self.include_antihistamine:
                row.append("✓" if entry.took_antihistamine else "")
            
            if self.include_notes:
                notes = entry.notes[:40] + "…" if len(entry.notes) > 40 else entry.notes
                row.append(notes or "")
            
            table_data.append(row)
        
        # Calculate column widths
        if self.include_notes:
            if self.include_breakdown and self.include_antihistamine:
                col_widths = [85, 35, 45, 55, 25, 145]
            elif self.include_breakdown:
                col_widths = [95, 40, 50, 65, 140]
            elif self.include_antihistamine:
                col_widths = [110, 45, 30, 205]
            else:
                col_widths = [120, 55, 215]
        else:
            if self.include_breakdown and self.include_antihistamine:
                col_widths = [130, 55, 75, 95, 45]
            elif self.include_breakdown:
                col_widths = [140, 65, 95, 100]
            elif self.include_antihistamine:
                col_widths = [180, 100, 120]
            else:
                col_widths = [200, 200]
        
        daily_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Build table style with severity-based row coloring
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), NHS_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        
        # Color code rows based on score
        for row_idx, entry in enumerate(self.entries, start=1):
            if entry.score == 0:
                row_color = colors.HexColor("#DCFCE7")  # Green
            elif entry.score <= 2:
                row_color = colors.HexColor("#F0FDF4")  # Light green
            elif entry.score <= 4:
                row_color = colors.HexColor("#FEF9C3")  # Yellow
            else:
                row_color = colors.HexColor("#FEE2E2")  # Red
            table_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), row_color))
        
        daily_table.setStyle(TableStyle(table_style))
        elements.append(daily_table)
        
        # ========== PATIENT NOTES SECTION ==========
        if self.include_notes:
            entries_with_notes = [e for e in self.entries if e.notes]
            if entries_with_notes:
                elements.append(Spacer(1, 12))
                elements.append(Paragraph("PATIENT-RECORDED NOTES", section_style))
                
                for entry in entries_with_notes[:15]:  # Limit to 15 notes
                    elements.append(Paragraph(
                        f"<b>{entry.date.strftime('%d %b %Y')}:</b> {entry.notes}",
                        normal_style
                    ))
                
                if len(entries_with_notes) > 15:
                    elements.append(Paragraph(
                        f"<i>... and {len(entries_with_notes) - 15} additional notes not shown</i>",
                        small_style
                    ))
        
        # ========== SCORING METHODOLOGY ==========
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("SCORING METHODOLOGY", section_style))
        
        method_text = """
        <b>Urticaria Activity Score (UAS)</b><br/>
        The daily UAS is calculated by summing two components:<br/><br/>
        
        <b>Pruritus (Itch) Severity:</b><br/>
        0 = None | 1 = Mild (present but not troublesome) | 2 = Moderate (troublesome but not interfering with daily activities) | 3 = Severe (interfering with daily activities or sleep)<br/><br/>
        
        <b>Wheal Count:</b><br/>
        0 = None | 1 = Mild (&lt;20 wheals/24h) | 2 = Moderate (20-50 wheals/24h) | 3 = Severe (&gt;50 wheals/24h or large confluent areas)<br/><br/>
        
        <b>Daily Score:</b> 0-6 (sum of itch + wheals)<br/>
        <b>Weekly UAS7:</b> 0-42 (sum of 7 consecutive daily scores)<br/><br/>
        
        <i>Methodology per EAACI/GA²LEN/EuroGuiDerm urticaria guidelines (Zuberbier T, et al. Allergy. 2022)</i>
        """
        elements.append(Paragraph(method_text.strip(), small_style))
        
        # ========== DISCLAIMER FOOTER ==========
        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#DC2626")))
        elements.append(Spacer(1, 6))
        
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=7,
            textColor=colors.HexColor("#7F1D1D"),
            alignment=TA_CENTER,
            leading=9,
        )
        
        elements.append(Paragraph(
            "<b>IMPORTANT CLINICAL DISCLAIMER</b><br/>"
            "This report contains patient-recorded symptom data collected via the CSU Tracker application. "
            "Data has NOT been verified by a healthcare professional and should be interpreted within the context "
            "of a full clinical assessment. This report is provided for informational purposes only and is not "
            "intended as a substitute for professional medical advice, diagnosis, or treatment. Healthcare providers "
            "should exercise clinical judgement when incorporating this data into treatment decisions.",
            disclaimer_style
        ))
        
        elements.append(Spacer(1, 8))
        
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=7,
            textColor=CLINICAL_GREY,
            alignment=TA_CENTER,
        )
        
        elements.append(Paragraph(
            f"CSU Tracker In-Depth Report • Generated: {timezone.now().strftime('%d %B %Y at %H:%M')} • "
            f"Verification: {self._generate_report_hash()} • For Healthcare Provider Use Only",
            footer_style
        ))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF from buffer
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
    
    def _create_enhanced_trend_chart(self):
        """Create an enhanced clinical trend chart with smooth curves and severity zones."""
        drawing = Drawing(480, 210)
        
        # Chart area
        chart_left = 45
        chart_bottom = 40
        chart_width = 380
        chart_height = 130
        
        # Severity zone backgrounds (bottom to top) with softer colors
        zone_height = chart_height / 3
        
        # Well controlled zone (0-2) - soft green
        drawing.add(Rect(chart_left, chart_bottom, chart_width, zone_height, 
                        fillColor=colors.HexColor("#ECFDF5"), strokeColor=None))
        # Moderate zone (2-4) - soft amber
        drawing.add(Rect(chart_left, chart_bottom + zone_height, chart_width, zone_height,
                        fillColor=colors.HexColor("#FFFBEB"), strokeColor=None))
        # Severe zone (4-6) - soft red
        drawing.add(Rect(chart_left, chart_bottom + zone_height * 2, chart_width, zone_height,
                        fillColor=colors.HexColor("#FEF2F2"), strokeColor=None))
        
        # Chart border
        drawing.add(Rect(chart_left, chart_bottom, chart_width, chart_height,
                        fillColor=None, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.5))
        
        # Zone labels with rounded backgrounds
        zone_labels = [
            (chart_bottom + zone_height * 0.5 - 4, "Well Controlled", "#166534", "#DCFCE7"),
            (chart_bottom + zone_height * 1.5 - 4, "Moderate", "#92400E", "#FEF3C7"),
            (chart_bottom + zone_height * 2.5 - 4, "Severe", "#991B1B", "#FEE2E2"),
        ]
        for y_pos, label_text, text_color, bg_color in zone_labels:
            # Label background pill
            label_x = chart_left + chart_width + 4
            drawing.add(Rect(label_x, y_pos - 2, 60, 12,
                           fillColor=colors.HexColor(bg_color), strokeColor=None,
                           rx=3, ry=3))
            drawing.add(String(label_x + 30, y_pos, label_text,
                              fontSize=5.5, fillColor=colors.HexColor(text_color),
                              textAnchor="middle", fontName="Helvetica-Bold"))
        
        # Prepare data points
        data_points = [(i, e.score) for i, e in enumerate(self.entries)]
        
        if not data_points:
            return drawing
        
        # Scale factors
        max_x = len(data_points) - 1 if len(data_points) > 1 else 1
        max_y = 6
        
        x_scale = chart_width / max_x
        y_scale = chart_height / max_y
        
        # Build pixel coordinates
        points = []
        for idx, score in data_points:
            x = chart_left + idx * x_scale
            y = chart_bottom + score * y_scale
            points.append((x, y))
        
        # Draw subtle Y-axis grid lines
        for y_val in range(0, 7):
            y_pos = chart_bottom + y_val * y_scale
            drawing.add(Line(
                chart_left, y_pos, chart_left + chart_width, y_pos,
                strokeColor=colors.HexColor("#E2E8F0"),
                strokeWidth=0.3
            ))
            drawing.add(String(
                chart_left - 8, y_pos - 3, str(y_val),
                fontSize=7, fillColor=colors.HexColor("#64748B"),
                textAnchor="end"
            ))
        
        # Draw smooth area fill under curve
        if len(points) >= 2:
            area_path = Path()
            area_path.moveTo(points[0][0], chart_bottom)
            area_path.lineTo(points[0][0], points[0][1])
            
            if len(points) >= 3:
                for i in range(len(points) - 1):
                    p0 = points[max(0, i - 1)]
                    p1 = points[i]
                    p2 = points[min(len(points) - 1, i + 1)]
                    p3 = points[min(len(points) - 1, i + 2)]
                    
                    tension = 0.3
                    cp1x = p1[0] + (p2[0] - p0[0]) * tension
                    cp1y = p1[1] + (p2[1] - p0[1]) * tension
                    cp2x = p2[0] - (p3[0] - p1[0]) * tension
                    cp2y = p2[1] - (p3[1] - p1[1]) * tension
                    
                    cp1y = max(chart_bottom, min(chart_bottom + chart_height, cp1y))
                    cp2y = max(chart_bottom, min(chart_bottom + chart_height, cp2y))
                    
                    area_path.curveTo(cp1x, cp1y, cp2x, cp2y, p2[0], p2[1])
            else:
                area_path.lineTo(points[1][0], points[1][1])
            
            area_path.lineTo(points[-1][0], chart_bottom)
            area_path.closePath()
            area_path.fillColor = colors.HexColor("#1E40AF")
            area_path.fillOpacity = 0.08
            area_path.strokeColor = None
            drawing.add(area_path)
        
        # Draw average line (dashed)
        avg_y = chart_bottom + self.stats["avg_score"] * y_scale
        drawing.add(Line(
            chart_left, avg_y, chart_left + chart_width, avg_y,
            strokeColor=colors.HexColor("#8B5CF6"),
            strokeWidth=0.8,
            strokeDashArray=[5, 3]
        ))
        # Average label with background
        avg_label_x = chart_left - 8
        drawing.add(String(
            avg_label_x, avg_y - 3, f"Avg: {self.stats['avg_score']:.1f}",
            fontSize=5.5, fillColor=colors.HexColor("#7C3AED"),
            textAnchor="end", fontName="Helvetica-Bold"
        ))
        
        # Draw smooth trend curve
        if len(points) >= 3:
            line_path = Path()
            line_path.moveTo(points[0][0], points[0][1])
            
            for i in range(len(points) - 1):
                p0 = points[max(0, i - 1)]
                p1 = points[i]
                p2 = points[min(len(points) - 1, i + 1)]
                p3 = points[min(len(points) - 1, i + 2)]
                
                tension = 0.3
                cp1x = p1[0] + (p2[0] - p0[0]) * tension
                cp1y = p1[1] + (p2[1] - p0[1]) * tension
                cp2x = p2[0] - (p3[0] - p1[0]) * tension
                cp2y = p2[1] - (p3[1] - p1[1]) * tension
                
                cp1y = max(chart_bottom, min(chart_bottom + chart_height, cp1y))
                cp2y = max(chart_bottom, min(chart_bottom + chart_height, cp2y))
                
                line_path.curveTo(cp1x, cp1y, cp2x, cp2y, p2[0], p2[1])
            
            line_path.strokeColor = colors.HexColor("#1E40AF")
            line_path.strokeWidth = 2.2
            line_path.fillColor = None
            drawing.add(line_path)
        elif len(points) == 2:
            drawing.add(Line(points[0][0], points[0][1], points[1][0], points[1][1],
                           strokeColor=colors.HexColor("#1E40AF"), strokeWidth=2.2))
        
        # Draw data points with color coding and glow
        for i, (x, y) in enumerate(points):
            score = data_points[i][1]
            if score <= 2:
                point_color = colors.HexColor("#22C55E")
            elif score <= 4:
                point_color = colors.HexColor("#F59E0B")
            else:
                point_color = colors.HexColor("#EF4444")
            
            # Outer glow ring
            drawing.add(Circle(x, y, 5.5, fillColor=point_color, fillOpacity=0.12, strokeColor=None))
            # Main point
            drawing.add(Circle(x, y, 2.8, fillColor=point_color, strokeColor=colors.white, strokeWidth=0.8))
        
        # X-axis labels
        if len(self.entries) > 0:
            if len(self.entries) <= 7:
                label_indices = list(range(len(self.entries)))
            elif len(self.entries) <= 14:
                step = max(1, len(self.entries) // 5)
                label_indices = list(range(0, len(self.entries), step))
                if len(self.entries) - 1 not in label_indices:
                    label_indices.append(len(self.entries) - 1)
            else:
                step = len(self.entries) // 5
                label_indices = list(range(0, len(self.entries), step))
                if len(self.entries) - 1 not in label_indices:
                    label_indices.append(len(self.entries) - 1)
            
            for idx in label_indices:
                if idx < len(self.entries):
                    x = chart_left + idx * x_scale
                    date_str = self.entries[idx].date.strftime("%d %b")
                    drawing.add(String(
                        x, chart_bottom - 14, date_str,
                        fontSize=6, fillColor=colors.HexColor("#64748B"),
                        textAnchor="middle"
                    ))
                    # Tick mark
                    drawing.add(Line(x, chart_bottom, x, chart_bottom - 3,
                                    strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.3))
        
        # Y-axis title
        drawing.add(String(
            8, chart_bottom + chart_height / 2, "Daily Score",
            fontSize=7, fillColor=colors.HexColor("#475569"),
            textAnchor="middle"
        ))
        
        # Chart title
        drawing.add(String(
            chart_left + chart_width / 2, chart_bottom + chart_height + 16, 
            "Daily Symptom Score Trend",
            fontSize=10, fillColor=colors.HexColor("#1E293B"),
            textAnchor="middle",
            fontName="Helvetica-Bold"
        ))
        
        # Legend at bottom
        legend_y = chart_bottom - 28
        legend_items = [
            (colors.HexColor("#22C55E"), "Well Controlled (0-2)"),
            (colors.HexColor("#F59E0B"), "Moderate (3-4)"),
            (colors.HexColor("#EF4444"), "Severe (5-6)"),
            (colors.HexColor("#8B5CF6"), "Average"),
        ]
        legend_x = chart_left + 20
        for color, text in legend_items:
            drawing.add(Circle(legend_x, legend_y + 3, 3, fillColor=color, strokeColor=None))
            drawing.add(String(legend_x + 6, legend_y, text,
                              fontSize=5.5, fillColor=colors.HexColor("#64748B")))
            legend_x += 95
        
        return drawing
    
    def _generate_filename(self, extension: str) -> str:
        """Generate a filename for the export."""
        date_range = f"{self.start_date.strftime('%Y%m%d')}-{self.end_date.strftime('%Y%m%d')}"
        
        if self.anonymize:
            return f"csu_data_export_{date_range}_anonymized.{extension}"
        else:
            # Handle cases where username or email might be None
            name = self.user.username or self.user.email or f"user_{self.user.id}"
            safe_name = name.replace(" ", "_").replace("@", "_")[:20]
            return f"csu_data_export_{safe_name}_{date_range}.{extension}"

    def _create_score_distribution_chart(self):
        """Create a horizontal bar chart showing score distribution."""
        drawing = Drawing(220, 95)
        
        if not self.entries:
            return drawing
        
        scores = [e.score for e in self.entries]
        total = len(scores)
        distribution = {i: scores.count(i) for i in range(7)}
        
        chart_left = 30
        chart_bottom = 8
        bar_height = 10
        max_bar_width = 150
        max_count = max(distribution.values()) if distribution.values() else 1
        
        bar_colors = [
            colors.HexColor("#22C55E"),  # 0
            colors.HexColor("#4ADE80"),  # 1
            colors.HexColor("#86EFAC"),  # 2
            colors.HexColor("#FDE047"),  # 3
            colors.HexColor("#FBBF24"),  # 4
            colors.HexColor("#F87171"),  # 5
            colors.HexColor("#EF4444"),  # 6
        ]
        
        for score_val in range(7):
            count = distribution.get(score_val, 0)
            pct = (count / total * 100) if total > 0 else 0
            bar_width = (count / max_count) * max_bar_width if max_count > 0 else 0
            y = chart_bottom + (6 - score_val) * (bar_height + 2)
            
            # Score label
            drawing.add(String(chart_left - 4, y + 2, str(score_val),
                              fontSize=7, fillColor=colors.HexColor("#475569"),
                              textAnchor="end", fontName="Helvetica-Bold"))
            
            # Bar background
            drawing.add(Rect(chart_left, y, max_bar_width, bar_height,
                           fillColor=colors.HexColor("#F1F5F9"), strokeColor=None,
                           rx=3, ry=3))
            
            # Bar fill
            if bar_width > 0:
                drawing.add(Rect(chart_left, y, max(4, bar_width), bar_height,
                               fillColor=bar_colors[score_val], strokeColor=None,
                               rx=3, ry=3))
            
            # Count & percentage label
            if count > 0:
                drawing.add(String(chart_left + max_bar_width + 5, y + 2,
                                  f"{count} ({pct:.0f}%)",
                                  fontSize=6, fillColor=colors.HexColor("#64748B")))
        
        return drawing

    def _create_weekly_uas7_bar_chart(self):
        """Create a bar chart of weekly UAS7 scores."""
        weeks = self.stats.get("weekly_uas7", [])
        if not weeks:
            return Drawing(220, 100)
        
        # Show up to last 8 weeks
        recent_weeks = weeks[-8:]
        
        drawing = Drawing(220, 105)
        chart_left = 30
        chart_bottom = 22
        chart_width = 175
        chart_height = 70
        
        bar_width = chart_width / (len(recent_weeks) * 1.5 + 0.5)
        gap = bar_width * 0.5
        
        # Background
        drawing.add(Rect(chart_left, chart_bottom, chart_width, chart_height,
                        fillColor=colors.HexColor("#FAFAFA"), strokeColor=colors.HexColor("#E2E8F0"),
                        strokeWidth=0.3))
        
        # Grid lines
        for val in [0, 6, 15, 27, 42]:
            y = chart_bottom + (val / 42) * chart_height
            drawing.add(Line(chart_left, y, chart_left + chart_width, y,
                           strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.3))
            if val in [6, 15, 27, 42]:
                drawing.add(String(chart_left - 4, y - 3, str(val),
                                  fontSize=5.5, fillColor=colors.HexColor("#94A3B8"),
                                  textAnchor="end"))
        
        # Bars
        for i, week in enumerate(recent_weeks):
            x = chart_left + gap + i * (bar_width + gap)
            bar_h = (week["uas7"] / 42) * chart_height
            
            if week.get("complete"):
                uas7 = week["uas7"]
                if uas7 <= 6:
                    bar_color = colors.HexColor("#22C55E")
                elif uas7 <= 15:
                    bar_color = colors.HexColor("#84CC16")
                elif uas7 <= 27:
                    bar_color = colors.HexColor("#F59E0B")
                else:
                    bar_color = colors.HexColor("#EF4444")
            else:
                bar_color = colors.HexColor("#CBD5E1")
            
            drawing.add(Rect(x, chart_bottom, bar_width, max(2, bar_h),
                           fillColor=bar_color, strokeColor=None, rx=2, ry=2))
            
            # Value on top
            drawing.add(String(x + bar_width / 2, chart_bottom + max(2, bar_h) + 2,
                              str(week["uas7"]),
                              fontSize=5.5, fillColor=colors.HexColor("#475569"),
                              textAnchor="middle", fontName="Helvetica-Bold"))
            
            # Week label
            drawing.add(String(x + bar_width / 2, chart_bottom - 10,
                              week["week_start"].strftime("%d/%m"),
                              fontSize=5, fillColor=colors.HexColor("#94A3B8"),
                              textAnchor="middle"))
        
        return drawing

    def _create_itch_hive_comparison_chart(self):
        """Create a comparison chart showing itch vs hive scores over time."""
        drawing = Drawing(480, 100)
        
        if len(self.entries) < 2:
            return drawing
        
        chart_left = 45
        chart_bottom = 20
        chart_width = 400
        chart_height = 65
        
        # Background
        drawing.add(Rect(chart_left, chart_bottom, chart_width, chart_height,
                        fillColor=colors.HexColor("#FAFAFA"), strokeColor=colors.HexColor("#E2E8F0"),
                        strokeWidth=0.3))
        
        max_entries = min(len(self.entries), 60)
        recent = self.entries[-max_entries:]
        x_step = chart_width / max(1, len(recent) - 1)
        y_scale = chart_height / 3
        
        # Build itch and hive point arrays
        itch_points = []
        hive_points = []
        for i, entry in enumerate(recent):
            x = chart_left + i * x_step
            if entry.itch_score is not None:
                itch_points.append((x, chart_bottom + entry.itch_score * y_scale))
            if entry.hive_count_score is not None:
                hive_points.append((x, chart_bottom + entry.hive_count_score * y_scale))
        
        # Draw smooth curves for each
        for points, color_hex, label in [
            (itch_points, "#EC4899", "Itch"),
            (hive_points, "#3B82F6", "Hives"),
        ]:
            if len(points) >= 3:
                line_path = Path()
                line_path.moveTo(points[0][0], points[0][1])
                for i in range(len(points) - 1):
                    p0 = points[max(0, i - 1)]
                    p1 = points[i]
                    p2 = points[min(len(points) - 1, i + 1)]
                    p3 = points[min(len(points) - 1, i + 2)]
                    tension = 0.3
                    cp1x = p1[0] + (p2[0] - p0[0]) * tension
                    cp1y = max(chart_bottom, min(chart_bottom + chart_height, p1[1] + (p2[1] - p0[1]) * tension))
                    cp2x = p2[0] - (p3[0] - p1[0]) * tension
                    cp2y = max(chart_bottom, min(chart_bottom + chart_height, p2[1] - (p3[1] - p1[1]) * tension))
                    line_path.curveTo(cp1x, cp1y, cp2x, cp2y, p2[0], p2[1])
                line_path.strokeColor = colors.HexColor(color_hex)
                line_path.strokeWidth = 1.5
                line_path.fillColor = None
                drawing.add(line_path)
            elif len(points) == 2:
                drawing.add(Line(points[0][0], points[0][1], points[1][0], points[1][1],
                               strokeColor=colors.HexColor(color_hex), strokeWidth=1.5))
        
        # Y-axis labels
        for i in range(4):
            y = chart_bottom + i * y_scale
            drawing.add(String(chart_left - 8, y - 3, str(i), fontSize=6,
                              fillColor=colors.HexColor("#64748B"), textAnchor="end"))
        
        # Legend
        legend_x = chart_left + 10
        legend_y = chart_bottom + chart_height + 6
        drawing.add(Line(legend_x, legend_y + 3, legend_x + 15, legend_y + 3,
                        strokeColor=colors.HexColor("#EC4899"), strokeWidth=2))
        drawing.add(String(legend_x + 18, legend_y, "Itch Score", fontSize=6,
                          fillColor=colors.HexColor("#64748B")))
        drawing.add(Line(legend_x + 75, legend_y + 3, legend_x + 90, legend_y + 3,
                        strokeColor=colors.HexColor("#3B82F6"), strokeWidth=2))
        drawing.add(String(legend_x + 93, legend_y, "Hive Score", fontSize=6,
                          fillColor=colors.HexColor("#64748B")))
        
        return drawing


def export_my_data_csv(user):
    """
    Export ALL data we hold on a user as a comprehensive CSV file.

    This is a data-portability / subject-access export available to every
    user regardless of subscription tier.  It includes:
    - Account & profile information
    - Medications
    - All daily symptom entries (no date restriction)
    - Notification preferences
    - Subscription details

    Returns an HttpResponse with the CSV attachment.
    """
    from accounts.models import Profile, UserMedication
    from notifications.models import ReminderPreferences

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    safe_email = (user.email or f"user_{user.id}").replace("@", "_").replace(".", "_")[:30]
    filename = f"my_data_{safe_email}_{timezone.now().strftime('%Y%m%d')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # ------------------------------------------------------------------
    # Section 1 – Account Information
    # ------------------------------------------------------------------
    writer.writerow(["MY DATA EXPORT"])
    writer.writerow([f"Generated on {timezone.now().strftime('%d %B %Y at %H:%M')} UTC"])
    writer.writerow([f"This file contains all the data we hold about your account."])
    writer.writerow([])

    writer.writerow(["ACCOUNT INFORMATION"])
    writer.writerow(["Field", "Value"])
    writer.writerow(["Email", user.email])
    writer.writerow(["First Name", user.first_name or ""])
    writer.writerow(["Last Name", user.last_name or ""])
    writer.writerow(["Date Joined", user.date_joined.strftime("%Y-%m-%d %H:%M") if user.date_joined else ""])
    writer.writerow(["Last Login", user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else ""])
    writer.writerow([])

    # ------------------------------------------------------------------
    # Section 2 – Profile
    # ------------------------------------------------------------------
    writer.writerow(["PROFILE"])
    writer.writerow(["Field", "Value"])
    try:
        profile = user.profile
        writer.writerow(["Display Name", profile.display_name or ""])
        writer.writerow(["Date of Birth", profile.date_of_birth.strftime("%Y-%m-%d") if profile.date_of_birth else ""])
        writer.writerow(["Age", profile.age if profile.age else ""])
        writer.writerow(["Gender", profile.gender or ""])
        writer.writerow(["CSU Diagnosis", profile.csu_diagnosis or ""])
        writer.writerow(["Has Prescribed Medication", profile.has_prescribed_medication or ""])
        writer.writerow(["Preferred Score Scale", profile.preferred_score_scale or ""])
        writer.writerow(["Date Format", profile.date_format or ""])
        writer.writerow(["Timezone", profile.default_timezone or ""])
        writer.writerow(["Allow Data Collection", "Yes" if profile.allow_data_collection else "No"])
        writer.writerow(["Privacy Consent Given", "Yes" if profile.privacy_consent_given else "No"])
        writer.writerow(["Privacy Consent Date", profile.privacy_consent_date.strftime("%Y-%m-%d %H:%M") if profile.privacy_consent_date else ""])
        writer.writerow(["Account Paused", "Yes" if profile.account_paused else "No"])
        writer.writerow(["Onboarding Completed", "Yes" if profile.onboarding_completed else "No"])
    except Profile.DoesNotExist:
        writer.writerow(["(no profile found)"])
    writer.writerow([])

    # ------------------------------------------------------------------
    # Section 3 – Medications
    # ------------------------------------------------------------------
    medications = UserMedication.objects.filter(user=user).order_by("-is_current", "-updated_at")
    writer.writerow(["MEDICATIONS"])
    if medications.exists():
        writer.writerow([
            "Medication Name", "Type", "Dose", "Unit",
            "Frequency/Day", "Last Injection Date", "Injection Frequency",
            "Next Estimated Injection Date", "Currently Taking", "Added On",
        ])
        for med in medications:
            next_inj = med.next_injection_date
            writer.writerow([
                med.display_name,
                med.get_medication_type_display(),
                med.dose_amount or "",
                med.dose_unit or "",
                med.frequency_per_day or "",
                med.last_injection_date.strftime("%Y-%m-%d") if med.last_injection_date else "",
                med.get_injection_frequency_display() if med.injection_frequency else "",
                next_inj.strftime("%Y-%m-%d") if next_inj else "",
                "Yes" if med.is_current else "No",
                med.created_at.strftime("%Y-%m-%d") if med.created_at else "",
            ])
    else:
        writer.writerow(["(no medications recorded)"])
    writer.writerow([])

    # ------------------------------------------------------------------
    # Section 4 – Daily Symptom Entries (ALL – no date restriction)
    # ------------------------------------------------------------------
    entries = DailyEntry.objects.filter(user=user).order_by("date")
    writer.writerow(["DAILY SYMPTOM ENTRIES"])
    writer.writerow([f"Total entries: {entries.count()}"])
    if entries.exists():
        writer.writerow([
            "Date", "Day of Week", "Total Score (0-6)",
            "Itch Score (0-3)", "Hive Score (0-3)",
            "Antihistamine Taken",
            "QoL Sleep (0-4)", "QoL Activities (0-4)",
            "QoL Appearance (0-4)", "QoL Mood (0-4)",
            "Notes",
        ])
        for entry in entries.iterator():
            writer.writerow([
                entry.date.strftime("%Y-%m-%d"),
                entry.date.strftime("%A"),
                entry.score,
                entry.itch_score if entry.itch_score is not None else "",
                entry.hive_count_score if entry.hive_count_score is not None else "",
                "Yes" if entry.took_antihistamine else "No",
                entry.qol_sleep if entry.qol_sleep is not None else "",
                entry.qol_daily_activities if entry.qol_daily_activities is not None else "",
                entry.qol_appearance if entry.qol_appearance is not None else "",
                entry.qol_mood if entry.qol_mood is not None else "",
                entry.notes or "",
            ])
    else:
        writer.writerow(["(no symptom entries recorded)"])
    writer.writerow([])

    # ------------------------------------------------------------------
    # Section 5 – Notification Preferences
    # ------------------------------------------------------------------
    writer.writerow(["NOTIFICATION PREFERENCES"])
    try:
        prefs = ReminderPreferences.objects.get(user=user)
        writer.writerow(["Field", "Value"])
        writer.writerow(["Reminders Enabled", "Yes" if prefs.enabled else "No"])
        writer.writerow(["Reminder Time", prefs.time_of_day.strftime("%H:%M") if prefs.time_of_day else ""])
        writer.writerow(["Timezone", prefs.timezone or ""])
    except ReminderPreferences.DoesNotExist:
        writer.writerow(["(no notification preferences set)"])
    writer.writerow([])

    # ------------------------------------------------------------------
    # Section 6 – Subscription
    # ------------------------------------------------------------------
    writer.writerow(["SUBSCRIPTION"])
    try:
        sub = user.subscription
        writer.writerow(["Field", "Value"])
        writer.writerow(["Plan", sub.plan.name if sub.plan else "Free"])
        writer.writerow(["Status", sub.status or ""])
        writer.writerow(["Current Period Start", sub.current_period_start.strftime("%Y-%m-%d") if sub.current_period_start else ""])
        writer.writerow(["Current Period End", sub.current_period_end.strftime("%Y-%m-%d") if sub.current_period_end else ""])
    except Exception:
        writer.writerow(["Plan", "Free"])
    writer.writerow([])

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    writer.writerow(["END OF DATA EXPORT"])
    writer.writerow(["If you believe any data is missing or incorrect, please contact support."])

    return response
