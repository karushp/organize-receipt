import os

# Users: comma-separated in .env (e.g. USERS=KP,ASB). Per-user: {USER}_SHEET_ID, {USER}_DRIVE_FOLDER_ID
_users_raw = os.environ.get("USERS", "")
USERS = [u.strip() for u in _users_raw.split(",") if u.strip()]

USER_CONFIG = {
    user: {
        "sheet_id": os.environ.get(f"{user}_SHEET_ID", ""),
        "drive_folder_id": os.environ.get(f"{user}_DRIVE_FOLDER_ID", ""),
    }
    for user in USERS
}

# Categories: comma-separated in .env (e.g. CATEGORIES=Food,Transportation,...)
_categories_raw = os.environ.get("CATEGORIES", "")
CATEGORIES = [c.strip() for c in _categories_raw.split(",") if c.strip()]
if not CATEGORIES:
    CATEGORIES = ["Uncategorized"]