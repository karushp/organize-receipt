# Receipt Tracker (Supabase)

Receipt capture and expense tracking with **Supabase** as the backend and optional **Google Sheets** sync.

## Setup

1. **Supabase**
   - Create a project at [supabase.com](https://supabase.com).
   - Run migrations: `supabase db push` (or run the SQL in `migrations/` via the SQL Editor).
   - Create the `receipts` storage bucket in Dashboard → Storage if the migration didn’t create it (public, ~5MB limit, image MIME types).
   - Copy `.env.example` to `.env` and set `SUPABASE_URL` and `SUPABASE_KEY`.

2. **Python**
   - From this directory: `pip install -r requirements.txt`
   - Optional (for PDF export): already in `requirements.txt` (reportlab, pillow).
   - Optional (for Sheets sync): set `GOOGLE_SHEETS_ID` and `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env`.

## Run the app

From the **supabase** directory:

```bash
streamlit run app/streamlit_app.py
```

### Authentication (for public URL)

To require login before using the app, set credentials in `.env` (never commit `.env`):

- **Single user:** `AUTH_USERNAME` and `AUTH_PASSWORD`
- **Multiple users:** `AUTH_CREDENTIALS=user1:pass1,user2:pass2` (no spaces in each `user:pass`)

If neither is set, the app runs without login. Use strong passwords when the app is exposed on a public URL.

## Sync to Google Sheets

From the **supabase** directory:

```bash
python scripts/sync_to_sheets.py
```

Uses `GOOGLE_SHEETS_ID` (spreadsheet ID from the URL) and `GOOGLE_SERVICE_ACCOUNT_JSON` (path to service account key). Creates one tab per user (from `USERS`) and fills them with `date | category | amount | description | created_date | receipt_url`.

Optional cron (e.g. monthly on the 1st at 2:00):

```bash
0 2 1 * * cd /path/to/supabase && python scripts/sync_to_sheets.py
```

## Layout

- `app/` – Streamlit app and Supabase client/upload/transactions logic.
- `config/` – Categories and other config (e.g. `categories.json`).
- `scripts/` – `sync_to_sheets.py` for Supabase → Google Sheets.
- `utils/` – Image handling and PDF export.
- `migrations/` – Supabase SQL (transactions table, storage bucket/policies).

See `plan.md` for the full project plan.
