"""
Sync transactions from Supabase to Google Sheets (one tab per user).
Run from supabase/: uv run python scripts/sync_to_sheets.py
Requires in .env: GOOGLE_SHEETS_ID, GOOGLE_SERVICE_ACCOUNT_JSON
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.sheets_sync import run_sync


def main():
    print("Syncing Supabase → Google Sheets...")
    ok, msg = run_sync()
    if ok:
        print(msg)
    else:
        print(f"Error: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
