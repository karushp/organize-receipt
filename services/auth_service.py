"""Google authentication service using service account credentials."""

from google.oauth2 import service_account
from google.auth.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def get_credentials() -> Credentials:
    """Get Google API credentials from Streamlit secrets or environment."""
    try:
        import streamlit as st

        if "gcp_service_account" in st.secrets:
            account_info = dict(st.secrets["gcp_service_account"])
            return service_account.Credentials.from_service_account_info(
                account_info, scopes=SCOPES
            )
    except (ImportError, FileNotFoundError):
        pass

    # Fallback: try loading from file path (e.g. for local dev)
    import os

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    if os.path.exists(creds_path):
        return service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES
        )

    raise RuntimeError(
        "No Google credentials found. Configure .streamlit/secrets.toml with "
        "gcp_service_account or set GOOGLE_APPLICATION_CREDENTIALS to a JSON key file."
    )
