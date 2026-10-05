"""ReportLab PDF builders: customer statements and generic report tables."""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

styles = getSampleStyleSheet()


def _doc(buffer, title):
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=title,
    )
    return doc


def _styled_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d4d4d8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f5")]),
        ("ALIGN", (-2, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def customer_statement_pdf(*, settings_obj, customer, lines, closing_balance):
    buffer = io.BytesIO()
    doc = _doc(buffer, f"Statement — {customer.name}")
    story = [
        Paragraph(settings_obj.shop_name, styles["Title"]),
        Paragraph(settings_obj.address or "", styles["Normal"]),
        Paragraph(settings_obj.phone or "", styles["Normal"]),
        Spacer(1, 8 * mm),
        Paragraph(f"Statement for: <b>{customer.name}</b>", styles["Heading2"]),
        Paragraph(f"Phone: {customer.phone or '—'} &nbsp;&nbsp; Address: {customer.address or '—'}", styles["Normal"]),
        Spacer(1, 5 * mm),
    ]
    data = [["Date", "Description", "Reference", "Debit", "Credit", "Balance"]]
    for line in lines:
        data.append([
            line["date"].strftime("%Y-%m-%d %H:%M"),
            line["kind"],
            str(line["ref"]),
            f'{line["debit"]:.2f}' if line["debit"] else "",
            f'{line["credit"]:.2f}' if line["credit"] else "",
            f'{line["balance"]:.2f}',
        ])
    data.append(["", "", "", "", "Closing balance:", f"{closing_balance:.2f}"])
    story.append(_styled_table(data, col_widths=[32 * mm, 45 * mm, 40 * mm, 20 * mm, 20 * mm, 22 * mm]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(settings_obj.receipt_footer or "", styles["Italic"]))
    doc.build(story)
    return buffer.getvalue()


def generic_report_pdf(*, settings_obj, title, headers, rows, totals_row=None):
    buffer = io.BytesIO()
    doc = _doc(buffer, title)
    story = [
        Paragraph(settings_obj.shop_name, styles["Title"]),
        Paragraph(title, styles["Heading2"]),
        Spacer(1, 5 * mm),
    ]
    data = [headers] + rows
    if totals_row:
        data.append(totals_row)
    story.append(_styled_table(data))
    doc.build(story)
    return buffer.getvalue()
