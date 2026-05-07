
import pandas as pd
import streamlit as st

from database import get_customers, get_invoices, get_products


def render() -> None:
    st.title("📊 Dashboard")

    invoices  = get_invoices()
    customers = get_customers()
    products  = get_products()

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Invoices",  len(invoices))
    col2.metric("Customers",       len(customers))
    col3.metric("Products",        len(products))

    if invoices:
        df = pd.DataFrame(invoices)
        col4.metric("Total Revenue", f"₹{df['total'].sum():,.2f}")
    else:
        col4.metric("Total Revenue", "₹0.00")

    st.divider()

    #Low-stock alerts
    if products:
        low = [p for p in products if float(p.get("quantity", 0)) <= 5]
        if low:
            with st.expander(f"⚠️ {len(low)} low / out-of-stock products", expanded=True):
                st.dataframe(
                    pd.DataFrame(low)[["name", "sku", "quantity", "price"]],
                    use_container_width=True,
                )

    #Recent invoices
    if invoices:
        st.subheader("Recent Invoices")
        df = pd.DataFrame(invoices)
        show_cols = [c for c in
                     ["invoice_number", "customer_name", "total", "invoice_date", "is_interstate"]
                     if c in df.columns]
        st.dataframe(df[show_cols].head(10), use_container_width=True)
    else:
        st.info("No invoices yet. Create your first bill from the **🧾 Create Bill** page.")
