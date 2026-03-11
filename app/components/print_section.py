"""Print / Export Report: month + user filter, Download PDF."""

from datetime import date
from io import BytesIO

import streamlit as st


def render_print_section(transactions_getter, users, pdf_generator, currency: str = "$"):
    """
    transactions_getter(month_date, user_or_none) -> list[dict]
    pdf_generator(transactions_list) -> bytes
    """
    with st.expander("Print / Export Report", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2030, value=date.today().year, key="print_year")
        with col2:
            month = st.selectbox("Month", list(range(1, 13)), index=date.today().month - 1, key="print_month")
        with col3:
            user_filter = st.selectbox("User", ["All"] + list(users), key="print_user")

        month_date = date(year, month, 1)
        user_val = None if user_filter == "All" else user_filter
        rows = transactions_getter(month_date, user_val)

        if not rows:
            st.info("No transactions for this period.")
            return

        total = sum(float(r.get("amount") or 0) for r in rows)
        st.caption(f"Total: {currency}{total:,.2f}")

        try:
            pdf_bytes = pdf_generator(rows)
            st.download_button(
                "Download PDF (multiple receipts per page)",
                pdf_bytes,
                file_name=f"receipts_{year}_{month:02d}.pdf",
                key="dl_pdf",
            )
        except Exception as e:
            st.error(f"PDF export failed: {e}")
