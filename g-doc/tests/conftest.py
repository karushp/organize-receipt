"""Pytest configuration. Load .env so tests have access to credentials and config."""
import pytest
from dotenv import load_dotenv

# Load .env before any test runs so USER_CONFIG and get_credentials() see real values
load_dotenv()
