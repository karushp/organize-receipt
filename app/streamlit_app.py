"""
Receipt Capture & Expense Tracker – Streamlit app (single dashboard, same layout as g-doc).
Run from project root: streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date
from io import BytesIO

import streamlit as st
import httpx

from app.supabase_client import get_client
from app import upload_receipt, transactions
from app.config import USERS, load_categories, DEFAULT_CURRENCY
from app.auth import auth_enabled, check_login, is_super_user, get_data_user_for_login
from app.components.capture_form import render_capture_form, SUCCESS_MESSAGE_KEY
from app.components.transactions_table import render_transactions_table
from app.components.print_section import render_print_section
from app.sheets_sync import run_sync as run_sheets_sync
from utils import export_statement, export_receipt

CATEGORIES = load_categories()

st.set_page_config(
    page_title="Receipt Tracker",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "current_data_user" not in st.session_state:
    st.session_state.current_data_user = None


def _ensure_supabase():
    try:
        get_client()
        return True
    except Exception as e:
        st.error(f"Supabase not configured: {e}")
        return False


def _handle_submit(transaction_dict, image_bytes, filename):
    """Upload image to Supabase Storage (if provided) and insert transaction."""
    user = transaction_dict["user"]
    transaction_date = date.fromisoformat(transaction_dict["date"])
    receipt_url = None
    if image_bytes and filename:
        content_type = upload_receipt.content_type_for_filename(filename)
        receipt_url = upload_receipt.upload_image(
            user, image_bytes, content_type, transaction_date=transaction_date
        )
    upload_receipt.insert_transaction(
        date_val=date.fromisoformat(transaction_dict["date"]),
        user=user,
        category=transaction_dict["category"],
        amount=transaction_dict["amount"],
        description=transaction_dict.get("description", ""),
        receipt_url=receipt_url,
    )


def _handle_delete(transaction_id, *, allowed_user=None):
    """Delete a transaction. If allowed_user is set (regular user), only allow if transaction belongs to that user."""
    if allowed_user is not None:
        tx = transactions.get_transaction_by_id(transaction_id)
        if not tx or tx.get("user") != allowed_user:
            raise PermissionError("You can only delete your own transactions.")
    transactions.delete_transaction(transaction_id)


def _render_login():
    st.title("Receipt Tracker")
    st.caption("Sign in to continue.")
    with st.form("login"):
        username = st.text_input("Username", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        if st.form_submit_button("Log in"):
            if username and password and check_login(username, password):
                st.session_state.authenticated = True
                st.session_state.auth_user = username
                st.rerun()
            else:
                st.error("Invalid username or password.")


def _render_user_select():
    """Select which user account (data) to use – like g-doc."""
    st.title("Receipt Tracker")
    st.caption("Select your account to continue.")
    st.divider()

    chosen = st.selectbox("User", options=USERS, key="auth_user_select", label_visibility="collapsed")
    if st.button("Continue", type="primary", width="stretch"):
        st.session_state.current_data_user = chosen
        st.rerun()


def main():
    if auth_enabled() and not st.session_state.authenticated:
        _render_login()
        return

    if not USERS:
        st.error("No users configured. Set USERS in .env (e.g. USERS=user-1,user-2).")
        return

    auth_user = st.session_state.auth_user  # None when auth is disabled
    if st.session_state.current_data_user is None:
        if not auth_enabled() or is_super_user(auth_user or ""):
            _render_user_select()
            return
        # Regular user: tied to one data user
        data_user = get_data_user_for_login(auth_user or "")
        if not data_user:
            st.error(
                "No data user assigned for this login. In .env set USER_DATA_MAP=authuser:datauser "
                "(e.g. alice:user-1,bob:user-2) so each auth user is mapped to a data user."
            )
            return
        st.session_state.current_data_user = data_user
        st.rerun()

    selected_user = st.session_state.current_data_user
    if not _ensure_supabase():
        return

    st.title(f'Receipt Tracker: **{selected_user}**')
    st.caption("Record expenses and store receipt images in Supabase. Sync to Google Sheets when needed.")

    if "load_full_history" not in st.session_state:
        st.session_state.load_full_history = False

    def _sync_google_sheets():
        with st.spinner("Syncing..."):
            return run_sheets_sync()

    with st.sidebar:
        st.caption(f"Adding as **{selected_user}**")
        can_switch = not auth_enabled() or is_super_user(st.session_state.auth_user or "")
        if can_switch:
            if st.button("Switch user", key="switch_user"):
                st.session_state.current_data_user = None
                st.rerun()
        st.divider()
        if auth_enabled():
            st.divider()
            st.caption(f"Logged in as **{st.session_state.auth_user}**")
            if st.button("Log out"):
                st.session_state.authenticated = False
                st.session_state.auth_user = None
                st.session_state.current_data_user = None
                st.rerun()

    if st.session_state.pop(SUCCESS_MESSAGE_KEY, False):
        st.success("Receipt saved successfully!")

    render_capture_form(
        categories=CATEGORIES,
        on_submit=_handle_submit,
        current_user=selected_user,
        on_sync_google_sheets=_sync_google_sheets,
    )
    st.divider()

    # Regular users only see their own transactions; super users see all
    auth_user = st.session_state.auth_user or ""
    only_my_data = auth_enabled() and not is_super_user(auth_user)
    current_month = date.today().replace(day=1)

    with st.container():
        left, right = st.columns([3, 1])
        with left:
            if st.session_state.load_full_history:
                st.caption("Showing full transaction history.")
            else:
                st.caption(f"Showing current month by default ({current_month.strftime('%B %Y')}) for faster initial load.")
        with right:
            if st.session_state.load_full_history:
                if st.button("Use fast month view", key="use_fast_month_view", width="stretch"):
                    st.session_state.load_full_history = False
                    st.rerun()
            else:
                if st.button("Load full history", key="load_full_history_btn", width="stretch"):
                    st.session_state.load_full_history = True
                    st.rerun()

    try:
        if st.session_state.load_full_history:
            if only_my_data:
                all_tx = transactions.get_transactions_filtered(user=selected_user)
            else:
                all_tx = transactions.get_all_transactions()
        else:
            if only_my_data:
                all_tx = transactions.get_transactions_filtered(month=current_month, user=selected_user)
            else:
                all_tx = transactions.get_transactions_filtered(month=current_month)
    except httpx.ConnectError as e:
        st.error(
            "**Cannot reach Supabase.** Check that `SUPABASE_URL` in `.env` is correct "
            "(e.g. `https://your-project.supabase.co` with no trailing slash) and you have network access. "
            "Run from project root: `uv run streamlit run app/streamlit_app.py`"
        )
        st.stop()

    delete_callback = (lambda tid: _handle_delete(tid, allowed_user=selected_user)) if only_my_data else _handle_delete
    render_transactions_table(all_tx, delete_callback, currency=DEFAULT_CURRENCY)
    st.divider()

    if only_my_data:
        def _transactions_for_print(month_date, user_or_none):
            return transactions.get_transactions_filtered(month=month_date, user=selected_user)
        report_users = [selected_user]
    else:
        def _transactions_for_print(month_date, user_or_none):
            return transactions.get_transactions_filtered(month=month_date, user=user_or_none)
        report_users = USERS

    def _make_pdf(rows, include_receipts=True, include_statement=True, month_label="", user_name=""):
        # When a single user is selected, filter to that user only (defensive for report/receipts)
        if user_name and user_name != "All users":
            rows = [r for r in rows if r.get("user") == user_name]
        buf = BytesIO()
        if not include_statement and include_receipts:
            export_receipt.generate_receipts_pdf(rows, output_buffer=buf, heading_suffix=month_label)
        else:
            export_statement.generate_receipts_pdf(
                rows,
                output_buffer=buf,
                receipts_per_page=15,
                currency=DEFAULT_CURRENCY,
                include_receipts=include_receipts,
                include_statement=include_statement,
                statement_month_label=month_label,
                statement_user_name=user_name,
            )
        return buf.getvalue()

    render_print_section(
        _transactions_for_print,
        report_users,
        _make_pdf,
        currency=DEFAULT_CURRENCY,
        show_user_filter=not only_my_data,
        current_user=selected_user,
    )


if __name__ == "__main__":
    main()
