"""
Pytest configuration and fixtures.
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ.setdefault("DEBUG", "true")


@pytest.fixture(scope="session")
def app():
    """Create Flask application for testing."""
    from src.app import create_app
    
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="session")
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="session")
def settings():
    """Get application settings."""
    from src.config import get_settings
    return get_settings()
