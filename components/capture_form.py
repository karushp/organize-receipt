"""Form component for capturing receipt details."""

import streamlit as st

from config import CATEGORIES
from utils.date_utils import parse_and_format, is_valid_date
from utils.id_utils import generate_receipt_id, generate_image_filename
from utils.image_utils import validate_image_file
from services.pdf_service import is_supported_receipt_file


def render_capture_form(on_submit):
    """
    Render the receipt capture form.
    on_submit: callback(sheet_id, drive_folder_id, transaction_dict, image_bytes, filename)
    """
    with st.form("capture_form", clear_on_submit=True):
        st.subheader("Add Receipt")

        col1, col2 = st.columns(2)

        with col1:
            date_str = st.text_input(
                "Date",
                value=st.session_state.get("today", ""),
                placeholder="YYYY-MM-DD or DD/MM/YYYY",
                help="Enter the receipt date",
            )
            item = st.text_input("Item", placeholder="e.g. Groceries at Store")
            category = st.selectbox("Category", options=CATEGORIES)

        with col2:
            amount = st.number_input(
                "Amount",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                placeholder="0.00",
            )
            image_file = st.file_uploader(
                "Receipt Image",
                type=["jpg", "jpeg", "png", "gif", "webp", "pdf"],
                help="Upload receipt photo or PDF",
            )

        submitted = st.form_submit_button("Save Receipt")

        if submitted:
            # Validate date
            if not date_str or not date_str.strip():
                st.error("Please enter a date.")
                return
            formatted_date = parse_and_format(date_str)
            if not formatted_date:
                st.error("Invalid date format. Use YYYY-MM-DD or DD/MM/YYYY.")
                return

            # Validate item
            if not item or not item.strip():
                st.error("Please enter an item description.")
                return

            # Validate amount
            if amount is None or amount < 0:
                st.error("Please enter a valid amount.")
                return

            # Validate image (optional but recommended)
            image_bytes = None
            filename = ""
            if image_file:
                if not is_supported_receipt_file(image_file.name):
                    st.error("Unsupported file type. Use JPG, PNG, GIF, WebP, or PDF.")
                    return
                image_bytes = image_file.read()
                if not image_file.name.lower().endswith(".pdf"):
                    is_valid, err = validate_image_file(image_bytes, image_file.name)
                    if not is_valid:
                        st.error(err)
                        return
                filename = image_file.name

            transaction = {
                "id": generate_receipt_id(),
                "date": formatted_date,
                "item": item.strip(),
                "category": category,
                "amount": amount,
                "drive_file_id": "",
            }

            try:
                on_submit(transaction, image_bytes, filename)
                st.success("Receipt saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
