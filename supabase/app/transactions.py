"""CRUD for transactions table."""
from datetime import date

from app.supabase_client import get_client
from app.upload_receipt import _amount_for_db


def get_all_transactions():
    """Fetch all transactions, newest first."""
    client = get_client()
    resp = client.table("transactions").select("*").order("date", desc=True).execute()
    return resp.data or []


def get_transactions_filtered(month: date | None = None, user: str | None = None):
    """Fetch transactions optionally filtered by month and/or user."""
    client = get_client()
    q = client.table("transactions").select("*")
    if user:
        q = q.eq("user", user)
    if month:
        start = date(month.year, month.month, 1)
        if month.month == 12:
            end = date(month.year, 12, 31)
        else:
            end = date(month.year, month.month + 1, 1)
        from datetime import timedelta
        end = end - timedelta(days=1)
        q = q.gte("date", start.isoformat()).lte("date", end.isoformat())
    q = q.order("date", desc=True)
    resp = q.execute()
    return resp.data or []


def update_transaction(
    id: str,
    *,
    date_val: date | None = None,
    user: str | None = None,
    category: str | None = None,
    amount: float | None = None,
    description: str | None = None,
) -> dict:
    """Update a transaction by id. Only provided fields are updated."""
    client = get_client()
    payload = {}
    if date_val is not None:
        payload["date"] = date_val.isoformat()
    if user is not None:
        payload["user"] = user
    if category is not None:
        payload["category"] = category
    if amount is not None:
        payload["amount"] = _amount_for_db(amount)
    if description is not None:
        payload["description"] = description
    if not payload:
        return get_transaction_by_id(id)
    resp = client.table("transactions").update(payload).eq("id", id).execute()
    if not resp.data or len(resp.data) == 0:
        raise RuntimeError("Update failed: no data returned")
    return resp.data[0]


def get_transaction_by_id(id: str) -> dict | None:
    """Get a single transaction by id."""
    client = get_client()
    resp = client.table("transactions").select("*").eq("id", id).execute()
    if not resp.data or len(resp.data) == 0:
        return None
    return resp.data[0]


def delete_transaction(id: str) -> None:
    """Delete a transaction by id."""
    client = get_client()
    client.table("transactions").delete().eq("id", id).execute()
