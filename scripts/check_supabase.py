#!/usr/bin/env python3
"""
Test Supabase setup. Run from project root: uv run python scripts/check_supabase.py
Optional: uv run python scripts/check_supabase.py --full  (also tests insert + storage)
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
load_dotenv()

def main():
    full = "--full" in sys.argv
    ok = True

    # 1. Env
    print("1. Environment")
    url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_KEY") or "").strip()
    if not url:
        print("   FAIL: SUPABASE_URL missing in .env")
        ok = False
    else:
        print(f"   OK: SUPABASE_URL set ({len(url)} chars)")
    if not key:
        print("   FAIL: SUPABASE_KEY missing in .env")
        ok = False
    else:
        print("   OK: SUPABASE_KEY set")
    if not ok:
        return 1
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    print()

    # 2. Connection + table
    print("2. Supabase connection & transactions table")
    client = None
    try:
        from supabase import create_client
        client = create_client(url, key)
        resp = client.table("transactions").select("id").limit(1).execute()
        print("   OK: Connected. Table 'transactions' exists.")
    except Exception as e:
        err = str(e)
        if "PGRST205" in err or "schema cache" in err or "not find the table" in err:
            print("   FAIL: Table 'transactions' not found. Run migrations:")
            print("      migrations/20250308000001_create_transactions_table.sql")
            print("      migrations/20250308000002_storage_receipts_bucket.sql")
            ok = False
        else:
            print(f"   FAIL: {e}")
            ok = False
    print()

    if not ok:
        return 1

    # 3. Storage bucket (list – may fail if bucket or policies missing)
    print("3. Storage bucket 'receipts'")
    if client:
        try:
            client.storage.from_("receipts").list()
            print("   OK: Bucket 'receipts' exists and is readable.")
        except Exception as e:
            err = str(e)
            if "Bucket not found" in err or "404" in err or "not find" in err.lower():
                print("   FAIL: Bucket missing. Run migration:")
                print("      migrations/20250308000002_storage_receipts_bucket.sql")
            else:
                print(f"   WARN: {e}")
    print()

    # 4. Optional: insert + select
    if full and client:
        print("4. Insert / select (--full)")
        try:
            from app.transactions import get_all_transactions, delete_transaction
            from app.upload_receipt import insert_transaction
            from datetime import date
            row = insert_transaction(
                date_val=date.today(),
                user="KP",
                category="Other",
                amount=0.01,
                description="test",
                receipt_url=None,
            )
            print("   OK: Insert succeeded.")
            tx_id = row["id"]
            rows = get_all_transactions()
            if any(r["id"] == tx_id for r in rows):
                print("   OK: Select found the row.")
            delete_transaction(tx_id)
            print("   OK: Test row deleted.")
        except Exception as e:
            print(f"   FAIL: {e}")
            ok = False
        print()

    print("All checks passed." if ok else "Some checks failed.")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
