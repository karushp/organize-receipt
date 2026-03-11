"""
Push Supabase transactions to Google Sheets (one tab per user).
Used by scripts/sync_to_sheets.py and the Streamlit app "Sync to Sheets" button.
"""
import os
from pathlib import Path

HEADERS = ["date", "category", "amount", "description", "created_date", "receipt_url"]


def _get_sheets_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise RuntimeError("Install gspread and google-auth: pip install gspread google-auth")

    root = Path(__file__).resolve().parent.parent
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    # Try absolute/user path first, then relative to project root
    for candidate in [
        (Path(raw).expanduser() if raw else None),
        (root / raw) if raw else (root / "private" / "credentials.json"),
    ]:
        if candidate and candidate.is_file():
            creds_path = str(candidate.resolve())
            break
    else:
        raise RuntimeError(
            "Set GOOGLE_SERVICE_ACCOUNT_JSON in .env to the path of your service account JSON file."
        )
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scope)
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
            if not user_rows:
                ws.update("A1:F1", [HEADERS])
            else:
                data = [[str(r.get("date", "")), str(r.get("category", "")), str(r.get("amount", "")), str(r.get("description", "")), str(r.get("created_date", "")), str(r.get("receipt_url", ""))] for r in user_rows]
                ws.update("A1", [HEADERS] + data)
    except Exception as e:
        return False, str(e)

    total = sum(len([t for t in all_tx if t.get("user") == u]) for u in USERS)
    return True, f"Synced {len(all_tx)} transactions to tabs: {', '.join(SHEET_TAB_NAMES.get(u, u) for u in USERS)}."
