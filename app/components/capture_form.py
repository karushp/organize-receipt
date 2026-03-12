"""Capture form: Take Photo / Upload File tabs, then save to Supabase."""

from datetime import date

import streamlit as st

from utils.receipt_scanner import scan_receipt_image_bytes

PENDING_RECEIPT_KEY = "capture_form_pending_receipt"
SHOW_CAMERA_KEY = "capture_form_show_camera"
RETAINED_FORM_KEY = "capture_form_retained"
RETAINED_ERROR_KEY = "capture_form_retained_error"
SUCCESS_MESSAGE_KEY = "capture_form_show_success"

CATEGORY_PLACEHOLDER = "Select one"
DEFAULT_RECEIPT_FILENAME = "receipt.jpg"
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def _get_pending_receipt() -> tuple[bytes | None, str]:
    data = st.session_state.get(PENDING_RECEIPT_KEY)
    if data is None:
        return None, ""
    return data.get("bytes"), data.get("filename", "")


def _set_pending_receipt(image_bytes: bytes, filename: str) -> None:
    st.session_state[PENDING_RECEIPT_KEY] = {"bytes": image_bytes, "filename": filename}


def _clear_pending_receipt() -> None:
    if PENDING_RECEIPT_KEY in st.session_state:
        del st.session_state[PENDING_RECEIPT_KEY]


def _normalize_receipt_filename(name: str | None) -> str:
    if not name or not name.lower().endswith(ALLOWED_EXTENSIONS):
        return DEFAULT_RECEIPT_FILENAME
    return name


def _process_and_set_pending_receipt(raw_bytes: bytes, filename: str) -> None:
    processed = scan_receipt_image_bytes(raw_bytes)
    _set_pending_receipt(processed, _normalize_receipt_filename(filename))


def _retain_form_values(
    date_value: date | None,
    amount: float,
    description: str,
    category: str,
) -> None:
    st.session_state[RETAINED_FORM_KEY] = {
        "date": date_value,
        "amount": amount,
        "description": description or "",
        "category": category,
    }


def _get_retained_form_values() -> dict | None:
    return st.session_state.get(RETAINED_FORM_KEY)


def _clear_retained_form() -> None:
    for key in (RETAINED_FORM_KEY, RETAINED_ERROR_KEY):
        if key in st.session_state:
            del st.session_state[key]


def _retain_error(msg: str) -> None:
    st.session_state[RETAINED_ERROR_KEY] = msg


def _show_retained_error() -> None:
    err = st.session_state.pop(RETAINED_ERROR_KEY, None)
    if err:
        st.error(err)


def _default_date_from_retained(retained: dict | None) -> date:
    if not retained or not retained.get("date"):
        return date.today()
    d = retained["date"]
    if hasattr(d, "strftime"):
        return d
    if isinstance(d, str):
        try:
            return date.fromisoformat(d)
        except ValueError:
            pass
    return date.today()


def _render_camera_tab() -> None:
    show_camera = st.session_state.get(SHOW_CAMERA_KEY, False)
    if show_camera:
        camera_img = st.camera_input(
            "Capture receipt",
            key="receipt_camera",
            help="Center the receipt in the frame. The app will crop the middle strip.",
        )
        if st.button("Close camera", key="close_camera"):
            st.session_state[SHOW_CAMERA_KEY] = False
            st.rerun()
        if camera_img:
            _process_and_set_pending_receipt(
                camera_img.getvalue(),
                getattr(camera_img, "name", None) or DEFAULT_RECEIPT_FILENAME,
            )
            st.session_state[SHOW_CAMERA_KEY] = False
            st.rerun()
    else:
        if st.button("📷 Capture receipt", key="open_camera", type="primary"):
            st.session_state[SHOW_CAMERA_KEY] = True
            st.rerun()


def _render_upload_tab() -> None:
    image_file = st.file_uploader(
        "Receipt Image",
        type=["jpg", "jpeg", "png", "webp", "heic"],
        key="receipt_upload",
        help="Upload receipt photo",
    )
    if image_file:
        raw_bytes = image_file.read()
        if raw_bytes:
            _process_and_set_pending_receipt(raw_bytes, image_file.name)


def _render_receipt_preview() -> None:
    pending_bytes, _ = _get_pending_receipt()
    if pending_bytes:
        st.caption("✅ Preview — this is the cropped area that will be saved.")
        st.image(
            pending_bytes,
            caption="This image will be attached to your receipt entry.",
            width="stretch",
        )
        if st.button(
            "Clear and take another",
            key="clear_receipt",
            help="Remove this image and capture or upload a new one",
        ):
            _clear_pending_receipt()
            st.rerun()
    else:
        st.caption("Optional: add a receipt image, or check **Save without receipt** below.")


def _render_transaction_form(
    categories: list[str],
    on_submit,
    current_user: str,
) -> None:
    retained = _get_retained_form_values()
    _show_retained_error()

    category_options = [CATEGORY_PLACEHOLDER] + (categories or ["Other"])

    with st.form("capture_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([1.2, 1, 2.2, 1.8])

        with col1:
            date_value = st.date_input(
                "Date",
                value=_default_date_from_retained(retained),
                format="YYYY-MM-DD",
            )

        with col2:
            default_amount = 0.0
            if retained and retained.get("amount") is not None:
                try:
                    default_amount = float(retained["amount"])
                except (TypeError, ValueError):
                    pass
            amount = st.number_input(
                "Amount ($)",
                value=default_amount,
                min_value=0.0,
                step=0.01,
                format="%.2f",
            )

        with col3:
            default_desc = (retained or {}).get("description", "")
            description = st.text_input(
                "Description",
                value=default_desc,
                placeholder="e.g. Shimamura clothes shopping",
            )

        with col4:
            default_cat = (retained or {}).get("category", "")
            cat_index = (
                category_options.index(default_cat)
                if default_cat and default_cat in categories
                else 0
            )
            category = st.selectbox(
                "Category (required)",
                options=category_options,
                index=cat_index,
            )

        bypass_receipt = st.checkbox(
            "Save without receipt image",
            key="bypass_receipt",
            help="Save the entry with no photo.",
        )
        submitted = st.form_submit_button("Save Receipt")

        if submitted:
            _handle_form_submit(
                date_value=date_value,
                amount=amount,
                description=description,
                category=category,
                category_options=category_options,
                bypass_receipt=bypass_receipt,
                on_submit=on_submit,
                current_user=current_user,
            )


def _handle_form_submit(
    *,
    date_value: date,
    amount: float,
    description: str,
    category: str,
    category_options: list[str],
    bypass_receipt: bool,
    on_submit,
    current_user: str,
) -> None:
    retained_cat = category if category != CATEGORY_PLACEHOLDER else ""

    if date_value is None:
        _retain_form_values(date_value, amount, description, retained_cat)
        st.error("Please select a date.")
        st.rerun()
        return

    if amount is None or amount < 0:
        _retain_form_values(date_value, amount, description, retained_cat)
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
        _retain_error(
            "Add a receipt image (📷 Take Photo or 📁 Upload File) or check **Save without receipt image**."
        )
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
        on_submit(
            transaction,
            image_bytes if not bypass_receipt else None,
            filename if not bypass_receipt else None,
        )
        _clear_pending_receipt()
        _clear_retained_form()
        st.session_state[SUCCESS_MESSAGE_KEY] = True
        st.rerun()
    except Exception as e:
        _retain_form_values(date_value, amount, description, category)
        _retain_error(str(e))
        st.rerun()


def render_capture_form(
    categories: list[str],
    on_submit,
    current_user: str,
) -> None:
    """
    Render the Add Receipt section: image source tabs, preview, and transaction form.

    current_user: the selected user (from "Adding as X"); all new entries go to this user.
    on_submit(transaction_dict, image_bytes, filename) where image_bytes/filename may be None if bypass receipt.
    """
    st.subheader("Add Receipt")

    tab_photo, tab_upload = st.tabs(["📷 Take Photo", "📁 Upload File"])
    with tab_photo:
        _render_camera_tab()
    with tab_upload:
        _render_upload_tab()

    _render_receipt_preview()
    _render_transaction_form(categories, on_submit, current_user)
