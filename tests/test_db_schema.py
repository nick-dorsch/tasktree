"""
Tests for database schema basics.
"""

import sqlite3


def test_db_has_tasks_table(test_db_connection: sqlite3.Connection):
    """Test that the tasks table exists and has the correct schema."""
    cursor = test_db_connection.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    result = cursor.fetchone()
    assert result is not None

    cursor.execute("PRAGMA table_info(tasks)")
    columns = {row["name"] for row in cursor.fetchall()}

    expected_columns = {
        "id",
        "feature_id",
        "name",
        "description",
        "specification",
        "tests_required",
        "priority",
        "status",
        "created_at",
        "updated_at",
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
