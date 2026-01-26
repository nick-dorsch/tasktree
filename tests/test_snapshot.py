"""
Tests for snapshot export/import.
"""

import json
import sqlite3
from pathlib import Path

from tasktree_mcp.snapshot import export_snapshot, import_snapshot


def _load_snapshot_records(snapshot_path: Path) -> list[dict]:
    lines = snapshot_path.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines:
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def test_export_snapshot_writes_ordered_jsonl(test_db: Path, tmp_path: Path) -> None:
    """Export produces deterministic JSONL ordering and serialization."""
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO features (name, description, enabled) VALUES (?, ?, ?)",
            ("analytics", "Analytics feature", True),
        )
        cursor.execute(
            """
            INSERT INTO tasks (name, description, feature_name, priority, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("alpha", "Alpha task", "default", 3, "pending"),
        )
        cursor.execute(
            """
            INSERT INTO tasks (name, description, feature_name, priority, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("beta", "Beta task", "analytics", 2, "pending"),
        )
        cursor.execute(
            "INSERT INTO dependencies (task_name, depends_on_task_name) VALUES (?, ?)",
            ("beta", "alpha"),
        )
        conn.commit()
    finally:
        conn.close()

    snapshot_path = tmp_path / "snapshot.jsonl"
    export_snapshot(test_db, snapshot_path)

    raw_lines = snapshot_path.read_text(encoding="utf-8").splitlines()
    records = _load_snapshot_records(snapshot_path)

    assert records[0]["record_type"] == "meta"

    feature_names = [r["name"] for r in records if r["record_type"] == "feature"]
    assert feature_names == sorted(feature_names)

    task_names = [r["name"] for r in records if r["record_type"] == "task"]
    assert task_names == sorted(task_names)

    dependency_pairs = [
        (r["task_name"], r["depends_on_task_name"])
        for r in records
        if r["record_type"] == "dependency"
    ]
    assert dependency_pairs == sorted(dependency_pairs)

    for line in raw_lines:
        if not line.strip():
            continue
        record = json.loads(line)
        expected = json.dumps(
            record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        assert line == expected


def test_import_snapshot_overwrite_restores_data(test_db: Path, tmp_path: Path) -> None:
    """Import recreates a database and restores snapshot data."""
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO features (name, description, enabled) VALUES (?, ?, ?)",
            ("analytics", "Analytics feature", True),
        )
        cursor.execute(
            """
            INSERT INTO tasks (name, description, feature_name, priority, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("alpha", "Alpha task", "default", 3, "pending"),
        )
        cursor.execute(
            """
            INSERT INTO tasks (name, description, feature_name, priority, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("beta", "Beta task", "analytics", 2, "pending"),
        )
        cursor.execute(
            "INSERT INTO dependencies (task_name, depends_on_task_name) VALUES (?, ?)",
            ("beta", "alpha"),
        )
        conn.commit()
    finally:
        conn.close()

    snapshot_path = tmp_path / "snapshot.jsonl"
    export_snapshot(test_db, snapshot_path)

    new_db_path = tmp_path / "imported.db"
    import_snapshot(new_db_path, snapshot_path, overwrite=True)

    snapshot_records = _load_snapshot_records(snapshot_path)
    feature_records = {
        r["name"]: r for r in snapshot_records if r["record_type"] == "feature"
    }
    task_records = {
        r["name"]: r for r in snapshot_records if r["record_type"] == "task"
    }
    dependency_records = [
        (r["task_name"], r["depends_on_task_name"])
        for r in snapshot_records
        if r["record_type"] == "dependency"
    ]

    conn = sqlite3.connect(new_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name, description, enabled, created_at, updated_at FROM features"
        )
        for row in cursor.fetchall():
            record = feature_records[row["name"]]
            assert row["description"] == record["description"]
            assert bool(row["enabled"]) == bool(record["enabled"])
            assert row["created_at"] == record["created_at"]
            assert row["updated_at"] == record["updated_at"]

        cursor.execute(
            """
            SELECT
                name,
                description,
                details,
                feature_name,
                priority,
                status,
                created_at,
                updated_at,
                started_at,
                completed_at
            FROM tasks
            """
        )
        for row in cursor.fetchall():
            record = task_records[row["name"]]
            assert row["description"] == record["description"]
            assert row["details"] == record["details"]
            assert row["feature_name"] == record["feature_name"]
            assert row["priority"] == record["priority"]
            assert row["status"] == record["status"]
            assert row["created_at"] == record["created_at"]
            assert row["updated_at"] == record["updated_at"]
            assert row["started_at"] == record["started_at"]
            assert row["completed_at"] == record["completed_at"]

        cursor.execute(
            """
            SELECT task_name, depends_on_task_name
            FROM dependencies
            ORDER BY task_name, depends_on_task_name
            """
        )
        dependencies = [
            (row["task_name"], row["depends_on_task_name"]) for row in cursor.fetchall()
        ]
        assert dependencies == sorted(dependency_records)

        cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = {row[0] for row in cursor.fetchall()}
        assert "v_available_tasks" in views
    finally:
        conn.close()
