"""Transactions table with month filter and delete."""

from datetime import datetime

import streamlit as st

ALL_MONTHS_KEY = "All months"


def _transaction_in_month(tx: dict, year: int, month: int) -> bool:
    date_str = tx.get("date", "") or ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.year == year and dt.month == month
    except ValueError:
        return False


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


def _filter_by_month(transactions: list[dict], selection: str) -> list[dict]:
    if selection == ALL_MONTHS_KEY:
        return transactions
    try:
        year, month = map(int, selection.split("-"))
        return [tx for tx in transactions if _transaction_in_month(tx, year, month)]
    except (ValueError, AttributeError):
        return transactions


def render_transactions_table(transactions: list[dict], on_delete, currency: str = "$"):
    """
    on_delete: callback(transaction_id)
    """
    if not transactions:
        st.info("No receipts recorded yet. Add one above!")
        return

    st.subheader("Transactions")

    month_options = _get_month_options(transactions)
    selected_month = st.selectbox(
        "Month",
        options=month_options,
        format_func=_format_month_option,
        key="transactions_month_filter",
        help="Filter transactions by month",
    )
    filtered = _filter_by_month(transactions, selected_month)
    filtered = sorted(filtered, key=lambda tx: tx.get("date") or "", reverse=True)

    if not filtered:
        st.info("No transactions in the selected period.")
        return

    total = sum(float(tx.get("amount", 0) or 0) for tx in filtered)
    st.caption(f"{len(filtered)} transaction{'s' if len(filtered) != 1 else ''} · Total: {currency}{total:,.2f}")

    h1, h2, h3, h4, h5, h6 = st.columns([1.5, 3, 1.5, 1, 0.8, 0.8])
    with h1:
        st.caption("**Date**")
    with h2:
        st.caption("**Description**")
    with h3:
        st.caption("**Category**")
    with h4:
        st.caption("**Amount**")
    with h5:
        st.caption("")
    with h6:
        st.caption("")

    for tx in filtered:
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([1.5, 3, 1.5, 1, 0.8, 0.8])
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
