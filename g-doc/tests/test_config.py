"""Tests that run with .env loaded (credentials and sheet/drive IDs available)."""


def test_env_loaded():
    """Ensure .env is loaded so config and auth can use credentials."""
    import os

    # At least one of: key file path or GCP env vars should be set when .env is present
    has_key_path = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    has_gcp_creds = all(
        os.environ.get(k)
        for k in ("GCP_PROJECT_ID", "GCP_PRIVATE_KEY", "GCP_CLIENT_EMAIL")
    )
    assert has_key_path or has_gcp_creds, (
        "No credentials in env. Copy .env.example to .env and add "
        "GOOGLE_APPLICATION_CREDENTIALS or GCP_PROJECT_ID / GCP_PRIVATE_KEY / GCP_CLIENT_EMAIL."
    )


def test_config_has_sheet_and_drive_ids():
    """Ensure at least one user has sheet_id and drive_folder_id from .env."""
    from config import USER_CONFIG

    for user, cfg in USER_CONFIG.items():
        if cfg.get("sheet_id") and cfg.get("drive_folder_id"):
            return  # at least one user configured
    raise AssertionError(
        "No user in USERS has both {user}_SHEET_ID and {user}_DRIVE_FOLDER_ID set in .env."
    )
