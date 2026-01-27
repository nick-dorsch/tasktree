"""
Tests for database inline migrations.
"""

from pathlib import Path

import sqlite3


def test_inline_migration_adds_tests_required_column(tmp_path: Path, monkeypatch):
    """Test inline migration adds tests_required to existing tasks table."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS features (
              id CHAR(32) PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
              name VARCHAR(55) NOT NULL UNIQUE,
              description TEXT NOT NULL,
              specification TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            INSERT OR IGNORE INTO features (name, description, specification) VALUES
            (
              'misc',
              'Default feature for uncategorized tasks',
              'Use this feature in cases where a task is minimal and does not require a feature, such as minor hotfixes, tweaks etc.'
            );

            CREATE TABLE IF NOT EXISTS tasks (
              id CHAR(32) PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
              feature_id CHAR(32) REFERENCES features(id),
              name VARCHAR(55) NOT NULL,
              description TEXT NOT NULL,
              specification TEXT NOT NULL,
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
              UNIQUE(name, feature_id)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO tasks (feature_id, name, description, specification, priority, status)
            SELECT id, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "legacy-task",
                "Legacy task",
                "Legacy task",
                0,
                "pending",
                "misc",
            ),
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
