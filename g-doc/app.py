"""Receipt Organization App - Main Streamlit application."""

from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

import streamlit as st

from googleapiclient.errors import HttpError

from config import USER_CONFIG, USERS
from services.auth_service import (
    get_credentials_or_none,
    get_credentials,
    get_oauth_authorization_url,
    exchange_oauth_code_for_credentials,
    is_oauth_configured,
)
from services.sheets_service import (
    get_sheets_service,
    ensure_sheet_ready,
    get_all_transactions,
    append_transaction,
    delete_transaction_by_id,
)
from services.drive_service import (
    get_drive_service,
    upload_receipt_image,
    delete_file,
)
from services.pdf_service import prepare_receipt_for_upload, get_mime_type
from utils.id_utils import generate_image_filename
from components.capture_form import render_capture_form, SUCCESS_MESSAGE_KEY
from components.transactions_table import render_transactions_table
from components.print_section import render_print_section

st.set_page_config(
    page_title="Receipt Organizer",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Current user (set after selecting on auth page)
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

# Default today's date for the form
if "today" not in st.session_state:
    st.session_state["today"] = datetime.now().strftime("%Y-%m-%d")

# Demo mode: in-memory storage when no credentials
if "demo_transactions" not in st.session_state:
    st.session_state["demo_transactions"] = [
        {"id": "rec_demo_1", "date": "2024-02-15", "item": "Coffee shop", "category": "Food", "amount": "12.50", "drive_file_id": ""},
        {"id": "rec_demo_2", "date": "2024-02-18", "item": "Uber ride", "category": "Transportation", "amount": "24.00", "drive_file_id": ""},
    ]

# -------- Initial auth page: select user to enter dashboard --------
if not USERS:
    st.error(
        "**Invalid configuration:** No users defined. In your `.env` file set "
        "`USERS=YourName` (comma-separated for multiple, e.g. `USERS=KP,ASB`). "
        "Then set `YourName_SHEET_ID` and `YourName_DRIVE_FOLDER_ID` for each user."
    )
    st.stop()

if st.session_state["current_user"] is None:
    st.title("Receipt Organizer")
    st.caption("Select your account to continue.")
    st.divider()

    chosen = st.selectbox("User", options=USERS, key="auth_user_select", label_visibility="collapsed")
    if chosen not in USER_CONFIG:
        st.error("Invalid user configuration. Check your `.env`.")
        st.stop()

    if st.button("Continue", type="primary", use_container_width=True):
        st.session_state["current_user"] = chosen
        st.rerun()
    st.stop()

# -------- Dashboard: user is set --------
selected_user = st.session_state["current_user"]
config = USER_CONFIG[selected_user]
sheet_id = config["sheet_id"]
drive_folder_id = config["drive_folder_id"]

st.title("Receipt Organizer")
st.caption("Record expenses and store receipt images in Google Sheets & Drive.")

with st.sidebar:
    st.caption(f"Signed in as **{selected_user}**")
    if st.button("Switch user", key="switch_user"):
        st.session_state["current_user"] = None
        st.rerun()

# Credentials: OAuth callback, then Sign in with Google, else demo mode
creds = get_credentials_or_none()
if creds is None:
    code = st.query_params.get("code")
    if isinstance(code, list):
        code = code[0] if code else None
    if code:
        if exchange_oauth_code_for_credentials(code):
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Sign-in failed. Please try again.")
    elif is_oauth_configured():
        st.info("Sign in with your **personal Google account** so receipts go to your Drive (no Shared Drive needed).")
        auth_url = get_oauth_authorization_url()
        if auth_url:
            st.link_button("Sign in with Google", url=auth_url, type="primary", use_container_width=True)
            st.caption("You’ll be redirected back here after signing in.")
        st.stop()

demo_mode = creds is None

if demo_mode:
    st.info("**Demo mode** – No Google credentials found. Data is stored in memory only and resets on refresh.")

# Initialize Google API clients (cached) - only when not in demo mode
@st.cache_resource
def get_services():
    creds = get_credentials()
    return {
        "sheets": get_sheets_service(creds),
        "drive": get_drive_service(creds),
    }


def handle_submit(transaction, image_bytes, filename):
    """Handle form submission: upload image to Drive, append row to Sheets."""
    if demo_mode:
        transaction["drive_file_id"] = ""  # No Drive in demo
        st.session_state["demo_transactions"] = st.session_state["demo_transactions"] + [transaction]
        return

    svc = get_services()
    drive_svc = svc["drive"]
    sheets_svc = svc["sheets"]

    drive_file_id = ""
    if image_bytes and filename:
        prep_bytes, mime = prepare_receipt_for_upload(image_bytes, filename)
        drive_filename = generate_image_filename(transaction["id"], filename)
        # OAuth (personal account): always use user's folder. Service account: use SA Drive only when email set or no folder.
        is_oauth = bool(creds and getattr(creds, "refresh_token", None))
        use_sa_drive = not is_oauth and (bool(config.get("email")) or not (drive_folder_id or "").strip())
        folder_id_for_upload = "" if use_sa_drive else (drive_folder_id or "")
        drive_file_id = upload_receipt_image(
            drive_svc,
            folder_id_for_upload,
            prep_bytes,
            drive_filename,
            mime,
            share_with_email=None if is_oauth else (config.get("email") or None),
            user_name=selected_user if use_sa_drive else None,
        )
    transaction["drive_file_id"] = drive_file_id

    ensure_sheet_ready(sheets_svc, sheet_id)
    append_transaction(sheets_svc, sheet_id, transaction)


def handle_delete(transaction_id):
    """Handle delete: remove from Sheets and delete image from Drive if present."""
    if demo_mode:
        st.session_state["demo_transactions"] = [
            tx for tx in st.session_state["demo_transactions"]
            if tx.get("id") != transaction_id
        ]
        return

    svc = get_services()
    sheets_svc = svc["sheets"]
    drive_svc = svc["drive"]

    transactions = get_all_transactions(sheets_svc, sheet_id)
    drive_file_id = None
    for tx in transactions:
        if tx.get("id") == transaction_id:
            drive_file_id = tx.get("drive_file_id")
            break

    delete_transaction_by_id(sheets_svc, sheet_id, transaction_id)

    if drive_file_id:
        delete_file(drive_svc, drive_file_id)


# Show success message from previous save (message is set before rerun, shown here after)
if st.session_state.pop(SUCCESS_MESSAGE_KEY, False):
    st.success("Receipt saved successfully!")

# Capture form
render_capture_form(handle_submit)

st.divider()

# Transactions table
if demo_mode:
    transactions = st.session_state["demo_transactions"]
else:
    try:
        services = get_services()
        transactions = get_all_transactions(services["sheets"], sheet_id)
    except HttpError as e:
        if e.resp.status == 403:
            creds = get_credentials()
            sa_email = getattr(creds, "service_account_email", "your service account (see client_email in credentials JSON)")
            st.error(
                "**Permission denied** – This app cannot access your Google Sheet. "
                "Share the sheet with the service account so it can read/write: "
                f"**{sa_email}** (give Editor access). Then refresh."
            )
            st.stop()
        raise

render_transactions_table(transactions, handle_delete)

st.divider()

# Print section (Phase 2 placeholder)
render_print_section()
