"""Google Sheets API integration for storing receipt transactions."""

from googleapiclient.discovery import build
from google.auth.credentials import Credentials

from config import USER_CONFIG

SHEET_NAME = "Transactions"
HEADERS = ["id", "date", "item", "category", "amount", "drive_file_id"]


def get_sheets_service(credentials: Credentials):
    """Build the Google Sheets API service."""
    return build("sheets", "v4", credentials=credentials)


def ensure_sheet_ready(service, sheet_id: str) -> None:
    """Ensure the sheet has the Transactions tab with headers. Creates it if missing."""
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_names = [s["properties"]["title"] for s in spreadsheet["sheets"]]

    if SHEET_NAME not in sheet_names:
        # Create the Transactions sheet
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={
                "requests": [
                    {
                        "addSheet": {
                            "properties": {"title": SHEET_NAME},
                        }
                    }
                ]
            },
        ).execute()

    # Get sheet ID for Transactions
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    for s in spreadsheet["sheets"]:
        if s["properties"]["title"] == SHEET_NAME:
            sheet_id_internal = s["properties"]["sheetId"]
            break
    else:
        return

    # Check if headers exist
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"'{SHEET_NAME}'!A1:F1")
        .execute()
    )
    values = result.get("values", [])

    if not values or values[0] != HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{SHEET_NAME}'!A1:F1",
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()


def get_all_transactions(service, sheet_id: str) -> list[dict]:
    """Fetch all transactions from the sheet."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"'{SHEET_NAME}'!A2:F")
        .execute()
    )
    values = result.get("values", [])

    transactions = []
    for row in values:
        if len(row) >= 5:
            transactions.append(
                {
                    "id": row[0] if len(row) > 0 else "",
                    "date": row[1] if len(row) > 1 else "",
                    "item": row[2] if len(row) > 2 else "",
                    "category": row[3] if len(row) > 3 else "",
                    "amount": row[4] if len(row) > 4 else "",
                    "drive_file_id": row[5] if len(row) > 5 else "",
                }
            )
    return transactions


def append_transaction(
    service,
    sheet_id: str,
    transaction: dict,
) -> None:
    """Append a new transaction row to the sheet."""
    ensure_sheet_ready(service, sheet_id)

    row = [
        transaction.get("id", ""),
        transaction.get("date", ""),
        transaction.get("item", ""),
        transaction.get("category", ""),
        str(transaction.get("amount", "")),
        transaction.get("drive_file_id", ""),
    ]
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"'{SHEET_NAME}'!A:F",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def delete_transaction_by_id(service, sheet_id: str, transaction_id: str) -> None:
    """Delete a transaction row by ID."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"'{SHEET_NAME}'!A2:F")
        .execute()
    )
    values = result.get("values", [])
    row_index = None
    for i, row in enumerate(values):
        if row and row[0] == transaction_id:
            row_index = i + 2  # 1-based, +1 for header
            break

    if row_index is None:
        return

    # Delete the row
    spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    for s in spreadsheet["sheets"]:
        if s["properties"]["title"] == SHEET_NAME:
            sheet_id_internal = s["properties"]["sheetId"]
            break
    else:
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id_internal,
                            "dimension": "ROWS",
                            "startIndex": row_index - 1,
                            "endIndex": row_index,
                        }
                    }
                }
            ]
        },
    ).execute()
