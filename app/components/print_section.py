"""
Print / Export Report: month + optional user filter (superuser only), download PDF.

Renders an expander with Year/Month (and optionally User) filters, then three
download buttons: statement only, statement + receipts, receipts only.
"""

from __future__ import annotations

from datetime import date
from typing import Callable

import streamlit as st

# Year range for the report filter
_PRINT_YEAR_MIN = 2020
_PRINT_YEAR_MAX = 2030


def _generate_pdf_variants(
    pdf_generator: Callable[..., bytes],
    rows: list[dict],
    month_label: str,
    user_name: str,
) -> tuple[bytes, bytes, bytes]:
    """
    Generate three PDF variants (statement only, statement + receipts, receipts only).
    On TypeError (e.g. older generator without keyword args), falls back to single full PDF.
    """
    try:
        statement_only = pdf_generator(
            rows,
            include_receipts=False,
            include_statement=True,
            month_label=month_label,
            user_name=user_name,
        )
        with_receipts = pdf_generator(
            rows,
            include_receipts=True,
            include_statement=True,
            month_label=month_label,
            user_name=user_name,
        )
        receipts_only = pdf_generator(
            rows,
            include_receipts=True,
            include_statement=False,
            month_label=month_label,
            user_name=user_name,
        )
        return statement_only, with_receipts, receipts_only
    except TypeError:
        fallback = pdf_generator(rows)
        return fallback, fallback, fallback


def render_print_section(
    transactions_getter: Callable[[date, str | None], list[dict]],
    users: list[str],
    pdf_generator: Callable[..., bytes],
    *,
    currency: str = "$",
    show_user_filter: bool = True,
    current_user: str | None = None,
) -> None:
    """
    Render the "Download Statement" expander with filters and PDF download buttons.

    Args:
        transactions_getter: (month_date, user_or_none) -> list of transaction dicts.
        users: List of user identifiers for the User dropdown (when show_user_filter).
        pdf_generator: (rows, ..., month_label=, user_name=) -> PDF bytes.
        currency: Symbol for amounts (e.g. "$", "¥").
        show_user_filter: If True, show User dropdown (for superuser). If False, report is for current_user only.
        current_user: Used when show_user_filter is False.
    """
    with st.expander("Download Statement", expanded=False):
        n_cols = 3 if show_user_filter else 2
        cols = st.columns(n_cols)

        with cols[0]:
            year = st.selectbox(
                "Year",
                options=list(range(_PRINT_YEAR_MIN, _PRINT_YEAR_MAX + 1)),
                index=min(date.today().year - _PRINT_YEAR_MIN, _PRINT_YEAR_MAX - _PRINT_YEAR_MIN),
                key="print_year",
            )
        with cols[1]:
            month = st.selectbox(
                "Month",
                options=list(range(1, 13)),
                format_func=lambda m: date(2000, m, 1).strftime("%b"),
                index=date.today().month - 1,
                key="print_month",
            )

        if show_user_filter:
            with cols[2]:
                user_filter = st.selectbox("User", ["All"] + list(users), key="print_user")
            user_val = None if user_filter == "All" else user_filter
        else:
            user_val = current_user

        month_date = date(year, month, 1)
        rows = transactions_getter(month_date, user_val)

        if not rows:
            st.info("No transactions for this period.")
            return

        total = sum(float(r.get("amount") or 0) for r in rows)
        st.caption(f"Total: {currency}{total:,.2f}")

        month_label = month_date.strftime("%B %Y")
        user_name = user_val or "All users"
        base_name = f"statement_{year}_{month:02d}"

        try:
            pdf_statement_only, pdf_with_receipts, pdf_receipts_only = _generate_pdf_variants(
                pdf_generator, rows, month_label, user_name
            )
        except Exception as e:
            st.error(f"PDF export failed: {e}")
            return

        download_specs = [
            ("Download statement only", pdf_statement_only, f"{base_name}.pdf", "dl_pdf_statement"),
            ("Download statement + receipts", pdf_with_receipts, f"{base_name}_receipts.pdf", "dl_pdf_receipts"),
            ("Download receipts only", pdf_receipts_only, f"{base_name}_receipts_only.pdf", "dl_pdf_receipts_only"),
        ]
        dl_cols = st.columns(3)
        for (label, data, filename, key), col in zip(download_specs, dl_cols):
            with col:
                st.download_button(label, data, file_name=filename, key=key)
