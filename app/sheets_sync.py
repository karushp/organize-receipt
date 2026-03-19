"""
Push Supabase transactions to Google Sheets (one tab per user).
Used by scripts/sync_to_sheets.py and the Streamlit app "Sync to Sheets" button.
"""
import json
import os
from pathlib import Path

HEADERS = ["date", "category", "amount", "description", "created_date", "receipt_url"]


def _row_for_sheet(transaction: dict) -> list:
    """Build a sheet row from a transaction dict using HEADERS order."""
    return [str(transaction.get(h, "")) for h in HEADERS]


def _get_sheets_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise RuntimeError("Install gspread and google-auth: pip install gspread google-auth")

    from app.config import ROOT
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # GOOGLE_SERVICE_ACCOUNT_JSON can be either:
    # - a file path (absolute or relative to project root)
    # - the JSON content (useful on hosted deployments where files aren't present)
    creds = None
    if raw.startswith("{"):
        try:
            info = json.loads(raw)
            creds = Credentials.from_service_account_info(info, scopes=scope)
        except Exception:
            creds = None
    elif raw:
        # Try absolute/user path first, then relative to project root
        for candidate in [Path(raw).expanduser(), ROOT / raw]:
            if candidate.is_file():
                creds = Credentials.from_service_account_file(str(candidate.resolve()), scopes=scope)
                break

    if creds is None:
        default_path = ROOT / "private" / "credentials.json"
        if default_path.is_file():
            creds = Credentials.from_service_account_file(str(default_path.resolve()), scopes=scope)

    if creds is None:
        raise RuntimeError(
            "Set GOOGLE_SERVICE_ACCOUNT_JSON to either (1) a path to your service account JSON file "
            "or (2) the JSON content itself (recommended for hosted deployments)."
        )
    return gspread.authorize(creds)


def run_sync():
    """
    Fetch all transactions from Supabase and write to Google Sheets (one tab per user).
    Returns (success: bool, message: str).
    """
    from app.supabase_client import get_client
    from app.transactions import get_all_transactions
    from app.config import USERS, SHEET_TAB_NAMES

    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not spreadsheet_id or not spreadsheet_id.strip():
        return False, "Set GOOGLE_SHEETS_ID in .env (spreadsheet ID from the sheet URL)."

    try:
        all_tx = get_all_transactions()
    except Exception as e:
        return False, f"Supabase: {e}"

    try:
        gc = _get_sheets_client()
    except Exception as e:
        return False, str(e)

    try:
        sh = gc.open_by_key(spreadsheet_id)
    except Exception as e:
        err = str(e).lower()
        if "404" in err or "not found" in err or "permission" in err:
            return False, (
                "Cannot open the spreadsheet. Share it with your service account email "
                "(in the JSON key file, field 'client_email') and give it Editor access."
            )
        return False, str(e)

    try:
        for user in USERS:
            user_rows = [t for t in all_tx if t.get("user") == user]
            user_rows.sort(key=lambda x: (x.get("date") or "", x.get("id") or ""))
            title = SHEET_TAB_NAMES.get(user, user)
            try:
                ws = sh.worksheet(title)
            except Exception:
                ws = sh.add_worksheet(title=title, rows=1000, cols=10)
            # Always clear first so deleted transactions disappear from the sheet
            ws.clear()
            data = [_row_for_sheet(r) for r in user_rows]
            ws.update("A1", [HEADERS] + data)
    except Exception as e:
        return False, str(e)

    return True, f"Synced {len(all_tx)} transactions to tabs: {', '.join(SHEET_TAB_NAMES.get(u, u) for u in USERS)}."
