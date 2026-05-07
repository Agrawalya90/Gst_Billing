
import pandas as pd
import streamlit as st

from database import add_customer_manual, get_customers, upsert_customers
from utils import INDIAN_STATES, create_sample_customers_excel


def render() -> None:
    st.title("👥 Customers")

    tab_all, tab_upload, tab_manual = st.tabs(
        ["All Customers", "📤 Upload Excel", "✏️ Add Manually"]
    )

    # All customers
    with tab_all:
        customers = get_customers()
        if customers:
            st.dataframe(pd.DataFrame(customers), use_container_width=True)
            st.caption(f"{len(customers)} customer(s) total")
        else:
            st.info("No customers yet. Add some using the other tabs.")

    #Bulk upload
    with tab_upload:
        st.download_button(
            label="⬇ Download Sample Excel",
            data=create_sample_customers_excel(),
            file_name="sample_customers.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption("Columns required: **Customer Name, Phone, GST Number, Address, State**")

        file = st.file_uploader("Upload Customers Excel", type=["xlsx"])
        if file:
            df = pd.read_excel(file)
            df.columns = [c.lower().strip() for c in df.columns]
            st.dataframe(df.head(), use_container_width=True)
            if st.button("📥 Import Customers", type="primary"):
                with st.spinner("Importing…"):
                    ins, upd = upsert_customers(df.to_dict("records"))
                st.success(f"✅ {ins} added, {upd} updated")
                st.rerun()

    #Manual add
    with tab_manual:
        with st.form("add_customer_form", clear_on_submit=True):
            name  = st.text_input("Name *")
            phone = st.text_input("Phone")
            gst   = st.text_input("GST Number")
            addr  = st.text_area("Address")
            state = st.selectbox("State", INDIAN_STATES)
            submitted = st.form_submit_button("➕ Add Customer", type="primary")

        if submitted:
            if not name.strip():
                st.error("Customer name is required.")
            else:
                add_customer_manual(name.strip(), phone, gst, addr, state)
                st.success(f"✅ '{name}' added!")
                st.rerun()
