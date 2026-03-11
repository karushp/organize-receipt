"""Supabase client singleton for the receipt tracker."""
import os

from supabase import create_client, Client

_client: Client | None = None


def _ensure_env_loaded():
    """Load .env from project root so credentials are available when client is created."""
    from app.config import ensure_env_loaded
    ensure_env_loaded()


def get_client() -> Client:
    global _client
    if _client is None:
        _ensure_env_loaded()

        url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
        key = (os.environ.get("SUPABASE_KEY") or "").strip()

        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set. "
                "Add them to .env in the project root and run: uv run streamlit run app/streamlit_app.py"
            )

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        _client = create_client(url, key)
    return _client


def first_row(resp, *, or_raise: bool = False):
    """
    Return the first row from a Supabase select/insert/update response, or None if empty.
    If or_raise=True, raise RuntimeError when no row is returned.
    """
    data = getattr(resp, "data", None) or []
    if not data:
        if or_raise:
            raise RuntimeError("No data returned")
        return None
    return data[0]
