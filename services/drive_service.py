"""Google Drive API integration for storing receipt images."""

import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.credentials import Credentials


def get_drive_service(credentials: Credentials):
    """Build the Google Drive API service."""
    return build("drive", "v3", credentials=credentials)


def upload_receipt_image(
    service,
    folder_id: str,
    file_data: bytes,
    filename: str,
    mime_type: str = "image/jpeg",
) -> str:
    """
    Upload a receipt image to the specified Drive folder.
    Returns the file ID of the uploaded file.
    """
    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
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
    return file["id"]


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
