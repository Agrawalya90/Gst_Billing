
import streamlit as st

from database import get_settings, save_settings
from utils import INDIAN_STATES


def render() -> None:
    st.title("⚙️ Settings")

    s = get_settings()

    # Resolve current state index safely
    current_state = s.get("business_state", "Bihar")
    state_idx     = INDIAN_STATES.index(current_state) if current_state in INDIAN_STATES else 0

    with st.form("settings_form"):
        st.subheader("Business Details")

        name    = st.text_input("Business Name *",    value=s.get("business_name", ""))
        gstin   = st.text_input("GSTIN",              value=s.get("business_gstin", ""))
        state   = st.selectbox("Business State",      INDIAN_STATES, index=state_idx)
        address = st.text_area("Business Address",    value=s.get("business_address", ""))
        phone   = st.text_input("Business Phone",     value=s.get("business_phone", ""))
        email   = st.text_input("Business Email",     value=s.get("business_email", ""))

        submitted = st.form_submit_button("💾 Save Settings", type="primary")

    if submitted:
        if not name.strip():
            st.error("Business name is required.")
        else:
            save_settings({
                "business_name":    name.strip(),
                "business_gstin":   gstin.strip(),
                "business_state":   state,
                "business_address": address.strip(),
                "business_phone":   phone.strip(),
                "business_email":   email.strip(),
            })
            # Refresh session cache
            st.session_state["settings"] = get_settings()
            st.success("✅ Settings saved!")
            st.rerun()

    if s:
        st.divider()
        st.subheader("Current Settings")
        rows = {
            "Business Name":  s.get("business_name",    "—"),
            "GSTIN":          s.get("business_gstin",   "—"),
            "State":          s.get("business_state",   "—"),
            "Address":        s.get("business_address", "—"),
            "Phone":          s.get("business_phone",   "—"),
            "Email":          s.get("business_email",   "—"),
        }
        for label, val in rows.items():
            c1, c2 = st.columns([1, 3])
            c1.write(f"**{label}**")
            c2.write(val or "—")
