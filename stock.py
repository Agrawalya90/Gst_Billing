
import pandas as pd
import streamlit as st

from database import get_products, upsert_products
from utils import create_sample_products_excel, export_stock_report


def render() -> None:
    st.title("📦 Stock Management")

    tab_stock, tab_add, tab_upload= st.tabs(["Current Stock","Add Items","📤 Upload Products"])

    # ── Current stock ────────────────────────────────────────
    with tab_stock:
        products = get_products()
        if products:
            df = pd.DataFrame(products)

            # Low-stock warning
            low = df[df["quantity"].astype(float) <= 5]
            if not low.empty:
                st.warning(f"⚠️ {len(low)} product(s) are low or out of stock!")

            st.dataframe(df, use_container_width=True)
            st.caption(f"{len(products)} product(s) in catalogue")

            report_bytes = export_stock_report(products)
            st.download_button(
                label="⬇ Export Stock Report",
                data=report_bytes,
                file_name="stock_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No products yet. Use the **Upload Products** tab to add stock.")

    with tab_upload:
        st.download_button(
            label="⬇ Download Sample Excel",
            data=create_sample_products_excel(),
            file_name="sample_products.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption("Columns required: **Product Name, SKU, Quantity, Price, GST%**")

        file = st.file_uploader("Upload Products Excel", type=["xlsx"])
        if file:
            df = pd.read_excel(file)
            df.columns = [c.lower().strip() for c in df.columns]
            st.dataframe(df.head(), use_container_width=True)
            if st.button("📥 Import Products", type="primary"):
                with st.spinner("Importing…"):
                    ins, upd = upsert_products(df.to_dict("records"))
                st.success(f"✅ {ins} added, {upd} updated")
                st.rerun()
    