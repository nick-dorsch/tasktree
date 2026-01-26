"""
Tests for database fixtures.
"""

from pathlib import Path


def test_db_fixture_creates_database(test_db: Path):
    """Test that the test_db fixture creates a valid database file."""
    assert test_db.exists()
    assert test_db.suffix == ".db"
