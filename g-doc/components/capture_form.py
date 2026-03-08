"""Form component for capturing receipt details."""

from datetime import date

import streamlit as st

from config import CATEGORIES
from utils.id_utils import generate_receipt_id
from utils.image_utils import validate_image_file
from services.pdf_service import is_supported_receipt_file

PENDING_RECEIPT_KEY = "capture_form_pending_receipt"
SHOW_CAMERA_KEY = "capture_form_show_camera"
RETAINED_FORM_KEY = "capture_form_retained"
RETAINED_ERROR_KEY = "capture_form_retained_error"
SUCCESS_MESSAGE_KEY = "capture_form_show_success"


def _get_pending_receipt():
    """Get (bytes, filename) or (None, '') from session state."""
    data = st.session_state.get(PENDING_RECEIPT_KEY)
    if data is None:
        return None, ""
    return data.get("bytes"), data.get("filename", "")


def _set_pending_receipt(image_bytes: bytes, filename: str):
    """Store receipt image in session state."""
    st.session_state[PENDING_RECEIPT_KEY] = {"bytes": image_bytes, "filename": filename}


def _clear_pending_receipt():
    """Clear pending receipt from session state."""
    if PENDING_RECEIPT_KEY in st.session_state:
        del st.session_state[PENDING_RECEIPT_KEY]


def _retain_form_values(date_value, amount, item, category):
    """Store form values so they persist when validation fails."""
    st.session_state[RETAINED_FORM_KEY] = {
        "date": date_value,
        "amount": amount,
        "item": item or "",
        "category": category,
    }


def _get_retained_form_values():
    """Get retained form values, or None if none."""
    return st.session_state.get(RETAINED_FORM_KEY)


def _clear_retained_form():
    """Clear retained form values after successful submit."""
    if RETAINED_FORM_KEY in st.session_state:
        del st.session_state[RETAINED_FORM_KEY]
    if RETAINED_ERROR_KEY in st.session_state:
        del st.session_state[RETAINED_ERROR_KEY]


def _retain_error(msg: str):
    """Store error message to show after rerun."""
    st.session_state[RETAINED_ERROR_KEY] = msg


def _show_retained_error():
    """Display and clear any retained error."""
    err = st.session_state.pop(RETAINED_ERROR_KEY, None)
    if err:
        st.error(err)


def render_capture_form(on_submit):
    """
    Render the receipt capture form.
    on_submit: callback(transaction_dict, image_bytes, filename)
    """
    st.subheader("Add Receipt")

    # Image capture - outside form (camera/file_uploader don't work reliably inside forms)
    # Tabs for Take Photo (mobile-friendly) vs Upload
    img_tab1, img_tab2 = st.tabs(["📷 Take Photo", "📁 Upload File"])

    with img_tab1:
        show_camera = st.session_state.get(SHOW_CAMERA_KEY, False)

        if show_camera:
            camera_img = st.camera_input(
                "Capture receipt",
                key="receipt_camera",
                help="Take a photo of your receipt (required). Works best on mobile with HTTPS.",
            )
            if st.button("Close camera", key="close_camera"):
                st.session_state[SHOW_CAMERA_KEY] = False
                st.rerun()
            if camera_img:
                image_bytes = camera_img.getvalue()
                filename = getattr(camera_img, "name", None) or "receipt.jpg"
                if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    filename = "receipt.jpg"
                _set_pending_receipt(image_bytes, filename)
                st.session_state[SHOW_CAMERA_KEY] = False
                st.rerun()
        else:
            if st.button("📷 Capture receipt", key="open_camera", type="primary"):
                st.session_state[SHOW_CAMERA_KEY] = True
                st.rerun()

    with img_tab2:
        image_file = st.file_uploader(
            "Receipt Image",
            type=["jpg", "jpeg", "png", "gif", "webp", "pdf"],
            key="receipt_upload",
            help="Upload receipt photo or PDF (required)",
        )
        if image_file:
            _set_pending_receipt(image_file.read(), image_file.name)

    pending_bytes, pending_filename = _get_pending_receipt()
    if pending_bytes:
        st.caption("✅ Receipt image ready (required)")
        if st.button("Clear image", key="clear_receipt"):
            _clear_pending_receipt()
            st.rerun()
    else:
        st.caption("⚠️ Add a receipt image (required to save)")

    retained = _get_retained_form_values()
    _show_retained_error()

    with st.form("capture_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            default_date = retained["date"] if retained and retained.get("date") else date.today()
            if hasattr(default_date, "strftime"):
                pass  # already a date
            elif isinstance(default_date, str):
                try:
                    default_date = date.fromisoformat(default_date)
                except ValueError:
                    default_date = date.today()
            else:
                default_date = date.today()
            date_value = st.date_input(
                "Date",
                value=default_date,
                format="YYYY-MM-DD",
                help="Pick from calendar or type the date (YYYY-MM-DD)",
            )
        with col2:
            default_amount = retained.get("amount", 0.0) if retained else 0.0
            try:
                default_amount = float(default_amount)
            except (TypeError, ValueError):
                default_amount = 0.0
            amount = st.number_input(
                "Amount (¥)",
                value=default_amount,
                min_value=0.0,
                step=1.0,
                format="%.0f",
                placeholder="0",
            )
        with col3:
            default_item = retained.get("item", "") if retained else ""
            item = st.text_input("Item", value=default_item, placeholder="e.g. Groceries at Store")
        with col4:
            first_category = CATEGORIES[0] if CATEGORIES else "Uncategorized"
            default_category = retained.get("category", first_category) if retained else first_category
            cat_index = CATEGORIES.index(default_category) if default_category in CATEGORIES else 0
            category = st.selectbox("Category", options=CATEGORIES, index=cat_index)

        submitted = st.form_submit_button("Save Receipt")

        if submitted:
            with st.spinner("Saving…"):
                # Validate date
                if date_value is None:
                    _retain_form_values(date_value, amount, item, category)
                    st.error("Please select a date.")
                    st.rerun()
                    return
                formatted_date = date_value.strftime("%Y-%m-%d")

                # Validate item
                if not item or not item.strip():
                    _retain_form_values(date_value, amount, item, category)
                    st.error("Please enter an item description.")
                    st.rerun()
                    return

                # Validate amount
                if amount is None or amount < 0:
                    _retain_form_values(date_value, amount, item, category)
                    st.error("Please enter a valid amount.")
                    st.rerun()
                    return

                # Validate image (required)
                image_bytes, filename = _get_pending_receipt()
                if not image_bytes or not filename:
                    _retain_form_values(date_value, amount, item, category)
                    _retain_error("Need a photo mate 📷 — add a receipt image to save.")
                    st.error("Add a receipt image first (📷 Take Photo or 📁 Upload File above), then click Save again.")
                    st.rerun()
                    return
                if not is_supported_receipt_file(filename):
                    _retain_form_values(date_value, amount, item, category)
                    st.error("Unsupported file type. Use JPG, PNG, GIF, WebP, or PDF.")
                    st.rerun()
                    return
                if not filename.lower().endswith(".pdf"):
                    is_valid, err = validate_image_file(image_bytes, filename)
                    if not is_valid:
                        _retain_form_values(date_value, amount, item, category)
                        st.error(err)
                        st.rerun()
                        return

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
                    _clear_pending_receipt()
                    _clear_retained_form()
                    st.session_state[SUCCESS_MESSAGE_KEY] = True
                    st.rerun()
                except Exception as e:
                    _retain_form_values(date_value, amount, item, category)
                    err_msg = str(e)
                    if "404" in err_msg and "drive" in err_msg.lower():
                        _retain_error(
                            "Drive folder not found. Check your ..._DRIVE_FOLDER_ID in .env: use a real folder ID from the Drive URL and share that folder with your service account (Editor)."
                        )
                    elif "403" in err_msg and "storageQuotaExceeded" in err_msg:
                        _retain_error(
                            "Drive upload failed: service account has no storage. Set your ..._EMAIL in .env (e.g. KP_EMAIL=you@gmail.com) so receipts go to the app’s Drive and are shared with you. Or use a Shared Drive (Workspace) and ..._DRIVE_FOLDER_ID."
                        )
                    else:
                        _retain_error(f"Failed to save: {e}")
                    st.rerun()
