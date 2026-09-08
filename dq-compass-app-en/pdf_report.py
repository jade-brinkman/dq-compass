"""
pdf_report.py — Builds the downloadable PDF version of the quality report
(Quality Report page, Export section).

This is the PDF leg of the export flow described in the team's working
session: the tool must let the user hand a written report to the data
owner (CSV/JSON and PDF), so it can be escalated outside the app.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

BRAND_RED = colors.HexColor("#E2001A")
BRAND_BLACK = colors.HexColor("#1A1A1A")
GREY = colors.HexColor("#5C5C5C")
GREEN = colors.HexColor("#00CC96")
ORANGE = colors.HexColor("#FFA15A")
RED = colors.HexColor("#EF553B")

STATUS_COLORS = {"PASS": GREEN, "FAIL": RED, "ERROR": ORANGE}


def _status_row_colors(statuses):
    return [STATUS_COLORS.get(s, GREY) for s in statuses]


def generate_pdf_report(results: dict, filename: str, total_rules: int, passed: int,
                         failed: int, errors: int, pass_rate: float) -> bytes:
    """Builds a compact PDF quality report and returns it as bytes, ready for
    st.download_button()."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=15 * mm, leftMargin=15 * mm, rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DQTitle", parent=styles["Title"], textColor=BRAND_BLACK, fontSize=20, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DQSubtitle", parent=styles["Normal"], textColor=BRAND_RED, fontSize=11,
        spaceAfter=14, fontName="Helvetica-Bold",
    )
    h2_style = ParagraphStyle(
        "DQH2", parent=styles["Heading2"], textColor=BRAND_BLACK, fontSize=13, spaceBefore=14, spaceAfter=6,
    )
    normal_style = styles["Normal"]
    small_style = ParagraphStyle("DQSmall", parent=styles["Normal"], fontSize=8, textColor=GREY)

    story = []

    # --- Header ---
    story.append(Paragraph("DQ Compass — Data Quality Report", title_style))
    story.append(Paragraph("Universal Data Quality Platform", subtitle_style))

    run_id = results.get("run_id", "n/a")
    timestamp = results.get("timestamp", datetime.now().isoformat(timespec="seconds"))
    meta_table = Table(
        [
            ["File", filename],
            ["Run ID", run_id],
            ["Timestamp", timestamp],
            ["Report generated", datetime.now().isoformat(timespec="seconds")],
        ],
        colWidths=[35 * mm, 130 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GREY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)

    # --- Overview ---
    story.append(Paragraph("Overview", h2_style))
    overview_data = [
        ["Total rules", "Passed", "Failed", "Errors", "Pass rate"],
        [str(total_rules), str(passed), str(failed), str(errors), f"{pass_rate:.1f}%"],
    ]
    overview_table = Table(overview_data, colWidths=[33 * mm] * 5)
    overview_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (2, 1), (2, 1), RED if failed else GREEN),
        ("TEXTCOLOR", (4, 1), (4, 1), GREEN if pass_rate >= 80 else (ORANGE if pass_rate >= 50 else RED)),
    ]))
    story.append(overview_table)

    # --- Detailed results ---
    story.append(Paragraph("Detailed results", h2_style))
    summary_df = results["summary"]
    header = ["Status", "Rule ID", "Name", "Dimension", "Severity", "Total", "Failed", "KPI"]
    rows = [header]
    for _, r in summary_df.iterrows():
        rows.append([
            str(r.get("status", "")),
            str(r.get("rule_id", "")),
            str(r.get("control_name", ""))[:32],
            str(r.get("dimension", "")),
            str(r.get("severity", "")),
            str(r.get("total_records", "")),
            str(r.get("failed_records", "")),
            f"{r.get('kpi_value', '')}",
        ])

    detail_table = Table(rows, colWidths=[16 * mm, 20 * mm, 42 * mm, 26 * mm, 18 * mm, 16 * mm, 16 * mm, 26 * mm], repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    row_colors = _status_row_colors(summary_df["status"].tolist())
    for i, color in enumerate(row_colors, start=1):
        style_cmds.append(("TEXTCOLOR", (0, i), (0, i), color))
        style_cmds.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))
    detail_table.setStyle(TableStyle(style_cmds))
    story.append(detail_table)

    # --- Exceptions summary (counts only, to keep the PDF compact) ---
    exceptions = results.get("exceptions", {})
    failed_rules = summary_df[summary_df["status"] == "FAIL"]
    if len(failed_rules) > 0:
        story.append(Paragraph("Exceptions summary", h2_style))
        story.append(Paragraph(
            "Full exception records are available in the CSV/JSON exports and in the "
            "evidence pack (audit trail). This PDF only lists the count per rule.",
            small_style,
        ))
        story.append(Spacer(1, 4))
        exc_rows = [["Rule ID", "Control name", "Exceptions"]]
        for _, r in failed_rules.iterrows():
            rule_id = r["rule_id"]
            count = len(exceptions.get(rule_id, [])) if rule_id in exceptions else int(r.get("failed_records") or 0)
            exc_rows.append([rule_id, str(r["control_name"])[:45], str(count)])
        exc_table = Table(exc_rows, colWidths=[25 * mm, 105 * mm, 30 * mm])
        exc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(exc_table)

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "DQ Compass — Universal Data Quality Platform. Generated automatically, "
        "no manual edit — safe to attach as-is to an escalation to the data owner.",
        small_style,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
