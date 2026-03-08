"""Table display of all transactions with edit/delete options."""

from datetime import datetime

import streamlit as st

ALL_MONTHS_KEY = "All months"


def _transaction_in_month(tx: dict, year: int, month: int) -> bool:
    """Check if transaction date falls in the given year/month."""
    date_str = tx.get("date", "") or ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.year == year and dt.month == month
    except ValueError:
        return False


def _get_month_options(transactions: list[dict]) -> list[str]:
    """Extract unique months (YYYY-MM) from transactions, sorted descending."""
    months = set()
    for tx in transactions:
        date_str = tx.get("date", "") or ""
        if len(date_str) >= 7:
            months.add(date_str[:7])
    return [ALL_MONTHS_KEY] + sorted(months, reverse=True)


def _format_month_option(value: str) -> str:
    """Format 'YYYY-MM' as 'Feb 2024' for display."""
    if value == ALL_MONTHS_KEY:
        return "All months"
    try:
        return datetime.strptime(value + "-01", "%Y-%m-%d").strftime("%b %Y")
    except ValueError:
        return value


def _filter_by_month(transactions: list[dict], selection: str) -> list[dict]:
    """Filter transactions by selected month."""
    if selection == ALL_MONTHS_KEY:
        return transactions
    try:
        year, month = map(int, selection.split("-"))
        return [tx for tx in transactions if _transaction_in_month(tx, year, month)]
    except (ValueError, AttributeError):
        return transactions


def render_transactions_table(transactions: list[dict], on_delete):
    """
    Render the transactions table with month filter and delete buttons.
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

    # Sort by date descending (latest first)
    def _sort_key(tx):
        d = tx.get("date", "") or ""
        return d if d else ""

    filtered = sorted(filtered, key=_sort_key, reverse=True)

    if not filtered:
        st.info(f"No transactions in the selected period.")
        return

    total = sum(float(tx.get("amount", 0) or 0) for tx in filtered)
    st.caption(f"{len(filtered)} transaction{'s' if len(filtered) != 1 else ''} · Total: ¥{total:,.0f}")

    # Header row
    h1, h2, h3, h4, h5, h6 = st.columns([1.5, 3, 1.5, 1, 0.8, 0.8])
    with h1:
        st.caption("**Date**")
    with h2:
        st.caption("**Item**")
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
                st.write(f"**{tx.get('item', '')}**")
            with col3:
                st.write(tx.get("category", ""))
            with col4:
                amount = tx.get("amount", "")
                st.write(f"¥{float(amount):,.0f}" if amount else "—")
            with col5:
                if tx.get("drive_file_id"):
                    st.markdown(
                        f"[📷](https://drive.google.com/file/d/{tx['drive_file_id']}/view)"
                    )
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
