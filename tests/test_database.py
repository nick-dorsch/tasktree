"""
Tests for database operations using the test_db fixture.
"""

from pathlib import Path

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
        "tests_required",
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


def test_inline_migration_adds_tests_required_column(tmp_path: Path, monkeypatch):
    """Test inline migration adds tests_required to existing tasks table."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS features (
              name VARCHAR(55) PRIMARY KEY,
              description TEXT,
              enabled BOOLEAN DEFAULT TRUE,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            INSERT OR IGNORE INTO features (name, description, enabled) VALUES
            ('default', 'Default feature set for basic task management', TRUE);

            CREATE TABLE IF NOT EXISTS tasks (
              name VARCHAR(55) PRIMARY KEY,
              description TEXT NOT NULL,
              details TEXT,
              feature_name VARCHAR(55) NOT NULL DEFAULT 'default',
              priority INTEGER DEFAULT 0 CHECK(priority >= 0 AND priority <= 10),
              status TEXT DEFAULT 'pending' CHECK(
                status IN (
                  'pending',
                  'in_progress',
                  'completed',
                  'blocked'
                )
              ),
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              started_at TIMESTAMP,
              completed_at TIMESTAMP,
              FOREIGN KEY (feature_name) REFERENCES features(name)
            );
            """
        )
        conn.execute(
            "INSERT INTO tasks (name, description, feature_name, priority, status) "
            "VALUES (?, ?, ?, ?, ?)",
            ("legacy-task", "Legacy task", "default", 0, "pending"),
        )
        conn.commit()
    finally:
        conn.close()

    import tasktree_mcp.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    tasks = db_module.TaskRepository.list_tasks()

    assert tasks[0].tests_required is True

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        columns = {row["name"] for row in cursor.fetchall()}
        assert "tests_required" in columns
    finally:
        conn.close()
