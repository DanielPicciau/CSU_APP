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
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle
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
    
    # Quality of life impact thresholds
    QOL_THRESHOLDS = {
        "minimal": (0, 6),
        "mild": (7, 15),
        "moderate": (16, 27),
        "severe": (28, 42),
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
        
        # Fetch data
        self.entries = self._fetch_entries()
        self.stats = self._calculate_stats()
        self.patterns = self._analyze_patterns()
        self.treatment_analysis = self._analyze_treatment_response()
    
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
        """Calculate UAS7 for complete weeks in the range."""
        weekly_scores = []
        entry_by_date = {e.date: e for e in self.entries}
        
        # Find the first Sunday in or before the range
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
    
    def export_pdf(self) -> HttpResponse:
        """Generate comprehensive clinical PDF report for NHS/healthcare providers."""
        response = HttpResponse(content_type="application/pdf")
        
        filename = self._generate_filename("pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        
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
        elements.append(Spacer(1, 12))
        
        # ========== EXECUTIVE SUMMARY BOX ==========
        category, category_color = self._get_current_disease_category()
        
        elements.append(Paragraph("EXECUTIVE SUMMARY", section_style))
        
        # Traffic light indicator
        summary_items = []
        
        # Disease Activity Status with traffic light
        if category == "Well Controlled":
            status_color = CLINICAL_GREEN
            status_icon = "●"
        elif category == "Mild Activity":
            status_color = colors.HexColor("#84CC16")
            status_icon = "●"
        elif category == "Moderate Activity":
            status_color = CLINICAL_AMBER
            status_icon = "●"
        elif category == "Severe Activity":
            status_color = CLINICAL_RED
            status_icon = "●"
        else:
            status_color = CLINICAL_GREY
            status_icon = "○"
        
        # Key metrics summary box
        summary_data = [
            [
                Paragraph(f"<font color='{status_color.hexval()}'><b>{status_icon}</b></font> <b>Disease Activity:</b> {category}", normal_style),
                Paragraph(f"<b>Tracking Adherence:</b> {self.stats['adherence_pct']:.0f}%", normal_style),
            ],
            [
                Paragraph(f"<b>Mean Daily Score:</b> {self.stats['avg_score']:.1f}/6", normal_style),
                Paragraph(f"<b>Days Recorded:</b> {self.stats['logged_days']}/{self.stats['total_days']}", normal_style),
            ],
        ]
        
        if self.patterns:
            summary_data.append([
                Paragraph(f"<b>Symptom-Free Days:</b> {self.patterns['symptom_free_days']} ({self.patterns['symptom_free_pct']:.0f}%)", normal_style),
                Paragraph(f"<b>Severe Days (≥5):</b> {self.patterns['severe_days']} ({self.patterns['severe_pct']:.0f}%)", normal_style),
            ])
            trend_text = self.patterns['trend'].replace('_', ' ').title()
            summary_data.append([
                Paragraph(f"<b>Disease Trend:</b> {trend_text}", normal_style),
                Paragraph(f"<b>Longest Remission:</b> {self.patterns['longest_remission_streak']} days", normal_style),
            ])
        
        if self.treatment_analysis:
            summary_data.append([
                Paragraph(f"<b>H1-Antihistamine Response:</b> {self.treatment_analysis['response_category']}", normal_style),
                Paragraph(f"<b>Medication Adherence:</b> {self.treatment_analysis['adherence_rate']:.0f}%", normal_style),
            ])
        
        summary_table = Table(summary_data, colWidths=[240, 240])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, NHS_LIGHT_BLUE),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 8))
        
        # ========== CLINICAL GUIDANCE BOX ==========
        if self.include_clinical_guidance and category in self.CLINICAL_GUIDANCE:
            guidance = self.CLINICAL_GUIDANCE[category]
            elements.append(Paragraph("CLINICAL GUIDANCE (per EAACI/GA²LEN/EuroGuiDerm 2021)", subsection_style))
            
            guidance_text = f"""
            <b>Assessment:</b> {guidance['description']}<br/>
            <b>Suggested Action:</b> {guidance['recommendation']}<br/>
            <b>Recommended Review Interval:</b> {guidance['review_interval']}
            """
            elements.append(Paragraph(guidance_text.strip(), clinical_note_style))
            elements.append(Spacer(1, 6))
        
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
            f"CSU Tracker Clinical Report • Generated: {timezone.now().strftime('%d %B %Y at %H:%M')} • "
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
        """Create an enhanced clinical trend chart showing score trend with severity zones."""
        drawing = Drawing(480, 180)
        
        # Background with severity zones
        chart_left = 45
        chart_bottom = 35
        chart_width = 400
        chart_height = 120
        
        # Severity zone backgrounds (bottom to top)
        zone_height = chart_height / 3
        
        # Well controlled zone (0-2)
        drawing.add(Rect(chart_left, chart_bottom, chart_width, zone_height, 
                        fillColor=colors.HexColor("#DCFCE7"), strokeColor=None))
        # Moderate zone (2-4)
        drawing.add(Rect(chart_left, chart_bottom + zone_height, chart_width, zone_height,
                        fillColor=colors.HexColor("#FEF9C3"), strokeColor=None))
        # Severe zone (4-6)
        drawing.add(Rect(chart_left, chart_bottom + zone_height * 2, chart_width, zone_height,
                        fillColor=colors.HexColor("#FEE2E2"), strokeColor=None))
        
        # Chart border
        drawing.add(Rect(chart_left, chart_bottom, chart_width, chart_height,
                        fillColor=None, strokeColor=colors.HexColor("#9CA3AF"), strokeWidth=0.5))
        
        # Zone labels
        drawing.add(String(chart_left + chart_width + 5, chart_bottom + zone_height/2 - 4, "Well Controlled",
                          fontSize=6, fillColor=colors.HexColor("#166534")))
        drawing.add(String(chart_left + chart_width + 5, chart_bottom + zone_height * 1.5 - 4, "Moderate",
                          fontSize=6, fillColor=colors.HexColor("#A16207")))
        drawing.add(String(chart_left + chart_width + 5, chart_bottom + zone_height * 2.5 - 4, "Severe",
                          fontSize=6, fillColor=colors.HexColor("#DC2626")))
        
        # Prepare data points
        data_points = [(i, e.score) for i, e in enumerate(self.entries)]
        
        if not data_points:
            return drawing
        
        # Scale factors
        max_x = len(data_points) - 1 if len(data_points) > 1 else 1
        max_y = 6  # Max score is 6
        
        x_scale = chart_width / max_x
        y_scale = chart_height / max_y
        
        # Draw Y-axis labels and grid lines
        for y in range(0, 7):
            y_pos = chart_bottom + y * y_scale
            drawing.add(Line(
                chart_left, y_pos, chart_left + chart_width, y_pos,
                strokeColor=colors.HexColor("#D1D5DB"),
                strokeWidth=0.3
            ))
            drawing.add(String(
                chart_left - 8, y_pos - 3, str(y),
                fontSize=7, fillColor=colors.HexColor("#6B7280"),
                textAnchor="end"
            ))
        
        # Draw average line
        avg_y = chart_bottom + self.stats["avg_score"] * y_scale
        drawing.add(Line(
            chart_left, avg_y, chart_left + chart_width, avg_y,
            strokeColor=colors.HexColor("#6366F1"),
            strokeWidth=1,
            strokeDashArray=[4, 2]
        ))
        drawing.add(String(
            chart_left - 8, avg_y - 3, f"Avg",
            fontSize=6, fillColor=colors.HexColor("#6366F1"),
            textAnchor="end"
        ))
        
        # Draw line connecting points
        if len(data_points) >= 2:
            for i in range(len(data_points) - 1):
                x1 = chart_left + data_points[i][0] * x_scale
                y1 = chart_bottom + data_points[i][1] * y_scale
                x2 = chart_left + data_points[i + 1][0] * x_scale
                y2 = chart_bottom + data_points[i + 1][1] * y_scale
                
                drawing.add(Line(
                    x1, y1, x2, y2,
                    strokeColor=colors.HexColor("#1E40AF"),
                    strokeWidth=1.5
                ))
        
        # Draw points with color coding
        for i, (idx, score) in enumerate(data_points):
            x = chart_left + idx * x_scale
            y = chart_bottom + score * y_scale
            
            # Color based on score
            if score <= 2:
                point_color = colors.HexColor("#22C55E")
            elif score <= 4:
                point_color = colors.HexColor("#F59E0B")
            else:
                point_color = colors.HexColor("#EF4444")
            
            drawing.add(Circle(x, y, 3, fillColor=point_color, strokeColor=colors.white, strokeWidth=0.5))
        
        # X-axis labels
        if len(self.entries) > 0:
            # Determine appropriate label spacing
            if len(self.entries) <= 7:
                label_indices = list(range(len(self.entries)))
            elif len(self.entries) <= 14:
                label_indices = [0, len(self.entries)//2, len(self.entries)-1]
            else:
                # Show first, last, and a few in between
                step = len(self.entries) // 4
                label_indices = [0, step, step*2, step*3, len(self.entries)-1]
            
            for idx in label_indices:
                if idx < len(self.entries):
                    x = chart_left + idx * x_scale
                    date_str = self.entries[idx].date.strftime("%d %b")
                    drawing.add(String(
                        x, chart_bottom - 12, date_str,
                        fontSize=6, fillColor=colors.HexColor("#6B7280"),
                        textAnchor="middle"
                    ))
        
        # Y-axis title
        drawing.add(String(
            10, chart_bottom + chart_height / 2, "Daily Score",
            fontSize=7, fillColor=colors.HexColor("#374151"),
            textAnchor="middle"
        ))
        
        # Chart title
        drawing.add(String(
            chart_left + chart_width / 2, chart_bottom + chart_height + 12, 
            "Daily Symptom Score Trend",
            fontSize=9, fillColor=colors.HexColor("#1F2937"),
            textAnchor="middle",
            fontName="Helvetica-Bold"
        ))
        
        return drawing
    
    def _generate_filename(self, extension: str) -> str:
        """Generate a filename for the export."""
        date_range = f"{self.start_date.strftime('%Y%m%d')}-{self.end_date.strftime('%Y%m%d')}"
        
        if self.anonymize:
            return f"csu_clinical_report_{date_range}_anonymized.{extension}"
        else:
            # Handle cases where username or email might be None
            name = self.user.username or self.user.email or f"user_{self.user.id}"
            safe_name = name.replace(" ", "_").replace("@", "_")[:20]
            return f"csu_clinical_report_{safe_name}_{date_range}.{extension}"
