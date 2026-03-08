# Receipt Organizer (Google Sheets & Drive)

This app lives in the **`g-doc/`** folder. It’s a Streamlit app for recording and organizing expenses and receipts with Google Sheets and Drive.

## Features

- **Multi-user support** - Manage expenses for multiple users
- **Google Sheets integration** - Store expense data in Google Sheets
- **Google Drive integration** - Store and manage receipt files in Google Drive
- **Receipt capture** - Take photos with camera (mobile-friendly) or upload images/PDFs
- **Transaction tracking** - View and manage all transactions in a table format
- **Expense categories** - Organize expenses by category (Food, Transportation, Entertainment, Utilities, Shopping)
- **Print functionality** - Generate printable expense reports

## Running

From the repo root:

```bash
cd g-doc
uv sync
uv run streamlit run app.py
```

Copy `g-doc/.env.example` to `g-doc/.env` and add your Google and user config.

## Project Structure

```
g-doc/
├── app.py                 # Main Streamlit application entry point
├── config.py             # User and category configuration (from .env)
├── pyproject.toml        # Project config & dependencies (uv)
├── components/           # UI components
│   ├── capture_form.py   # Receipt capture form
│   ├── transactions_table.py  # Expense transactions display
│   └── print_section.py  # Report printing functionality
├── services/             # Google services integration
│   ├── auth_service.py   # Authentication
│   ├── sheets_service.py # Google Sheets integration
│   ├── drive_service.py  # Google Drive integration
│   └── pdf_service.py    # PDF processing
├── utils/                # Utility functions
│   ├── date_utils.py     # Date handling utilities
│   ├── id_utils.py       # ID generation utilities
│   └── image_utils.py    # Image processing utilities
└── .streamlit/           # Streamlit configuration
    └── secrets.toml.example
```

## Getting Started

Requires [uv](https://docs.astral.sh/uv/). From the **g-doc** directory: `uv sync` then `uv run streamlit run app.py`. See **Running** above.

**Mobile:** Camera capture works on phones when served over HTTPS (e.g. Streamlit Cloud).

## Technologies

- **Streamlit** - Web framework for the UI
- **Google Sheets API** - For expense data storage
- **Google Drive API** - For receipt file storage
- **Python** - Main programming language 
