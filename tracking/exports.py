"""
Export functionality for CSU tracking data.
Generates CSV and PDF exports suitable for healthcare providers.
"""

import csv
import io
from datetime import date, timedelta
from typing import Optional

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker

from .models import DailyEntry


class CSUExporter:
    """
    Handles export of CSU tracking data in various formats.
    """
    
    ITCH_LABELS = {
        0: "None",
        1: "Mild",
        2: "Moderate", 
        3: "Severe",
    }
    
    HIVE_LABELS = {
        0: "None",
        1: "Mild (<20)",
        2: "Moderate (20-50)",
        3: "Severe (>50)",
    }
    
    UAS7_CATEGORIES = [
        (0, 6, "Well Controlled", "#22C55E"),
        (7, 15, "Mild Activity", "#84CC16"),
        (16, 27, "Moderate Activity", "#F59E0B"),
        (28, 42, "Severe Activity", "#EF4444"),
    ]
    
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
        
        # Fetch data
        self.entries = self._fetch_entries()
        self.stats = self._calculate_stats()
    
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
        """Generate CSV export."""
        response = HttpResponse(content_type="text/csv")
        
        filename = self._generate_filename("csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Header row
        headers = ["Date", "Day", "Total Score"]
        if self.include_breakdown:
            headers.extend(["Itch Score", "Itch Level", "Hive Score", "Hive Level"])
        if self.include_antihistamine:
            headers.append("Antihistamine")
        if self.include_notes:
            headers.append("Notes")
        
        writer.writerow(headers)
        
        # Data rows
        for entry in self.entries:
            row = [
                entry.date.isoformat(),
                entry.date.strftime("%A"),
                entry.score,
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
        
        # Add summary section
        writer.writerow([])
        writer.writerow(["--- SUMMARY ---"])
        writer.writerow(["Date Range", f"{self.start_date} to {self.end_date}"])
        writer.writerow(["Total Days", self.stats["total_days"]])
        writer.writerow(["Days Logged", self.stats["logged_days"]])
        writer.writerow(["Adherence", f"{self.stats['adherence_pct']:.1f}%"])
        writer.writerow(["Average Score", f"{self.stats['avg_score']:.2f}"])
        writer.writerow(["Score Range", f"{self.stats['min_score']} - {self.stats['max_score']}"])
        
        if self.include_antihistamine:
            writer.writerow(["Antihistamine Days", self.stats["antihistamine_days"]])
        
        # Weekly UAS7
        if self.stats["weekly_uas7"]:
            writer.writerow([])
            writer.writerow(["--- WEEKLY UAS7 ---"])
            writer.writerow(["Week", "UAS7 Score", "Status"])
            for week in self.stats["weekly_uas7"]:
                status = "Complete" if week["complete"] else f"Incomplete ({week.get('days_logged', 0)}/7 days)"
                writer.writerow([
                    f"{week['week_start']} - {week['week_end']}",
                    week["uas7"],
                    status,
                ])
        
        return response
    
    def export_pdf(self) -> HttpResponse:
        """Generate PDF export."""
        response = HttpResponse(content_type="application/pdf")
        
        filename = self._generate_filename("pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=25*mm,
        )
        
        # Build content
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=12,
            textColor=colors.HexColor("#4F46E5"),
        )
        
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#1F2937"),
        )
        
        normal_style = ParagraphStyle(
            "CustomNormal",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=6,
        )
        
        small_style = ParagraphStyle(
            "CustomSmall",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
        )
        
        # Title
        elements.append(Paragraph("CSU Symptom Report", title_style))
        elements.append(Spacer(1, 6))
        
        # Report metadata
        elements.append(Paragraph(
            f"<b>Patient:</b> {self._get_patient_identifier()}",
            normal_style
        ))
        elements.append(Paragraph(
            f"<b>Date Range:</b> {self.start_date.strftime('%B %d, %Y')} – {self.end_date.strftime('%B %d, %Y')}",
            normal_style
        ))
        elements.append(Paragraph(
            f"<b>Generated:</b> {timezone.now().strftime('%B %d, %Y at %H:%M')}",
            normal_style
        ))
        
        elements.append(Spacer(1, 12))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB")))
        elements.append(Spacer(1, 12))
        
        # Adherence Summary Section
        elements.append(Paragraph("Tracking Adherence", heading_style))
        
        adherence_data = [
            ["Total Days", "Days Logged", "Days Missing", "Adherence Rate"],
            [
                str(self.stats["total_days"]),
                str(self.stats["logged_days"]),
                str(self.stats["missing_days"]),
                f"{self.stats['adherence_pct']:.1f}%",
            ]
        ]
        
        adherence_table = Table(adherence_data, colWidths=[100, 100, 100, 100])
        adherence_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(adherence_table)
        elements.append(Spacer(1, 16))
        
        # Score Summary Section
        elements.append(Paragraph("Score Summary", heading_style))
        
        summary_data = [
            ["Average Score", "Lowest Score", "Highest Score"],
            [
                f"{self.stats['avg_score']:.1f}",
                str(self.stats["min_score"]),
                str(self.stats["max_score"]),
            ]
        ]
        
        if self.include_breakdown and self.stats["avg_itch"] is not None:
            summary_data[0].extend(["Avg Itch", "Avg Hives"])
            summary_data[1].extend([
                f"{self.stats['avg_itch']:.1f}",
                f"{self.stats['avg_hives']:.1f}" if self.stats["avg_hives"] else "N/A",
            ])
        
        if self.include_antihistamine:
            summary_data[0].append("Antihistamine Days")
            summary_data[1].append(str(self.stats["antihistamine_days"]))
        
        col_width = 400 / len(summary_data[0])
        summary_table = Table(summary_data, colWidths=[col_width] * len(summary_data[0]))
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 16))
        
        # Trend Chart
        if len(self.entries) >= 2:
            elements.append(Paragraph("Score Trend", heading_style))
            chart = self._create_trend_chart()
            elements.append(chart)
            elements.append(Spacer(1, 16))
        
        # Weekly UAS7 Section
        if self.stats["weekly_uas7"]:
            elements.append(Paragraph("Weekly UAS7 Scores", heading_style))
            
            uas7_header = ["Week", "UAS7", "Category", "Status"]
            uas7_data = [uas7_header]
            
            for week in self.stats["weekly_uas7"]:
                # Determine category
                category = "Incomplete"
                if week["complete"]:
                    for min_val, max_val, label, _ in self.UAS7_CATEGORIES:
                        if min_val <= week["uas7"] <= max_val:
                            category = label
                            break
                
                status = "✓ Complete" if week["complete"] else f"Partial ({week.get('days_logged', 0)}/7)"
                
                uas7_data.append([
                    f"{week['week_start'].strftime('%b %d')} – {week['week_end'].strftime('%b %d')}",
                    str(week["uas7"]),
                    category,
                    status,
                ])
            
            uas7_table = Table(uas7_data, colWidths=[120, 60, 120, 100])
            uas7_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(uas7_table)
            elements.append(Spacer(1, 16))
        
        # Daily Scores Table
        elements.append(Paragraph("Daily Score Log", heading_style))
        
        # Build table headers
        table_headers = ["Date", "Score"]
        if self.include_breakdown:
            table_headers.extend(["Itch", "Hives"])
        if self.include_antihistamine:
            table_headers.append("💊")
        if self.include_notes:
            table_headers.append("Notes")
        
        table_data = [table_headers]
        
        for entry in self.entries:
            row = [
                entry.date.strftime("%b %d, %Y"),
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
                notes = entry.notes[:50] + "..." if len(entry.notes) > 50 else entry.notes
                row.append(notes or "")
            
            table_data.append(row)
        
        # Calculate column widths
        if self.include_notes:
            if self.include_breakdown and self.include_antihistamine:
                col_widths = [70, 40, 50, 60, 25, 155]
            elif self.include_breakdown:
                col_widths = [80, 45, 55, 70, 150]
            elif self.include_antihistamine:
                col_widths = [90, 50, 30, 230]
            else:
                col_widths = [100, 60, 240]
        else:
            if self.include_breakdown and self.include_antihistamine:
                col_widths = [100, 60, 80, 100, 60]
            elif self.include_breakdown:
                col_widths = [120, 70, 100, 110]
            elif self.include_antihistamine:
                col_widths = [150, 100, 150]
            else:
                col_widths = [200, 200]
        
        daily_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        daily_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ]))
        elements.append(daily_table)
        
        # Notes section (if any entries have notes and notes are included)
        if self.include_notes:
            entries_with_notes = [e for e in self.entries if e.notes]
            if entries_with_notes:
                elements.append(Spacer(1, 16))
                elements.append(Paragraph("Patient Notes", heading_style))
                
                for entry in entries_with_notes[:10]:  # Limit to 10 notes
                    elements.append(Paragraph(
                        f"<b>{entry.date.strftime('%b %d, %Y')}:</b> {entry.notes}",
                        normal_style
                    ))
                
                if len(entries_with_notes) > 10:
                    elements.append(Paragraph(
                        f"<i>... and {len(entries_with_notes) - 10} more notes</i>",
                        small_style
                    ))
        
        # Disclaimer footer
        elements.append(Spacer(1, 24))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB")))
        elements.append(Spacer(1, 8))
        
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
            alignment=1,  # Center
        )
        
        elements.append(Paragraph(
            "<b>DISCLAIMER:</b> This report contains patient-recorded symptom data and is provided "
            "for informational purposes only. It is not intended to be a substitute for professional "
            "medical advice, diagnosis, or treatment. This data has not been verified by a healthcare "
            "professional and should be reviewed in the context of a clinical evaluation.",
            disclaimer_style
        ))
        
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(
            f"Generated by CSU Tracker • {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
            disclaimer_style
        ))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF from buffer
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
    
    def _create_trend_chart(self):
        """Create a simple line chart showing score trend."""
        drawing = Drawing(400, 150)
        
        # Background
        drawing.add(Rect(0, 0, 400, 150, fillColor=colors.HexColor("#FAFAFA"), strokeColor=None))
        
        # Prepare data points
        data_points = [(i, e.score) for i, e in enumerate(self.entries)]
        
        if not data_points:
            return drawing
        
        # Chart dimensions
        chart_left = 40
        chart_bottom = 30
        chart_width = 340
        chart_height = 100
        
        # Scale factors
        max_x = len(data_points) - 1 if len(data_points) > 1 else 1
        max_y = 6  # Max score is 6
        
        x_scale = chart_width / max_x
        y_scale = chart_height / max_y
        
        # Draw grid lines
        for y in range(0, 7, 2):
            y_pos = chart_bottom + y * y_scale
            drawing.add(Line(
                chart_left, y_pos, chart_left + chart_width, y_pos,
                strokeColor=colors.HexColor("#E5E7EB"),
                strokeDashArray=[2, 2]
            ))
            drawing.add(String(
                chart_left - 5, y_pos - 3, str(y),
                fontSize=8, fillColor=colors.HexColor("#6B7280"),
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
                    strokeColor=colors.HexColor("#4F46E5"),
                    strokeWidth=2
                ))
        
        # Draw points
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
            
            from reportlab.graphics.shapes import Circle
            drawing.add(Circle(x, y, 4, fillColor=point_color, strokeColor=colors.white, strokeWidth=1))
        
        # X-axis labels (show first, middle, last dates)
        if len(self.entries) > 0:
            label_indices = [0]
            if len(self.entries) > 2:
                label_indices.append(len(self.entries) // 2)
            if len(self.entries) > 1:
                label_indices.append(len(self.entries) - 1)
            
            for idx in label_indices:
                x = chart_left + idx * x_scale
                date_str = self.entries[idx].date.strftime("%b %d")
                drawing.add(String(
                    x, chart_bottom - 15, date_str,
                    fontSize=7, fillColor=colors.HexColor("#6B7280"),
                    textAnchor="middle"
                ))
        
        # Y-axis label
        drawing.add(String(
            10, chart_bottom + chart_height / 2, "Score",
            fontSize=8, fillColor=colors.HexColor("#6B7280"),
            textAnchor="middle"
        ))
        
        return drawing
    
    def _generate_filename(self, extension: str) -> str:
        """Generate a filename for the export."""
        date_range = f"{self.start_date.strftime('%Y%m%d')}-{self.end_date.strftime('%Y%m%d')}"
        
        if self.anonymize:
            return f"csu_report_{date_range}_anonymized.{extension}"
        else:
            # Handle cases where username or email might be None
            name = self.user.username or self.user.email or f"user_{self.user.id}"
            safe_name = name.replace(" ", "_").replace("@", "_")[:20]
            return f"csu_report_{safe_name}_{date_range}.{extension}"
