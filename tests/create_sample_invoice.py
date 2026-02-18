"""
Generates a sample invoice PDF for testing.
Run: python tests/create_sample_invoice.py
Requires: pip install reportlab
"""

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
    )
except ImportError:
    print("Install reportlab first: pip install reportlab")
    raise SystemExit(1)

import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "sample_invoice.pdf")


def build_invoice():
    doc = SimpleDocTemplate(OUTPUT_PATH, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>INVOICE</b>", styles["Title"]))
    story.append(Spacer(1, 6 * mm))

    meta = [
        ["Invoice No:", "INV-2024-0042", "Invoice Date:", "2024-03-15"],
        ["Vendor:", "Acme Corp Ltd", "Due Date:", "2024-04-14"],
        ["Address:", "123 Business Ave, NY 10001", "PO Number:", "PO-9981"],
        ["Email:", "billing@acmecorp.com", "Currency:", "USD"],
        ["Phone:", "+1 (555) 123-4567", "Tax ID:", "US-12-3456789"],
    ]
    meta_table = Table(meta, colWidths=[35 * mm, 70 * mm, 35 * mm, 50 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10 * mm))

    # ── Bill To ─────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Bill To:</b>", styles["Normal"]))
    story.append(Paragraph("TechStart Inc.", styles["Normal"]))
    story.append(Paragraph("456 Startup Road, San Francisco, CA 94107", styles["Normal"]))
    story.append(Paragraph("accounts@techstart.io", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    # ── Line Items ──────────────────────────────────────────────────────────
    items = [
        ["#", "Description", "Qty", "Unit Price", "Total"],
        ["1", "Web Development Services (March 2024)", "40", "$150.00", "$6,000.00"],
        ["2", "UI/UX Design Consultation", "8", "$200.00", "$1,600.00"],
        ["3", "Cloud Infrastructure Setup", "1", "$500.00", "$500.00"],
        ["4", "Monthly Maintenance Plan", "1", "$299.00", "$299.00"],
    ]
    item_table = Table(
        items,
        colWidths=[10 * mm, 90 * mm, 15 * mm, 30 * mm, 30 * mm],
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 8 * mm))

    # ── Totals ──────────────────────────────────────────────────────────────
    totals = [
        ["", "", "Subtotal:", "$8,399.00"],
        ["", "", "Tax (10%):", "$839.90"],
        ["", "", "Shipping:", "$0.00"],
        ["", "", "Discount:", "-$200.00"],
        ["", "", "TOTAL DUE:", "$9,038.90"],
    ]
    totals_table = Table(totals, colWidths=[10 * mm, 90 * mm, 45 * mm, 30 * mm])
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (2, -1), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 10 * mm))

    # ── Footer ──────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Payment Terms:</b> Net 30", styles["Normal"]))
    story.append(Paragraph("<b>Payment Method:</b> Bank Transfer", styles["Normal"]))
    story.append(
        Paragraph(
            "<b>Bank Account:</b> Acme Corp | Routing: 021000021 | Account: 987654321",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "Thank you for your business! For questions, contact billing@acmecorp.com",
            styles["Normal"],
        )
    )

    doc.build(story)
    print(f"✅ Sample invoice created: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_invoice()
