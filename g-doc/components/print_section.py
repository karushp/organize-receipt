"""Basic UI layout for Phase 2 report printing (placeholder)."""

import streamlit as st


def render_print_section():
    """Render the print/report section placeholder for Phase 2."""
    with st.expander("Print / Export Report", expanded=False):
        st.info("Report printing will be available in Phase 2.")
        st.caption("Filter by month, generate report, and export to PDF.")
