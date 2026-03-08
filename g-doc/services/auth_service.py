"""Google auth: OAuth (personal account) or service account (Workspace/Shared Drive)."""

import json
import os
from pathlib import Path

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.auth.credentials import Credentials as CredentialsBase
from google.auth.transport.requests import Request

# OAuth token file (gitignored via private/)
_OAUTH_TOKEN_FILE = os.environ.get(
    "GOOGLE_OAUTH_TOKEN_FILE",
    str(Path(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "private/credentials.json")).parent / "oauth_token.json"),
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


# -------- OAuth (personal Google account – works with My Drive, no Shared Drive needed) --------


def _oauth_client_config():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8501").strip()
    return {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri}


def get_oauth_credentials_from_storage() -> CredentialsBase | None:
    """Load OAuth credentials from token file if present and valid/refreshable."""
    cfg = _oauth_client_config()
    if not cfg:
        return None
    path = _OAUTH_TOKEN_FILE
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return None
    token = data.get("token")
    expiry = data.get("expiry")
    if expiry:
        from datetime import datetime
        try:
            expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except Exception:
            expiry = None
    creds = OAuthCredentials(
        token=token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=SCOPES,
        expiry=expiry,
    )
    try:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_oauth_credentials(creds)
    except Exception:
        return None
    return creds


def save_oauth_credentials(creds: CredentialsBase) -> None:
    path = _OAUTH_TOKEN_FILE
    if not path:
        return
    dirpath = os.path.dirname(path)
    if dirpath and not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    data = {
        "refresh_token": getattr(creds, "refresh_token", None) or "",
        "token": getattr(creds, "token", None),
        "expiry": getattr(creds, "expiry", None),
        "scopes": getattr(creds, "scopes", SCOPES),
    }
    if data.get("expiry"):
        data["expiry"] = data["expiry"].isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_oauth_authorization_url() -> str | None:
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        return None
    cfg = _oauth_client_config()
    if not cfg:
        return None
    client_config = {
        "web": {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uris": [cfg["redirect_uri"]],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, SCOPES, redirect_uri=cfg["redirect_uri"])
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    return auth_url


def exchange_oauth_code_for_credentials(code: str) -> CredentialsBase | None:
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        return None
    cfg = _oauth_client_config()
    if not cfg:
        return None
    client_config = {
        "web": {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uris": [cfg["redirect_uri"]],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, SCOPES, redirect_uri=cfg["redirect_uri"])
    try:
        flow.fetch_token(code=code)
    except Exception:
        return None
    creds = flow.credentials
    save_oauth_credentials(creds)
    return creds


def is_oauth_configured() -> bool:
    return _oauth_client_config() is not None


# -------- Service account --------


def get_service_account_credentials() -> CredentialsBase | None:
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            account_info = dict(st.secrets["gcp_service_account"])
            return service_account.Credentials.from_service_account_info(account_info, scopes=SCOPES)
    except (ImportError, FileNotFoundError):
        pass
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    if os.path.exists(creds_path):
        return service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return None


# -------- Unified: OAuth first (personal), then service account --------


def get_credentials() -> CredentialsBase:
    creds = get_oauth_credentials_from_storage()
    if creds is not None:
        return creds
    creds = get_service_account_credentials()
    if creds is not None:
        return creds
    raise RuntimeError(
        "No Google credentials. For personal accounts (My Drive): set GOOGLE_OAUTH_CLIENT_ID and "
        "GOOGLE_OAUTH_CLIENT_SECRET in .env and click “Sign in with Google”. "
        "Or use a service account for Workspace/Shared Drives."
    )


def get_credentials_or_none() -> CredentialsBase | None:
    try:
        return get_credentials()
    except RuntimeError:
        return None
