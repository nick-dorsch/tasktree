"""
Tests for database operations using the test_db fixture.
"""

from pathlib import Path

import pytest
import sqlite3


def test_db_fixture_creates_database(test_db: Path):
    """Test that the test_db fixture creates a valid database file."""
    assert test_db.exists()
    assert test_db.suffix == ".db"


def test_db_has_tasks_table(test_db_connection: sqlite3.Connection):
    """Test that the tasks table exists and has the correct schema."""
    cursor = test_db_connection.cursor()

    # Check that tasks table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    result = cursor.fetchone()
    assert result is not None

    # Check that the table has expected columns
    cursor.execute("PRAGMA table_info(tasks)")
    columns = {row["name"] for row in cursor.fetchall()}

    expected_columns = {
        "name",
        "description",
        "details",
        "priority",
        "status",
        "created_at",
        "started_at",
        "completed_at",
    }
    assert expected_columns.issubset(columns)


def test_db_has_dependencies_table(test_db_connection: sqlite3.Connection):
    """Test that the dependencies table exists."""
    cursor = test_db_connection.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dependencies'"
    )
    result = cursor.fetchone()
    assert result is not None


def test_db_is_isolated_between_tests(test_db_connection: sqlite3.Connection):
    """Test that each test gets a fresh database."""
    cursor = test_db_connection.cursor()

    # Insert a test task
    cursor.execute(
        "INSERT INTO tasks (name, description) VALUES (?, ?)",
        ("test-task", "This is a test task"),
    )
    test_db_connection.commit()

    # Verify it was inserted
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    result = cursor.fetchone()
    assert result["count"] == 1


def test_db_is_isolated_second_test(test_db_connection: sqlite3.Connection):
    """Test that the previous test's data is not present."""
    cursor = test_db_connection.cursor()

    # Database should be empty
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    result = cursor.fetchone()
    assert result["count"] == 0
