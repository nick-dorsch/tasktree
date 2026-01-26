"""
Tests for database fixture isolation.
"""

import sqlite3


def test_db_is_isolated_between_tests(test_db_connection: sqlite3.Connection):
    """Test that each test gets a fresh database."""
    cursor = test_db_connection.cursor()

    cursor.execute(
        "INSERT INTO tasks (name, description) VALUES (?, ?)",
        ("test-task", "This is a test task"),
    )
    test_db_connection.commit()

    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    result = cursor.fetchone()
    assert result["count"] == 1


def test_db_is_isolated_second_test(test_db_connection: sqlite3.Connection):
    """Test that the previous test's data is not present."""
    cursor = test_db_connection.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    result = cursor.fetchone()
    assert result["count"] == 0
