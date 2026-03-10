"""
Simple auth for Streamlit: credentials from .env (never in repo).
Set AUTH_CREDENTIALS=user1:pass1,user2:pass2 (one or more logins).
"""
import os

# One format for all logins: AUTH_CREDENTIALS=login1:pass1,login2:pass2 (no spaces in each pair)
def _get_credentials() -> dict[str, str]:
    """Return dict of login_username -> password from env."""
    creds = {}
    raw = os.environ.get("AUTH_CREDENTIALS", "").strip()
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            u, p = pair.split(":", 1)
            creds[u.strip()] = p.strip()
    return creds


def auth_enabled() -> bool:
    """True if any auth credentials are configured."""
    return len(_get_credentials()) > 0


def check_login(username: str, password: str) -> bool:
    """Return True if username/password match configured credentials."""
    creds = _get_credentials()
    return creds.get(username) == password


def is_super_user(username: str | None) -> bool:
    """True if this auth user can select any data user (e.g. user-1, user-2)."""
    from app.config import SUPER_USERS
    return (username or "").strip() in SUPER_USERS


def get_data_user_for_login(username: str) -> str | None:
    """For non-super users: return the data user (e.g. user-1) they are tied to, or None if not mapped."""
    from app.config import USER_DATA_MAP, USERS
    u = username.strip()
    data_user = USER_DATA_MAP.get(u)
    if data_user and data_user in USERS:
        return data_user
    return None
