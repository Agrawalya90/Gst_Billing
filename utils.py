"""
utils.py — GST calculations, PDF invoice generation, Excel export
"""

import io
from datetime import datetime

import pandas as pd

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu & Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry"
]

GST_RATES = [0, 5, 12, 18, 28]


def calculate_line_item(price: float, qty: float, gst_percent: float, is_interstate: bool) -> dict:
    """
    Returns a dict with:
      base_amount, cgst_amount, sgst_amount, igst_amount, line_total
    """
    base = round(price * qty, 2)
    gst_amount = round(base * gst_percent / 100, 2)

    if is_interstate:
        cgst = sgst = 0.0
        igst = gst_amount
    else:
        cgst = sgst = round(gst_amount / 2, 2)
        igst = 0.0

    return {
        "base_amount":  base,
        "cgst_amount":  cgst,
        "sgst_amount":  sgst,
        "igst_amount":  igst,
        "line_total":   round(base + gst_amount, 2),
    }


def calculate_invoice_totals(items: list[dict]) -> dict:
    subtotal = sum(i["base_amount"] for i in items)
    cgst     = sum(i["cgst_amount"] for i in items)
    sgst     = sum(i["sgst_amount"] for i in items)
    igst     = sum(i["igst_amount"] for i in items)
    total    = sum(i["line_total"]  for i in items)
    return {
        "subtotal": round(subtotal, 2),
        "cgst":     round(cgst, 2),
        "sgst":     round(sgst, 2),
        "igst":     round(igst, 2),
        "total":    round(total, 2),
    }

def generate_pdf(invoice: dict, items: list[dict], settings: dict) -> bytes:
    """
    Generate a professional GST invoice PDF and return raw bytes.
    Uses ReportLab. Falls back to a plain-text PDF if ReportLab unavailable.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            rightMargin=15*mm, leftMargin=15*mm,
            topMargin=15*mm, bottomMargin=15*mm
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "InvTitle", parent=styles["Heading1"],
            fontSize=20, textColor=colors.HexColor("#1a56db"),
            spaceAfter=2
        )
        sub_style = ParagraphStyle(
            "Sub", parent=styles["Normal"],
            fontSize=9, textColor=colors.HexColor("#6b7280")
        )
        bold_style = ParagraphStyle(
            "Bold", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica-Bold"
        )
        right_style = ParagraphStyle(
            "Right", parent=styles["Normal"],
            fontSize=10, alignment=TA_RIGHT
        )
        small = ParagraphStyle(
            "Small", parent=styles["Normal"], fontSize=8
        )

        story = []

        header_data = [[
            Paragraph(f"<b>{settings.get('business_name','My Business')}</b>", title_style),
            Paragraph(
                f"<b>TAX INVOICE</b><br/>"
                f"<font color='#1a56db'>{invoice['invoice_number']}</font>",
                ParagraphStyle("RH", parent=styles["Normal"], fontSize=14,
                               fontName="Helvetica-Bold", alignment=TA_RIGHT)
            )
        ]]
        header_tbl = Table(header_data, colWidths=["60%", "40%"])
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(header_tbl)

        story.append(Paragraph(
            f"GSTIN: {settings.get('business_gstin','')} &nbsp;|&nbsp; "
            f"State: {settings.get('business_state','')}",
            sub_style
        ))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#1a56db"), spaceAfter=6))

        date_str = invoice.get("invoice_date", datetime.now().strftime("%Y-%m-%d"))
        supply_type = "Inter-State (IGST)" if invoice.get("is_interstate") else "Intra-State (CGST+SGST)"

        details_data = [
            [
                Paragraph("<b>Bill To:</b>", bold_style),
                Paragraph("<b>Invoice Details:</b>", bold_style),
            ],
            [
                Paragraph(invoice.get("customer_name", ""), styles["Normal"]),
                Paragraph(f"Invoice No: <b>{invoice['invoice_number']}</b>", styles["Normal"]),
            ],
            [
                Paragraph(invoice.get("customer_gst") or "—", small),
                Paragraph(f"Date: <b>{date_str}</b>", styles["Normal"]),
            ],
            [
                Paragraph(invoice.get("customer_address") or "", small),
                Paragraph(f"Supply Type: {supply_type}", small),
            ],
            [
                Paragraph(f"State: {invoice.get('customer_state') or ''}", small),
                Paragraph("", small),
            ],
        ]
        details_tbl = Table(details_data, colWidths=["55%", "45%"])
        details_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(details_tbl)
        story.append(Spacer(1, 8*mm))

        is_interstate = invoice.get("is_interstate", False)
        if is_interstate:
            col_headers = ["#", "Product", "SKU", "Qty", "Rate (₹)", "GST%", "IGST (₹)", "Total (₹)"]
            col_widths  = [8*mm, 55*mm, 25*mm, 12*mm, 20*mm, 12*mm, 20*mm, 22*mm]
        else:
            col_headers = ["#", "Product", "SKU", "Qty", "Rate (₹)", "GST%", "CGST (₹)", "SGST (₹)", "Total (₹)"]
            col_widths  = [8*mm, 48*mm, 22*mm, 10*mm, 18*mm, 10*mm, 18*mm, 18*mm, 22*mm]

        rows = [col_headers]
        for idx, item in enumerate(items, 1):
            if is_interstate:
                rows.append([
                    str(idx),
                    item["product_name"],
                    item.get("sku") or "—",
                    str(item["quantity"]),
                    f"₹{item['price']:,.2f}",
                    f"{item['gst_percent']}%",
                    f"₹{item['igst_amount']:,.2f}",
                    f"₹{item['line_total']:,.2f}",
                ])
            else:
                rows.append([
                    str(idx),
                    item["product_name"],
                    item.get("sku") or "—",
                    str(item["quantity"]),
                    f"₹{item['price']:,.2f}",
                    f"{item['gst_percent']}%",
                    f"₹{item['cgst_amount']:,.2f}",
                    f"₹{item['sgst_amount']:,.2f}",
                    f"₹{item['line_total']:,.2f}",
                ])

        items_tbl = Table(rows, colWidths=col_widths)
        items_tbl.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#1a56db")),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0), 8),
            ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
            # Data rows
            ("FONTSIZE",     (0, 1), (-1, -1), 8),
            ("ALIGN",        (3, 1), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f0f4ff")]),
            # Grid
            ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(items_tbl)
        story.append(Spacer(1, 5*mm))

        totals_rows = [
            ["", "Sub-total:", f"₹{invoice['subtotal']:,.2f}"],
        ]
        if is_interstate:
            totals_rows.append(["", f"IGST:", f"₹{invoice['igst']:,.2f}"])
        else:
            totals_rows.append(["", f"CGST:", f"₹{invoice['cgst']:,.2f}"])
            totals_rows.append(["", f"SGST:", f"₹{invoice['sgst']:,.2f}"])
        totals_rows.append(["", "GRAND TOTAL:", f"₹{invoice['total']:,.2f}"])

        totals_tbl = Table(totals_rows, colWidths=["55%", "25%", "20%"])
        totals_tbl.setStyle(TableStyle([
            ("ALIGN",      (1, 0), (-1, -1), "RIGHT"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("FONTNAME",   (1, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (1, -1), (-1, -1), 11),
            ("TEXTCOLOR",  (1, -1), (-1, -1), colors.HexColor("#1a56db")),
            ("LINEABOVE",  (1, -1), (-1, -1), 1, colors.HexColor("#1a56db")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(totals_tbl)

        story.append(Spacer(1, 10*mm))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#d1d5db"), spaceAfter=4))
        story.append(Paragraph(
            "This is a computer-generated invoice and does not require a physical signature.",
            ParagraphStyle("Footer", parent=styles["Normal"],
                           fontSize=7, textColor=colors.gray, alignment=TA_CENTER)
        ))

        doc.build(story)
        return buf.getvalue()

    except ImportError:
        lines = [
            f"TAX INVOICE",
            f"Business: {settings.get('business_name','')}",
            f"GSTIN: {settings.get('business_gstin','')}",
            f"",
            f"Invoice No: {invoice['invoice_number']}",
            f"Date: {invoice.get('invoice_date','')}",
            f"Customer: {invoice['customer_name']}",
            f"",
            f"Items:",
        ]
        for i, item in enumerate(items, 1):
            lines.append(f"  {i}. {item['product_name']} x{item['quantity']} @ ₹{item['price']} = ₹{item['line_total']}")
        lines += [
            f"",
            f"Subtotal: ₹{invoice['subtotal']}",
            f"Total:    ₹{invoice['total']}",
        ]
        text = "\n".join(lines)
        return text.encode("utf-8")


def export_gst_report(invoices: list[dict], invoice_items_map: dict) -> bytes:
    """
    Build a GST report Excel file.
    invoice_items_map = {invoice_id: [items]}
    """
    buf = io.BytesIO()

    # Sheet 1 – Invoice Summary
    summary_rows = []
    for inv in invoices:
        summary_rows.append({
            "Invoice No":     inv["invoice_number"],
            "Date":           inv["invoice_date"],
            "Customer":       inv["customer_name"],
            "Customer GSTIN": inv.get("customer_gst") or "",
            "Customer State": inv.get("customer_state") or "",
            "Supply Type":    "Interstate" if inv.get("is_interstate") else "Intrastate",
            "Subtotal (₹)":   inv["subtotal"],
            "CGST (₹)":       inv["cgst"],
            "SGST (₹)":       inv["sgst"],
            "IGST (₹)":       inv["igst"],
            "Grand Total (₹)":inv["total"],
        })

    df_summary = pd.DataFrame(summary_rows)

    item_rows = []
    for inv in invoices:
        items = invoice_items_map.get(inv["id"], [])
        for it in items:
            item_rows.append({
                "Invoice No":    inv["invoice_number"],
                "Date":          inv["invoice_date"],
                "Customer":      inv["customer_name"],
                "Product":       it["product_name"],
                "SKU":           it.get("sku") or "",
                "Qty":           it["quantity"],
                "Rate (₹)":      it["price"],
                "GST%":          it["gst_percent"],
                "CGST (₹)":      it["cgst_amount"],
                "SGST (₹)":      it["sgst_amount"],
                "IGST (₹)":      it["igst_amount"],
                "Line Total (₹)":it["line_total"],
            })
    df_items = pd.DataFrame(item_rows)

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="Invoice Summary", index=False)
        df_items.to_excel(writer,   sheet_name="Itemised GST",    index=False)

        # Auto-fit columns
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max((len(str(cell.value or "")) for cell in col), default=0)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    return buf.getvalue()


def export_stock_report(products: list[dict]) -> bytes:
    """Export current stock levels to Excel."""
    buf = io.BytesIO()
    rows = []
    for p in products:
        status = "Low Stock" if p["quantity"] <= 5 else ("Out of Stock" if p["quantity"] <= 0 else "In Stock")
        rows.append({
            "Product Name": p["name"],
            "SKU":          p.get("sku") or "",
            "Quantity":     p["quantity"],
            "Price (₹)":   p["price"],
            "GST%":         p["gst_percent"],
            "Status":       status,
        })
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Stock Report", index=False)
        ws = writer.sheets["Stock Report"]
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=0)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 30)
    return buf.getvalue()


def create_sample_customers_excel() -> bytes:
    """Return bytes of a sample customers Excel file."""
    df = pd.DataFrame([
        {"Customer Name": "Ramesh Traders",     "Phone": "9876543210", "GST Number": "27AABCU9603R1ZX", "Address": "123 MG Road, Mumbai", "State": "Maharashtra"},
        {"Customer Name": "Sunita Enterprises", "Phone": "9812345678", "GST Number": "09AABCU9603R1ZY", "Address": "45 Connaught Place, Delhi", "State": "Delhi"},
        {"Customer Name": "Kapoor & Sons",      "Phone": "9734567890", "GST Number": "06AABCU9603R1ZZ", "Address": "78 Sector 18, Gurugram", "State": "Haryana"},
    ])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Customers")
    return buf.getvalue()


def create_sample_products_excel() -> bytes:
    """Return bytes of a sample products Excel file."""
    df = pd.DataFrame([
        {"Product Name": "HP Laptop 15s",  "SKU": "HP-LAP-15S", "Quantity": 25, "Price": 45000, "GST%": 18},
        {"Product Name": "Dell Monitor 24","SKU": "DEL-MON-24", "Quantity": 40, "Price": 15000, "GST%": 18},
        {"Product Name": "USB-C Hub 7Port","SKU": "USB-C-7PT",  "Quantity": 100,"Price": 1200,  "GST%": 12},
        {"Product Name": "Wireless Mouse", "SKU": "WRL-MSE-01", "Quantity": 80, "Price": 800,   "GST%": 12},
        {"Product Name": "Office Chair Pro","SKU":"OFC-CHR-PRO","Quantity": 15, "Price": 8500,  "GST%": 18},
        {"Product Name": "A4 Paper Ream",  "SKU": "A4-PPR-500", "Quantity": 200,"Price": 350,   "GST%": 5 },
    ])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Products")
    return buf.getvalue()
