"""Google Drive API integration for storing receipt images."""

import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.credentials import Credentials

FOLDER_MIMETYPE = "application/vnd.google-apps.folder"


def get_drive_service(credentials: Credentials):
    """Build the Google Drive API service."""
    return build("drive", "v3", credentials=credentials)


def _get_or_create_folder(service, name: str, parent_id: str | None = None) -> str:
    """
    Get or create a folder in the Service Account's Drive.
    parent_id=None means root. Returns the folder's file ID.
    """
    if parent_id:
        q = f"name='{name}' and '{parent_id}' in parents and mimeType='{FOLDER_MIMETYPE}' and trashed=false"
    else:
        q = f"name='{name}' and 'root' in parents and mimeType='{FOLDER_MIMETYPE}' and trashed=false"
    result = service.files().list(q=q, spaces="drive", fields="files(id,name)").execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]
    body = {"name": name, "mimeType": FOLDER_MIMETYPE}
    if parent_id:
        body["parents"] = [parent_id]
    folder = service.files().create(body=body, fields="id").execute()
    return folder["id"]


def _add_reader_permission(service, file_id: str, email_address: str) -> None:
    """Share the file with the given email so it appears in their Drive (Shared with me)."""
    if not email_address:
        return
    service.permissions().create(
        fileId=file_id,
        body={
            "type": "user",
            "role": "reader",
            "emailAddress": email_address,
        },
    ).execute()


def upload_receipt_image(
    service,
    folder_id: str,
    file_data: bytes,
    filename: str,
    mime_type: str = "image/jpeg",
    share_with_email: str | None = None,
    user_name: str | None = None,
) -> str:
    """
    Upload a receipt image to Drive and optionally share with an email.

    - If folder_id is set: upload to that folder (e.g. user's folder or Shared Drive).
    - If folder_id is empty and user_name is set: upload to Service Account's Drive
      under receipts/<user_name>, so it works for personal accounts (no quota error).
    - If share_with_email is set: share the file with that address (reader) so it
      shows in their "Shared with me".
    Returns the file ID of the uploaded file.
    """
    effective_folder_id = folder_id
    if not (effective_folder_id or "").strip() and user_name:
        receipts_id = _get_or_create_folder(service, "receipts", parent_id=None)
        effective_folder_id = _get_or_create_folder(
            service, user_name, parent_id=receipts_id
        )

    file_metadata = {"name": filename}
    if effective_folder_id:
        file_metadata["parents"] = [effective_folder_id]

    media = MediaIoBaseUpload(
        io.BytesIO(file_data),
        mimetype=mime_type,
        resumable=False,
    )
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    file_id = file["id"]

    if share_with_email:
        _add_reader_permission(service, file_id, share_with_email)

    return file_id


def delete_file(service, file_id: str) -> None:
    """Permanently delete a file from Google Drive."""
    try:
        service.files().delete(fileId=file_id).execute()
    except Exception:
        pass  # File may already be deleted


def get_file_download_url(service, file_id: str) -> str:
    """Get a direct download URL for a Drive file (for viewing in app)."""
    try:
        file = service.files().get(fileId=file_id, fields="webContentLink").execute()
        return file.get("webContentLink", "") or f"https://drive.google.com/uc?id={file_id}"
    except Exception:
        return f"https://drive.google.com/uc?id={file_id}"
