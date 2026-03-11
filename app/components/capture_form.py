"""Capture form: Take Photo / Upload File tabs, then save to Supabase."""

from datetime import date

import streamlit as st

PENDING_RECEIPT_KEY = "capture_form_pending_receipt"
SHOW_CAMERA_KEY = "capture_form_show_camera"
RETAINED_FORM_KEY = "capture_form_retained"
RETAINED_ERROR_KEY = "capture_form_retained_error"
SUCCESS_MESSAGE_KEY = "capture_form_show_success"


def _get_pending_receipt():
    data = st.session_state.get(PENDING_RECEIPT_KEY)
    if data is None:
        return None, ""
    return data.get("bytes"), data.get("filename", "")


def _set_pending_receipt(image_bytes: bytes, filename: str):
    st.session_state[PENDING_RECEIPT_KEY] = {"bytes": image_bytes, "filename": filename}


def _clear_pending_receipt():
    if PENDING_RECEIPT_KEY in st.session_state:
        del st.session_state[PENDING_RECEIPT_KEY]


def _retain_form_values(date_value, amount, description, category):
    st.session_state[RETAINED_FORM_KEY] = {
        "date": date_value,
        "amount": amount,
        "description": description or "",
        "category": category,
    }


def _get_retained_form_values():
    return st.session_state.get(RETAINED_FORM_KEY)


def _clear_retained_form():
    if RETAINED_FORM_KEY in st.session_state:
        del st.session_state[RETAINED_FORM_KEY]
    if RETAINED_ERROR_KEY in st.session_state:
        del st.session_state[RETAINED_ERROR_KEY]


def _retain_error(msg: str):
    st.session_state[RETAINED_ERROR_KEY] = msg


def _show_retained_error():
    err = st.session_state.pop(RETAINED_ERROR_KEY, None)
    if err:
        st.error(err)


def render_capture_form(categories, on_submit, current_user: str):
    """
    current_user: the selected user (from "Adding as X"); all new entries go to this user.
    on_submit(transaction_dict, image_bytes, filename) where image_bytes/filename may be None if bypass receipt.
    """
    st.subheader("Add Receipt")

    img_tab1, img_tab2 = st.tabs(["📷 Take Photo", "📁 Upload File"])

    with img_tab1:
        show_camera = st.session_state.get(SHOW_CAMERA_KEY, False)
        if show_camera:
            camera_img = st.camera_input(
                "Capture receipt",
                key="receipt_camera",
                help="Take a photo of your receipt. Works best on mobile with HTTPS.",
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
            type=["jpg", "jpeg", "png", "webp", "heic"],
            key="receipt_upload",
            help="Upload receipt photo",
        )
        if image_file:
            _set_pending_receipt(image_file.read(), image_file.name)

    pending_bytes, pending_filename = _get_pending_receipt()
    if pending_bytes:
        st.caption("✅ Receipt image ready")
        if st.button("Clear image", key="clear_receipt"):
            _clear_pending_receipt()
            st.rerun()
    else:
        st.caption("Optional: add a receipt image, or check **Save without receipt** below.")

    retained = _get_retained_form_values()
    _show_retained_error()

    CATEGORY_PLACEHOLDER = "Select one"
    category_options = [CATEGORY_PLACEHOLDER] + (categories or ["Other"])

    with st.form("capture_form", clear_on_submit=True):
        # Date | Amount (narrow) | Description (wide) | Category (wider)
        col1, col2, col3, col4 = st.columns([1.2, 1, 2.2, 1.8])

        with col1:
            default_date = date.today()
            if retained and retained.get("date"):
                d = retained["date"]
                if hasattr(d, "strftime"):
                    default_date = d
                elif isinstance(d, str):
                    try:
                        default_date = date.fromisoformat(d)
                    except ValueError:
                        pass
            date_value = st.date_input("Date", value=default_date, format="YYYY-MM-DD")

        with col2:
            default_amount = 0.0
            if retained and retained.get("amount") is not None:
                try:
                    default_amount = float(retained["amount"])
                except (TypeError, ValueError):
                    pass
            amount = st.number_input("Amount ($)", value=default_amount, min_value=0.0, step=0.01, format="%.2f")

        with col3:
            default_desc = (retained or {}).get("description", "")
            description = st.text_input("Description", value=default_desc, placeholder="e.g. Shimamura clothes shopping")

        with col4:
            default_cat = (retained or {}).get("category", "")
            if default_cat and default_cat in categories:
                cat_index = category_options.index(default_cat)  # 1-based in options
            else:
                cat_index = 0  # "Select one"
            category = st.selectbox("Category (required)", options=category_options, index=cat_index)

        bypass_receipt = st.checkbox("Save without receipt image", key="bypass_receipt", help="Save the entry with no photo.")

        submitted = st.form_submit_button("Save Receipt")

        if submitted:
            if date_value is None:
                _retain_form_values(date_value, amount, description, category if category != CATEGORY_PLACEHOLDER else "")
                st.error("Please select a date.")
                st.rerun()
                return
            if amount is None or amount < 0:
                _retain_form_values(date_value, amount, description, category if category != CATEGORY_PLACEHOLDER else "")
                st.error("Please enter a valid amount.")
                st.rerun()
                return
            if category == CATEGORY_PLACEHOLDER or not category:
                _retain_form_values(date_value, amount, description, "")
                _retain_error("Please select a category.")
                st.rerun()
                return

            image_bytes, filename = _get_pending_receipt()
            if not bypass_receipt and (not image_bytes or not filename):
                _retain_form_values(date_value, amount, description, category)
                _retain_error("Add a receipt image (📷 Take Photo or 📁 Upload File) or check **Save without receipt image**.")
                st.rerun()
                return

            transaction = {
                "date": date_value.strftime("%Y-%m-%d"),
                "user": current_user,
                "category": category,
                "amount": float(amount),
                "description": (description or "").strip(),
            }

            try:
                on_submit(transaction, image_bytes if not bypass_receipt else None, filename if not bypass_receipt else None)
                _clear_pending_receipt()
                _clear_retained_form()
                st.session_state[SUCCESS_MESSAGE_KEY] = True
                st.rerun()
            except Exception as e:
                _retain_form_values(date_value, amount, description, category)
                _retain_error(str(e))
                st.rerun()
