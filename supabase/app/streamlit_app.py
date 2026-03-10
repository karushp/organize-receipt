"""
Receipt Capture & Expense Tracker – Streamlit app (single dashboard, same layout as g-doc).
Run from supabase/: streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    # Load from supabase/.env first; then cwd (so "streamlit run" from repo root still finds .env)
    load_dotenv(ROOT / ".env")
    load_dotenv()
except ImportError:
    pass

import json
from datetime import date
from io import BytesIO

import streamlit as st
import httpx

from app.supabase_client import get_client
from app import upload_receipt, transactions
from app.config import USERS
from app.auth import auth_enabled, check_login, is_super_user, get_data_user_for_login
from app.components.capture_form import render_capture_form, SUCCESS_MESSAGE_KEY
from app.components.transactions_table import render_transactions_table
from app.components.print_section import render_print_section
from app.sheets_sync import run_sync as run_sheets_sync
from utils import pdf_export

CATEGORIES_PATH = ROOT / "config" / "categories.json"
with open(CATEGORIES_PATH) as f:
    CATEGORIES = json.load(f)

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
    receipt_url = None
    if image_bytes and filename:
        content_type = "image/jpeg"
        if filename.lower().endswith(".png"):
            content_type = "image/png"
        elif filename.lower().endswith(".webp"):
            content_type = "image/webp"
        elif filename.lower().endswith(".heic"):
            content_type = "image/heic"
        receipt_url = upload_receipt.upload_image(user, image_bytes, content_type)
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
    if st.button("Continue", type="primary", use_container_width=True):
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

    with st.sidebar:
        st.caption(f"Adding as **{selected_user}**")
        can_switch = not auth_enabled() or is_super_user(st.session_state.auth_user or "")
        if can_switch:
            if st.button("Switch user", key="switch_user"):
                st.session_state.current_data_user = None
                st.rerun()
        st.divider()
        if st.button("Sync to Google Sheets", key="sync_sheets", help="Push Supabase transactions to your Google Sheet"):
            with st.spinner("Syncing…"):
                ok, msg = run_sheets_sync()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
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
    )
    st.divider()

    # Regular users only see their own transactions; super users see all
    auth_user = st.session_state.auth_user or ""
    only_my_data = auth_enabled() and not is_super_user(auth_user)

    try:
        if only_my_data:
            all_tx = transactions.get_transactions_filtered(user=selected_user)
        else:
            all_tx = transactions.get_all_transactions()
    except httpx.ConnectError as e:
        st.error(
            "**Cannot reach Supabase.** Check that `SUPABASE_URL` in `supabase/.env` is correct "
            "(e.g. `https://your-project.supabase.co` with no trailing slash) and you have network access. "
            "Run the app from the supabase directory: `cd supabase && uv run streamlit run app/streamlit_app.py`"
        )
        st.stop()

    delete_callback = (lambda tid: _handle_delete(tid, allowed_user=selected_user)) if only_my_data else _handle_delete
    render_transactions_table(all_tx, delete_callback, currency="$")
    st.divider()

    if only_my_data:
        def _transactions_for_print(month_date, user_or_none):
            return transactions.get_transactions_filtered(month=month_date, user=selected_user)
        report_users = [selected_user]
    else:
        def _transactions_for_print(month_date, user_or_none):
            return transactions.get_transactions_filtered(month=month_date, user=user_or_none)
        report_users = USERS

    def _make_pdf(rows):
        buf = BytesIO()
        pdf_export.generate_receipts_pdf(rows, output_buffer=buf, receipts_per_page=4)
        return buf.getvalue()

    render_print_section(_transactions_for_print, report_users, _make_pdf, currency="$")


if __name__ == "__main__":
    main()
