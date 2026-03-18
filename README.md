# organize-receipt

Receipt capture and expense tracking with **Supabase** and optional **Google Sheets** sync.

## Setup

1. **Supabase**
   - Create a project at [supabase.com](https://supabase.com).
   - Run the SQL in `migrations/` via the SQL Editor (transactions table + receipts storage bucket).
   - Copy `.env.example` to `.env` and set `SUPABASE_URL` and `SUPABASE_KEY`.

2. **Python**
   - From project root: `uv sync` (or `pip install -r requirements.txt`).
   - Optional (Sheets sync): set `GOOGLE_SHEETS_ID` and `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env` (see `.env.example`).

## Run the app

From the **project root**:

```bash
uv run streamlit run app/streamlit_app.py
```

### Authentication (optional)

Set `AUTH_CREDENTIALS=login1:pass1,login2:pass2` in `.env`. Use `SUPER_USERS` and `USER_DATA_MAP` for super vs regular users (see `.env.example`).

## PDF exports (statement + receipts)

In the app, open **Download Statement** to generate PDFs for a selected month (and optionally a selected user):

- **Statement only**: transaction table.
- **Statement + receipts**: statement table followed by receipt grid pages.
- **Receipts only**: receipt grid pages.

Receipt pages are laid out in a fixed grid (A4) and the heading includes the selected month (e.g. “Receipts — March 2026”).

### Receipt image cropping

When you **take a photo** or **upload** a receipt image, the app crops it to match the print-template cell ratio (**171:365**, width:height) so it fits cleanly in the PDF grid without distortion.

## Sync to Google Sheets

From the **project root**:

```bash
uv run python scripts/sync_to_sheets.py
```

Or use the **Sync to Google Sheets** button in the app sidebar.

## Layout

- `app/` – Streamlit app, Supabase client, upload/transactions, auth, sheets sync.
- `config/` – Categories (`categories.json`).
- `scripts/` – `sync_to_sheets.py`, `check_supabase.py`.
- `utils/` – Image handling, PDF export, shared helpers.
- `migrations/` – Supabase SQL (transactions table, storage bucket).

See `plan.md` for the full project plan.
