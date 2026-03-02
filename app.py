"""Receipt Organization App - Main Streamlit application."""

from datetime import datetime

import streamlit as st

from config import USER_CONFIG, USERS
from services.auth_service import get_credentials_or_none, get_credentials
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
from components.capture_form import render_capture_form
from components.transactions_table import render_transactions_table
from components.print_section import render_print_section

st.set_page_config(
    page_title="Receipt Organizer",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Default today's date for the form
if "today" not in st.session_state:
    st.session_state["today"] = datetime.now().strftime("%Y-%m-%d")

# Demo mode: in-memory storage when no credentials
if "demo_transactions" not in st.session_state:
    st.session_state["demo_transactions"] = [
        {"id": "rec_demo_1", "date": "2024-02-15", "item": "Coffee shop", "category": "Food", "amount": "12.50", "drive_file_id": ""},
        {"id": "rec_demo_2", "date": "2024-02-18", "item": "Uber ride", "category": "Transportation", "amount": "24.00", "drive_file_id": ""},
    ]

st.title("Receipt Organizer")
st.caption("Record expenses and store receipt images in Google Sheets & Drive.")

# User selection
selected_user = st.selectbox("User", options=USERS, key="selected_user")

if selected_user not in USER_CONFIG:
    st.error("Invalid user configuration.")
    st.stop()

config = USER_CONFIG[selected_user]
sheet_id = config["sheet_id"]
drive_folder_id = config["drive_folder_id"]

# Check if we have credentials (demo mode if not)
creds = get_credentials_or_none()
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
        drive_file_id = upload_receipt_image(
            drive_svc, drive_folder_id, prep_bytes, drive_filename, mime
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


# Capture form
render_capture_form(handle_submit)

st.divider()

# Transactions table
if demo_mode:
    transactions = st.session_state["demo_transactions"]
else:
    services = get_services()
    transactions = get_all_transactions(services["sheets"], sheet_id)

render_transactions_table(transactions, handle_delete)

st.divider()

# Print section (Phase 2 placeholder)
render_print_section()
