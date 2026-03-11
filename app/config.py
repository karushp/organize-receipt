"""App config: project paths, env loading, users, and other settings from environment."""
import json
import os
from pathlib import Path

# Project root (parent of app/)
ROOT = Path(__file__).resolve().parent.parent


def ensure_env_loaded():
    """Load .env from project root (and cwd fallback). Safe to call multiple times."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
        load_dotenv()
    except ImportError:
        pass


ensure_env_loaded()

# Users: comma-separated in .env (e.g. USERS=user-1,user-2) – data users (tabs, receipts)
_users_raw = os.environ.get("USERS", "user-1,user-2")
USERS = [u.strip() for u in _users_raw.split(",") if u.strip()]
if not USERS:
    USERS = ["user-1", "user-2"]  # fallback

# Google Sheets tab name per user. Optional: USER_1_SHEET_TAB=My Tab Name (default = user name)
SHEET_TAB_NAMES = {
    u: os.environ.get(f"{u}_SHEET_TAB", u) for u in USERS
}

# Super users: auth usernames who can select any data user (USERS). Others are tied to one data user.
_super_raw = os.environ.get("SUPER_USERS", "").strip()
SUPER_USERS = [u.strip() for u in _super_raw.split(",") if u.strip()]

# Map auth username -> data user (e.g. alice:user-1,bob:user-2). Required for non-super logins.
_user_map_raw = os.environ.get("USER_DATA_MAP", "").strip()
USER_DATA_MAP = {}
for pair in _user_map_raw.split(","):
    pair = pair.strip()
    if ":" in pair:
        auth_u, data_u = pair.split(":", 1)
        USER_DATA_MAP[auth_u.strip()] = data_u.strip()

# Display
DEFAULT_CURRENCY = "$"


def load_categories() -> list:
    """Load category list from config/categories.json."""
    path = ROOT / "config" / "categories.json"
    with open(path) as f:
        return json.load(f)
