
import streamlit as st

st.set_page_config(
    page_title="GST Billing",
    page_icon="🧾",
    layout="wide",
)
from database import get_settings  # noqa: E402

import create_bill
import customers
import dashboard
import invoices
import reports
import settings
import stock

if "bill_items" not in st.session_state:
    st.session_state.bill_items = []

if "last_invoice" not in st.session_state:
    st.session_state.last_invoice = None

if "last_invoice_items" not in st.session_state:
    st.session_state.last_invoice_items = []

if "last_customer" not in st.session_state:
    st.session_state.last_customer = {}

if "settings" not in st.session_state:
    try:
        st.session_state["settings"] = get_settings()
    except Exception:
        st.session_state["settings"] = {}

PAGES = {
    "📊 Dashboard":   dashboard,
    "👥 Customers":   customers,
    "📦 Stock":       stock,
    "🧾 Create Bill": create_bill,
    "📋 Invoices":    invoices,
    "📈 Reports":     reports,
    "⚙️ Settings":    settings,
}

with st.sidebar:
    st.title("🧾 GST Billing")

    s = st.session_state["settings"]
    if s.get("business_name"):
        st.caption(s["business_name"])
    if s.get("business_gstin"):
        st.caption(f"GSTIN: {s['business_gstin']}")
    if s.get("business_state"):
        st.caption(f"📍 {s['business_state']}")

    st.divider()

    page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")

    # Bill item counter badge
    n = len(st.session_state.bill_items)
    if n:
        st.info(f"🛒 {n} item(s) in current bill")

try:
    PAGES[page].render()
except Exception as exc:
    st.error(f"Something went wrong: {exc}")
    st.exception(exc)
