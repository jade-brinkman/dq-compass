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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image,
)
from reportlab.lib.enums import TA_LEFT

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

BRAND_RED = colors.HexColor("#E2001A")
BRAND_BLACK = colors.HexColor("#1A1A1A")
GREY = colors.HexColor("#5C5C5C")
GREEN = colors.HexColor("#00CC96")
ORANGE = colors.HexColor("#FFA15A")
RED = colors.HexColor("#EF553B")

STATUS_COLORS = {"PASS": GREEN, "FAIL": RED, "ERROR": ORANGE}
MPL_STATUS_COLORS = {"PASS": "#00CC96", "FAIL": "#EF553B", "ERROR": "#FFA15A"}


def _status_row_colors(statuses):
    return [STATUS_COLORS.get(s, GREY) for s in statuses]


# ---------------------------------------------------------------------------
# BF-REP-01 — traffic-light scorecard, same rule as the Streamlit report
# (pages/3_Quality_Report.py::_traffic_light) so a rule's color never changes
# depending on whether you're looking at the app or the PDF export:
#   green  : failed_records == 0
#   red    : severity High and failing, OR failure rate >= 5%
#   orange : failing, severity Medium/Low, failure rate < 5%, or a
#            configuration ERROR (not a data failure)
# BNF-04 caps the report at 3 colors.
# ---------------------------------------------------------------------------
_TRAFFIC_LIGHT_HEX = {"green": "#00CC96", "orange": "#FFA15A", "red": "#EF553B"}


def _traffic_light_pdf(row) -> str:
    """Returns a hex color string ('#RRGGBB'), usable both in ReportLab
    TableStyle commands (via colors.HexColor(...)) and inline in Paragraph
    markup (<font color='...'>)."""
    status = row.get("status")
    if status == "ERROR":
        return _TRAFFIC_LIGHT_HEX["orange"]

    try:
        failed = int(row.get("failed_records"))
    except (TypeError, ValueError):
        failed = 0
    try:
        total = int(row.get("total_records"))
    except (TypeError, ValueError):
        total = 0

    if failed == 0:
        return _TRAFFIC_LIGHT_HEX["green"]
    if row.get("severity") == "High":
        return _TRAFFIC_LIGHT_HEX["red"]

    fail_rate = (failed / total * 100) if total else 100.0
    return _TRAFFIC_LIGHT_HEX["orange"] if fail_rate < 5 else _TRAFFIC_LIGHT_HEX["red"]


def _create_pie_chart_image(summary_df) -> bytes:
    """Create a pie chart showing PASS/FAIL/ERROR breakdown as PNG bytes using matplotlib."""
    status_counts = summary_df['status'].value_counts()

    if status_counts.empty:
        return None

    fig, ax = plt.subplots(figsize=(5, 4))

    # Get colors in the right order
    chart_colors = [MPL_STATUS_COLORS.get(s, '#888888') for s in status_counts.index]

    # Create donut chart
    wedges, texts, autotexts = ax.pie(
        status_counts.values,
        labels=status_counts.index,
        colors=chart_colors,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops=dict(width=0.6),
        textprops={'fontsize': 10}
    )

    # Style the percentage text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title('Status Breakdown', fontsize=12, fontweight='bold', pad=10)

    # Save to bytes
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _create_dimension_chart_image(summary_df) -> bytes:
    """Create a bar chart showing results by quality dimension as PNG bytes using matplotlib."""
    dim_status = summary_df.groupby(['dimension', 'status']).size().unstack(fill_value=0)

    if dim_status.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, 4))

    # Prepare data
    dimensions = dim_status.index.tolist()
    x = np.arange(len(dimensions))
    width = 0.25

    # Plot bars for each status
    statuses = ['PASS', 'FAIL', 'ERROR']
    for i, status in enumerate(statuses):
        if status in dim_status.columns:
            values = dim_status[status].values
            color = MPL_STATUS_COLORS.get(status, '#888888')
            ax.bar(x + i * width, values, width, label=status, color=color)

    ax.set_xlabel('')
    ax.set_ylabel('Rules', fontsize=10)
    ax.set_title('Results by Quality Dimension', fontsize=12, fontweight='bold', pad=10)
    ax.set_xticks(x + width)
    ax.set_xticklabels(dimensions, rotation=45, ha='right', fontsize=9)
    ax.legend(loc='upper right', fontsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis='y', alpha=0.3)

    # Save to bytes
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _create_severity_chart_image(summary_df) -> bytes:
    """Create a bar chart showing results by severity as PNG bytes using matplotlib."""
    severity_status = summary_df.groupby(['severity', 'status']).size().unstack(fill_value=0)

    if severity_status.empty:
        return None

    # Reorder to High, Medium, Low
    severity_order = ['High', 'Medium', 'Low']
    severity_status = severity_status.reindex([s for s in severity_order if s in severity_status.index])

    fig, ax = plt.subplots(figsize=(5, 3.5))

    # Prepare data
    severities = severity_status.index.tolist()
    x = np.arange(len(severities))
    width = 0.25

    # Plot bars for each status
    statuses = ['PASS', 'FAIL', 'ERROR']
    for i, status in enumerate(statuses):
        if status in severity_status.columns:
            values = severity_status[status].values
            color = MPL_STATUS_COLORS.get(status, '#888888')
            ax.bar(x + i * width, values, width, label=status, color=color)

    ax.set_xlabel('Severity', fontsize=10)
    ax.set_ylabel('Number of rules', fontsize=10)
    ax.set_title('Results by Severity', fontsize=12, fontweight='bold', pad=10)
    ax.set_xticks(x + width)
    ax.set_xticklabels(severities, fontsize=10)
    ax.legend(loc='upper right', fontsize=9)
    ax.set_axisbelow(True)
    ax.grid(axis='y', alpha=0.3)

    # Save to bytes
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    text = str(text) if text else ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 2] + ".."


def generate_pdf_report(results: dict, filename: str, total_rules: int, passed: int,
                         failed: int, errors: int, pass_rate: float) -> bytes:
    """Builds a compact PDF quality report and returns it as bytes, ready for
    st.download_button()."""
    buffer = io.BytesIO()
    # Use portrait A4
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15 * mm, bottomMargin=12 * mm, leftMargin=12 * mm, rightMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DQTitle", parent=styles["Title"], textColor=BRAND_BLACK, fontSize=18, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DQSubtitle", parent=styles["Normal"], textColor=BRAND_RED, fontSize=10,
        spaceAfter=10, fontName="Helvetica-Bold",
    )
    h2_style = ParagraphStyle(
        "DQH2", parent=styles["Heading2"], textColor=BRAND_BLACK, fontSize=12, spaceBefore=10, spaceAfter=5,
    )
    normal_style = styles["Normal"]
    small_style = ParagraphStyle("DQSmall", parent=styles["Normal"], fontSize=8, textColor=GREY)
    # Style for table cell text with word wrap
    cell_style = ParagraphStyle("DQCell", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_LEFT)

    story = []

    # --- Header ---
    story.append(Paragraph("DQ Compass — Data Quality Report", title_style))
    story.append(Paragraph("Universal Data Quality Platform", subtitle_style))

    run_id = results.get("run_id", "n/a")
    timestamp = results.get("timestamp", datetime.now().isoformat(timespec="seconds"))
    # Truncate filename if too long
    display_filename = _truncate(filename, 60)
    meta_table = Table(
        [
            ["File", display_filename],
            ["Run ID", run_id],
            ["Timestamp", timestamp],
            ["Report generated", datetime.now().isoformat(timespec="seconds")],
        ],
        colWidths=[35 * mm, 150 * mm],
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
    overview_table = Table(overview_data, colWidths=[37 * mm] * 5)
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

    # Get summary DataFrame for charts and tables
    summary_df = results["summary"]

    # --- Scorecard (BF-REP-01) ---
    story.append(Spacer(1, 8))
    story.append(Paragraph("Scorecard", h2_style))
    story.append(Paragraph(
        "Green = no failure &nbsp;-&nbsp; Orange = failing, Medium/Low severity, under 5% "
        "failure rate, or a configuration error &nbsp;-&nbsp; Red = High severity failure, "
        "or failure rate at/above 5%",
        small_style,
    ))
    story.append(Spacer(1, 4))

    badge_style = ParagraphStyle(
        "DQBadge", parent=styles["Normal"], fontSize=8, leading=10, textColor=BRAND_BLACK,
    )
    n_cols = 4
    badge_rows = []
    current_row = []
    for _, r in summary_df.iterrows():
        dot_hex = _traffic_light_pdf(r)
        label = f"<font color='{dot_hex}'>●</font> {_truncate(str(r.get('rule_id', '')), 14)} " \
                f"<font color='#999999'>· {_truncate(str(r.get('dimension', '')), 14)}</font>"
        current_row.append(Paragraph(label, badge_style))
        if len(current_row) == n_cols:
            badge_rows.append(current_row)
            current_row = []
    if current_row:
        while len(current_row) < n_cols:
            current_row.append("")
        badge_rows.append(current_row)

    if badge_rows:
        badge_table = Table(badge_rows, colWidths=[46.5 * mm] * n_cols)
        badge_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#EEEEEE")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(badge_table)

    # --- Charts section ---
    story.append(Paragraph("Charts", h2_style))

    # Generate chart images
    try:
        pie_img_bytes = _create_pie_chart_image(summary_df)
        dim_img_bytes = _create_dimension_chart_image(summary_df)

        # Create a table to place charts side by side
        chart_row = []

        # In portrait mode, stack charts vertically (one per row)
        if pie_img_bytes:
            pie_img = Image(io.BytesIO(pie_img_bytes), width=90 * mm, height=70 * mm)
            chart_row.append(pie_img)

        if dim_img_bytes:
            dim_img = Image(io.BytesIO(dim_img_bytes), width=90 * mm, height=70 * mm)
            chart_row.append(dim_img)

        if chart_row:
            # Place 2 charts side by side if both exist
            charts_table = Table([chart_row], colWidths=[93 * mm] * len(chart_row))
            charts_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(charts_table)
            story.append(Spacer(1, 5))

        # Severity chart (centered)
        severity_img_bytes = _create_severity_chart_image(summary_df)
        if severity_img_bytes:
            severity_img = Image(io.BytesIO(severity_img_bytes), width=100 * mm, height=70 * mm)
            severity_table = Table([[severity_img]], colWidths=[186 * mm])
            severity_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(severity_table)

    except Exception as e:
        # If chart generation fails, skip charts and show error
        story.append(Paragraph(
            f"Charts could not be generated. Error: {str(e)[:150]}",
            small_style
        ))

    story.append(Spacer(1, 10))

    # --- Detailed results ---
    story.append(Paragraph("Detailed results", h2_style))

    # Use Paragraph objects for cells that may contain long text to enable word wrap
    header = ["Status", "Rule ID", "Name", "Dimension", "Severity", "Total", "Failed", "KPI"]
    rows = [header]
    for _, r in summary_df.iterrows():
        # Truncate long values to prevent overflow
        control_name = _truncate(r.get("control_name", ""), 40)
        rule_id = _truncate(r.get("rule_id", ""), 15)
        kpi_val = str(r.get("kpi_value", ""))
        if len(kpi_val) > 12:
            kpi_val = kpi_val[:10] + ".."

        rows.append([
            str(r.get("status", "")),
            rule_id,
            Paragraph(control_name, cell_style),
            _truncate(r.get("dimension", ""), 18),
            str(r.get("severity", "")),
            str(r.get("total_records", "")),
            str(r.get("failed_records", "")),
            kpi_val,
        ])

    # Portrait A4 = 210mm wide, minus 24mm margins = 186mm available
    # Adjusted column widths for portrait mode
    detail_table = Table(
        rows,
        colWidths=[14 * mm, 20 * mm, 50 * mm, 28 * mm, 18 * mm, 18 * mm, 18 * mm, 20 * mm],
        repeatRows=1
    )
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (5, 0), (7, -1), "RIGHT"),  # Align numbers to the right
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
            exc_rows.append([
                _truncate(rule_id, 20),
                Paragraph(_truncate(r["control_name"], 60), cell_style),
                str(count)
            ])
        exc_table = Table(exc_rows, colWidths=[30 * mm, 126 * mm, 30 * mm])
        exc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
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
