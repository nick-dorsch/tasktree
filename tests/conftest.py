"""
Pytest configuration and fixtures for tasktree tests.
"""

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterator

import pytest

from tasktree.db.init import initialize_database


@pytest.fixture(scope="session")
def test_db() -> Generator[Path, None, None]:
    """
    Create a temporary test database with schema and views for the session.

    This fixture:
    1. Creates a temporary SQLite database file
    2. Applies the database schema from sql/schemas/
    3. Applies the database views from sql/views/
    4. Provides a shared database for the test session
    5. Automatically cleans up after the test session

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


class _ConnectionProxy:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def commit(self) -> None:
        """No-op commit to keep transaction open for rollback."""

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


class _SharedConnectionProxy(_ConnectionProxy):
    def close(self) -> None:
        """No-op close to keep the shared connection open."""
        return None


@pytest.fixture(scope="function", autouse=True)
def _db_transaction(test_db: Path, monkeypatch) -> Iterator[None]:
    """
    Wrap each test in a transaction and roll back after.

    This fixture monkeypatches tasktree.core.database.get_db_connection to
    always return the same connection (with commits disabled), so tests are
    isolated via rollback while using a session-scoped database.
    """
    import tasktree.core.database as db_module

    conn = sqlite3.connect(test_db, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("BEGIN")

    proxy = _ConnectionProxy(conn)
    shared_proxy = _SharedConnectionProxy(conn)

    sqlite3_connect = sqlite3.connect

    def _shared_connect(database, *args, **kwargs):
        try:
            db_path = Path(database)
        except TypeError:
            db_path = None

        if db_path == test_db or str(database) == str(test_db):
            return shared_proxy

        return sqlite3_connect(database, *args, **kwargs)

    @contextmanager
    def _get_db_connection() -> Iterator[_ConnectionProxy]:
        yield proxy

    monkeypatch.setattr(db_module, "get_db_connection", _get_db_connection)
    monkeypatch.setattr(sqlite3, "connect", _shared_connect)

    try:
        yield
    finally:
        conn.rollback()
        conn.close()


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
