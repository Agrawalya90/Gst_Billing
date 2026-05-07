
import pandas as pd
import streamlit as st

from database import get_customers, get_products, next_invoice_number, save_invoice
from utils import (
    GST_RATES,
    calculate_invoice_totals,
    calculate_line_item,
    generate_pdf,
    #whatsapp_link,
)


def render() -> None:
    st.title("🧾 Create Bill")

    settings       = st.session_state.get("settings", {})
    business_state = settings.get("business_state", "Maharashtra")

    #Customer selector
    customers = get_customers()
    if not customers:
        st.warning("No customers found — please add customers first.")
        return

    cust_name = st.selectbox("Select Customer", [c["name"] for c in customers])
    selected_cust = next((c for c in customers if c["name"] == cust_name), {})

    is_interstate = str(selected_cust.get("state", "")).strip() != str(business_state).strip()
    supply_label  = "🔀 Inter-State (IGST)" if is_interstate else "🏠 Intra-State (CGST + SGST)"
    st.info(f"Supply Type: **{supply_label}**")

    st.divider()

    #Add item form
    st.subheader("Add Item")

    products = get_products()
    if not products:
        st.warning("No products found — please add products first.")
        return

    col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
    with col1:
        pname = st.selectbox("Product", [p["name"] for p in products])
    with col2:
        qty = st.number_input("Qty", min_value=0.01, value=1.0, step=1.0)
    with col3:
        selected_prod = next((p for p in products if p["name"] == pname), {})
        price = st.number_input(
            "Price (₹)",
            min_value=0.0,
            value=float(selected_prod.get("price", 0)),
            step=1.0,
        )
    with col4:
        default_gst = int(selected_prod.get("gst_percent", 18))
        gst_idx     = GST_RATES.index(default_gst) if default_gst in GST_RATES else 3
        gst         = st.selectbox("GST %", GST_RATES, index=gst_idx)

    if st.button("➕ Add Item to Bill"):
        calc = calculate_line_item(price, qty, gst, is_interstate)
        st.session_state.bill_items.append({
            "product_name": pname,
            "quantity":     qty,
            "price":        price,
            "gst_percent":  gst,
            **calc,
        })
        st.success(f"Added **{pname}**")
        st.rerun()

    # Bill 
    if not st.session_state.bill_items:
        st.caption("No items added yet.")
        return

    st.divider()
    st.subheader("Bill Summary")

    df = pd.DataFrame(st.session_state.bill_items)
    display_cols = [c for c in
                    ["product_name", "quantity", "price", "gst_percent",
                     "base_amount", "cgst_amount", "sgst_amount", "igst_amount", "line_total"]
                    if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

    # Remove item
    remove_idx = st.number_input(
        "Remove item (row number, 0 = none)", min_value=0,
        max_value=len(st.session_state.bill_items), value=0, step=1
    )
    if st.button("🗑 Remove Item") and remove_idx > 0:
        st.session_state.bill_items.pop(remove_idx - 1)
        st.rerun()

    # Totals
    totals = calculate_invoice_totals(st.session_state.bill_items)
    c1, c2, c3 = st.columns(3)
    c1.metric("Subtotal",    f"₹{totals['subtotal']:,.2f}")
    if is_interstate:
        c2.metric("IGST",    f"₹{totals['igst']:,.2f}")
    else:
        c2.metric("CGST + SGST", f"₹{totals['cgst'] + totals['sgst']:,.2f}")
    c3.metric("Grand Total", f"₹{totals['total']:,.2f}")

    st.divider()

    col_save, col_clear = st.columns(2)

    with col_save:
        if st.button("💾 Save Invoice", type="primary", use_container_width=True):
            inv = {
                "invoice_number":   next_invoice_number(),
                "customer_name":    cust_name,
                "customer_gst":     selected_cust.get("gst_number"),
                "customer_address": selected_cust.get("address"),
                "customer_state":   selected_cust.get("state"),
                "business_state":   business_state,
                "is_interstate":    is_interstate,
                "invoice_date":     pd.Timestamp.now().strftime("%Y-%m-%d"),
                **totals,
            }
            save_invoice(inv, st.session_state.bill_items)
            st.session_state.last_invoice       = inv
            st.session_state.last_invoice_items = st.session_state.bill_items.copy()
            st.session_state.last_customer      = selected_cust
            st.session_state.bill_items         = []
            st.success(f"✅ Invoice **{inv['invoice_number']}** saved!")
            st.rerun()

    with col_clear:
        if st.button("🗑 Clear All Items", use_container_width=True):
            st.session_state.bill_items = []
            st.rerun()

    #Post-save actions
    if st.session_state.get("last_invoice"):
        inv   = st.session_state.last_invoice
        items = st.session_state.get("last_invoice_items", [])
        cust  = st.session_state.get("last_customer", {})

        st.divider()
        st.subheader(f"📄 Invoice {inv['invoice_number']} — Download / Share")

        col_pdf, col_wa = st.columns(2)
        with col_pdf:
            pdf_bytes = generate_pdf(inv, items, settings)
            st.download_button(
                label="📥 Download PDF Invoice",
                data=pdf_bytes,
                file_name=f"{inv['invoice_number']}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        """with col_wa:
            phone = cust.get("phone", "")
            if phone:
                wa_url = whatsapp_link(phone, inv)
                st.link_button(
                    "📱 Share via WhatsApp",
                    wa_url,
                    use_container_width=True,
                )
            else:
                st.caption("No phone number on file for this customer.")"""
