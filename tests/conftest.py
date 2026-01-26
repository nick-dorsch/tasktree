"""
Pytest configuration and fixtures for tasktree tests.
"""

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest

from tasktree_mcp.db_init import initialize_database


@pytest.fixture(scope="function")
def test_db() -> Generator[Path, None, None]:
    """
    Create a temporary test database with schema and views for each test.

    This fixture:
    1. Creates a temporary SQLite database file
    2. Applies the database schema from sql/schemas/
    3. Applies the database views from sql/views/
    4. Provides an isolated database for each test
    5. Automatically cleans up after the test

    Yields:
        Path: Path to the temporary test database file
    """
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    db_path = Path(temp_db.name)
    temp_db.close()

    try:
        # Initialize database using bundled SQL assets
        initialize_database(db_path, apply_views_flag=True)

        # Yield the database path to the test
        yield db_path

    finally:
        # Clean up: remove the temporary database file
        if db_path.exists():
            db_path.unlink()


@pytest.fixture(scope="function")
def test_db_connection(test_db: Path) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a database connection to the test database.

    This fixture depends on the test_db fixture and provides
    a ready-to-use connection with row_factory set.

    Args:
        test_db: Path to the test database (from test_db fixture)

    Yields:
        sqlite3.Connection: Active database connection
    """
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_test_db_connection(db_path: Path):
    """
    Context manager for getting a test database connection.

    Use this in tests when you need to override the default
    database connection with a test database connection.

    Args:
        db_path: Path to the test database

    Yields:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
