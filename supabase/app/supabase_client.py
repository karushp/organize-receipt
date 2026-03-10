"""Supabase client singleton for the receipt tracker."""
import os
from pathlib import Path

from supabase import create_client, Client

_client: Client | None = None


def _ensure_env_loaded():
    """Load .env from supabase/ so credentials are always read from file when client is created."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(env_path, override=False)  # don't override if already set (e.g. by deployment)
        if not os.environ.get("SUPABASE_URL"):
            load_dotenv()  # fallback: cwd .env
    except ImportError:
        pass


def get_client() -> Client:
    global _client
    if _client is None:
        _ensure_env_loaded()

        url = (os.environ.get("SUPABASE_URL") or "").strip().rstrip("/")
        key = (os.environ.get("SUPABASE_KEY") or "").strip()

        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set. "
                "Add them to supabase/.env and run from the supabase directory: "
                "cd supabase && uv run streamlit run app/streamlit_app.py"
            )

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        _client = create_client(url, key)
    return _client
