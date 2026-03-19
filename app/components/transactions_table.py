"""
Transactions table with year/month filter and per-row delete.

Renders a filter bar (Year, Month), summary caption, then a table of
transactions with columns: Date, Description, Category, Amount, receipt link, delete.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Callable

import streamlit as st

ALL_MONTHS_KEY = "All months"
ALL_YEARS_KEY = "All years"

# Column width ratios for table layout (Date, Description, Category, Amount, receipt, delete)
_TABLE_COL_RATIOS = [1.5, 3, 1.5, 1, 0.8, 0.8]


def _parse_date_year_month(date_str: str) -> tuple[int, int] | None:
    """Return (year, month) from 'YYYY-MM-DD' or None if invalid."""
    if not date_str or len(date_str) < 7:
        return None
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.year, dt.month
    except ValueError:
        return None


def _transaction_in_month(tx: dict, year: int, month: int) -> bool:
    parsed = _parse_date_year_month(tx.get("date", "") or "")
    if not parsed:
        return False
    y, m = parsed
    return y == year and m == month


def _get_year_options(transactions: list[dict]) -> list[int | str]:
    years = set()
    for tx in transactions:
        parsed = _parse_date_year_month(tx.get("date", "") or "")
        if parsed:
            years.add(parsed[0])
    return [ALL_YEARS_KEY] + sorted(years, reverse=True)


def _filter_by_year(transactions: list[dict], year_choice: int | str) -> list[dict]:
    if year_choice == ALL_YEARS_KEY:
        return transactions
    year_str = str(year_choice)
    return [tx for tx in transactions if (tx.get("date") or "")[:4] == year_str]


def _get_month_options(transactions: list[dict]) -> list[str]:
    months = set()
    for tx in transactions:
        date_str = tx.get("date", "") or ""
        if len(date_str) >= 7:
            months.add(date_str[:7])
    return [ALL_MONTHS_KEY] + sorted(months, reverse=True)


def _format_month_option(value: str) -> str:
    if value == ALL_MONTHS_KEY:
        return "All months"
    try:
        return datetime.strptime(value + "-01", "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        return value


def _month_label_for_header(selection: str) -> str:
    if selection == ALL_MONTHS_KEY:
        return "All months"
    try:
        return datetime.strptime(selection + "-01", "%Y-%m-%d").strftime("%B %Y")
    except ValueError:
        return selection


def _filter_by_month(transactions: list[dict], selection: str) -> list[dict]:
    if selection == ALL_MONTHS_KEY:
        return transactions
    try:
        year, month = map(int, selection.split("-"))
        return [tx for tx in transactions if _transaction_in_month(tx, year, month)]
    except (ValueError, AttributeError):
        return transactions


def _render_table_header() -> None:
    """Render the table column headers."""
    headers = ["**Date**", "**Description**", "**Category**", "**Amount**", "", ""]
    cols = st.columns(_TABLE_COL_RATIOS)
    for col, caption in zip(cols, headers):
        with col:
            st.caption(caption)


def _render_transaction_row(
    tx: dict,
    currency: str,
    on_delete: Callable[[str], None],
) -> None:
    """Render one transaction row (date, description, category, amount, receipt link, delete)."""
    with st.container():
        col1, col2, col3, col4, col5, col6 = st.columns(_TABLE_COL_RATIOS)
        with col1:
            st.write(tx.get("date", ""))
        with col2:
            st.write(f"**{(tx.get('description') or '').strip() or '—'}**")
        with col3:
            st.write(tx.get("category", ""))
        with col4:
            amount = tx.get("amount", "")
            st.write(f"{currency}{float(amount):,.2f}" if amount else "—")
        with col5:
            url = tx.get("receipt_url")
            if url:
                st.markdown(f"[📷]({url})")
        with col6:
            with st.popover("🗑", help="Delete"):
                st.caption("Delete this transaction?")
                if st.button("Confirm delete", key=f"confirm_del_{tx.get('id', '')}", type="primary"):
                    try:
                        on_delete(tx["id"])
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
        st.divider()


def render_transactions_table(
    transactions: list[dict],
    on_delete: Callable[[str], None],
    currency: str = "$",
) -> None:
    """
    Render the Transactions section: year/month filters and a table with delete.

    Args:
        transactions: Full list of transaction dicts (filtered by this component).
        on_delete: Callback(transaction_id) called when user confirms delete.
        currency: Symbol for amounts (e.g. "$", "¥").
    """
    if not transactions:
        st.info("No receipts recorded yet. Add one above!")
        return

    # Initialize filters to current period on first load.
    today = date.today()
    current_year = today.year
    current_month_key = today.strftime("%Y-%m")

    year_options = _get_year_options(transactions)
    if "transactions_year_filter" not in st.session_state:
        st.session_state["transactions_year_filter"] = (
            current_year if current_year in year_options else ALL_YEARS_KEY
        )

    by_year_for_default = _filter_by_year(transactions, st.session_state["transactions_year_filter"])
    month_options_for_default = _get_month_options(by_year_for_default)
    if "transactions_month_filter" not in st.session_state:
        st.session_state["transactions_month_filter"] = (
            current_month_key if current_month_key in month_options_for_default else ALL_MONTHS_KEY
        )

    filtered = _filter_by_year(transactions, st.session_state.get("transactions_year_filter", ALL_YEARS_KEY))
    filtered = _filter_by_month(
        filtered,
        st.session_state.get("transactions_month_filter", ALL_MONTHS_KEY),
    )
    filtered = sorted(filtered, key=lambda tx: tx.get("date") or "", reverse=True)
    n = len(filtered)
    total = sum(float(tx.get("amount", 0) or 0) for tx in filtered) if filtered else 0
    summary = f"{n} transaction{'s' if n != 1 else ''} · Total: {currency}{total:,.2f}"
    selected_month_for_header = st.session_state.get("transactions_month_filter", ALL_MONTHS_KEY)
    month_header = _month_label_for_header(selected_month_for_header)

    with st.expander(f"**Transactions ({month_header})** — {summary}", expanded=False):
        col_year, col_month = st.columns(2)
        with col_year:
            year_options = _get_year_options(transactions)
            selected_year = st.selectbox(
                "Year",
                options=year_options,
                format_func=lambda y: str(y),
                key="transactions_year_filter",
                help="Filter transactions by year",
            )
        by_year = _filter_by_year(transactions, selected_year)
        month_options = _get_month_options(by_year)
        with col_month:
            selected_month = st.selectbox(
                "Month",
                options=month_options,
                format_func=_format_month_option,
                key="transactions_month_filter",
                help="Filter transactions by month",
            )

        filtered = _filter_by_month(by_year, selected_month)
        filtered = sorted(filtered, key=lambda tx: tx.get("date") or "", reverse=True)

        if not filtered:
            st.info("No transactions in the selected period.")
        else:
            total = sum(float(tx.get("amount", 0) or 0) for tx in filtered)
            n = len(filtered)
            st.caption(f"{n} transaction{'s' if n != 1 else ''} · Total: {currency}{total:,.2f}")
            _render_table_header()
            for tx in filtered:
                _render_transaction_row(tx, currency, on_delete)
