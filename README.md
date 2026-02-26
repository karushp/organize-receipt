# organize-receipt

A Streamlit web application for recording and organizing expenses and receipts with cloud integration.

## Features

- **Multi-user support** - Manage expenses for multiple users
- **Google Sheets integration** - Store expense data in Google Sheets
- **Google Drive integration** - Store and manage receipt files in Google Drive
- **Receipt capture** - Capture and process receipt images/PDFs
- **Transaction tracking** - View and manage all transactions in a table format
- **Expense categories** - Organize expenses by category (Food, Transportation, Entertainment, Utilities, Shopping)
- **Print functionality** - Generate printable expense reports

## Project Structure

```
organize-receipt/
├── app.py                 # Main Streamlit application entry point
├── config.py             # User and category configuration
├── requirements.txt      # Python dependencies
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
└── streamlit/            # Streamlit configuration
    └── secrets.toml      # API secrets and credentials
```

## Technologies

- **Streamlit** - Web framework for the UI
- **Google Sheets API** - For expense data storage
- **Google Drive API** - For receipt file storage
- **Python** - Main programming language 
