
import pandas as pd
import streamlit as st

from database import get_invoice_items, get_invoices
from utils import export_gst_report, generate_pdf


def render() -> None:
    st.title("📋 Invoices")

    invoices = get_invoices()
    if not invoices:
        st.info("No invoices yet. Create your first bill from the **🧾 Create Bill** page.")
        return

    df = pd.DataFrame(invoices)
    show_cols = [c for c in
                 ["invoice_number", "customer_name", "invoice_date",
                  "subtotal", "cgst", "sgst", "igst", "total", "is_interstate"]
                 if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True)
    st.caption(f"{len(invoices)} invoice(s) total")

    # ── GST report export ─────────────────────────────────────
    if st.button("📊 Export Full GST Report (Excel)"):
        with st.spinner("Building report…"):
            items_map = {inv["id"]: get_invoice_items(inv["id"]) for inv in invoices}
            report    = export_gst_report(invoices, items_map)
        st.download_button(
            label="⬇ Download GST Report",
            data=report,
            file_name="gst_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.divider()

    st.subheader("Invoice Detail")
    inv_numbers    = [inv["invoice_number"] for inv in invoices]
    selected_num   = st.selectbox("Select an invoice to view", inv_numbers)
    selected_inv   = next((i for i in invoices if i["invoice_number"] == selected_num), None)

    if not selected_inv:
        return

    items = get_invoice_items(selected_inv["id"])

    col1, col2, col3 = st.columns(3)
    col1.write(f"**Customer:** {selected_inv.get('customer_name', '—')}")
    col1.write(f"**Date:** {selected_inv.get('invoice_date', '—')}")
    col2.write(f"**Subtotal:** ₹{selected_inv.get('subtotal', 0):,.2f}")
    supply = "Inter-State (IGST)" if selected_inv.get("is_interstate") else "Intra-State (CGST+SGST)"
    col2.write(f"**Supply Type:** {supply}")
    col3.write(f"**Grand Total:** ₹{selected_inv.get('total', 0):,.2f}")

    if items:
        item_cols = [c for c in
                     ["product_name", "quantity", "price", "gst_percent",
                      "cgst_amount", "sgst_amount", "igst_amount", "line_total"]
                     if c in pd.DataFrame(items).columns]
        st.dataframe(pd.DataFrame(items)[item_cols], use_container_width=True)

    settings  = st.session_state.get("settings", {})
    pdf_bytes = generate_pdf(selected_inv, items, settings)
    st.download_button(
        label=f"📥 Download PDF — {selected_num}",
        data=pdf_bytes,
        file_name=f"{selected_num}.pdf",
        mime="application/pdf",
    )
