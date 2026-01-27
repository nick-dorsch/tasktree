"""
Tests for snapshot export/import.
"""

import json
import sqlite3
from pathlib import Path

from tasktree_mcp import snapshot as snapshot_module
from tasktree_mcp.snapshot import export_snapshot, import_snapshot


def _load_snapshot_records(snapshot_path: Path) -> list[dict]:
    lines = snapshot_path.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines:
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _fetch_snapshot_view_lines(db_path: Path) -> list[str]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT json_line
            FROM v_snapshot_jsonl_lines
            ORDER BY record_order, sort_name, sort_secondary
            """
        )
        return [row["json_line"] for row in cursor.fetchall()]
    finally:
        conn.close()


def test_export_snapshot_writes_ordered_jsonl(test_db: Path, tmp_path: Path) -> None:
    """Export produces deterministic JSONL ordering and serialization."""
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO features (name, description, specification)
            VALUES (?, ?, ?)
            """,
            (
                "analytics",
                "Analytics feature",
                "Analytics feature specification",
            ),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id,
                name,
                description,
                specification,
                tests_required,
                priority,
                status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "alpha",
                "Alpha task",
                "Alpha task",
                1,
                3,
                "pending",
                "misc",
            ),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id,
                name,
                description,
                specification,
                tests_required,
                priority,
                status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "beta",
                "Beta task",
                "Beta task",
                1,
                2,
                "pending",
                "analytics",
            ),
        )
        cursor.execute(
            """
            INSERT INTO dependencies (task_id, depends_on_task_id)
            SELECT t.id, d.id
            FROM tasks t
            JOIN tasks d ON d.name = ?
            WHERE t.name = ?
            """,
            ("alpha", "beta"),
        )
        conn.commit()
    finally:
        conn.close()

    snapshot_path = tmp_path / "snapshot.jsonl"
    export_snapshot(test_db, snapshot_path)

    raw_lines = [
        line for line in snapshot_path.read_text(encoding="utf-8").splitlines() if line
    ]
    expected_lines = _fetch_snapshot_view_lines(test_db)
    records = _load_snapshot_records(snapshot_path)

    assert raw_lines == expected_lines
    assert records[0]["record_type"] == "meta"

    feature_names = [r["name"] for r in records if r["record_type"] == "feature"]
    assert feature_names == sorted(feature_names)

    task_names = [r["name"] for r in records if r["record_type"] == "task"]
    assert task_names == sorted(task_names)

    task_records = [r for r in records if r["record_type"] == "task"]
    assert all("tests_required" in record for record in task_records)
    assert all(record["tests_required"] is True for record in task_records)

    dependency_pairs = [
        (r["task_name"], r["depends_on_task_name"])
        for r in records
        if r["record_type"] == "dependency"
    ]
    assert dependency_pairs == sorted(dependency_pairs)


def test_export_snapshot_falls_back_without_json1(
    test_db: Path, tmp_path: Path, monkeypatch
) -> None:
    """Export falls back to Python serialization when JSON1 is unavailable."""
    conn = sqlite3.connect(test_db)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO features (name, description, specification)
            VALUES (?, ?, ?)
            """,
            ("gamma", "Gamma feature", "Gamma feature specification"),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id,
                name,
                description,
                specification,
                tests_required,
                priority,
                status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "delta",
                "Delta task",
                "Delta task",
                1,
                4,
                "pending",
                "gamma",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    snapshot_path = tmp_path / "snapshot.jsonl"
    monkeypatch.setattr(snapshot_module, "_json1_available", lambda _: False)
    export_snapshot(test_db, snapshot_path)

    raw_lines = snapshot_path.read_text(encoding="utf-8").splitlines()
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
            """
            INSERT INTO features (name, description, specification)
            VALUES (?, ?, ?)
            """,
            (
                "analytics",
                "Analytics feature",
                "Analytics feature specification",
            ),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id,
                name,
                description,
                specification,
                tests_required,
                priority,
                status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "alpha",
                "Alpha task",
                "Alpha task",
                1,
                3,
                "pending",
                "misc",
            ),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id,
                name,
                description,
                specification,
                tests_required,
                priority,
                status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "beta",
                "Beta task",
                "Beta task",
                1,
                2,
                "pending",
                "analytics",
            ),
        )
        cursor.execute(
            """
            INSERT INTO dependencies (task_id, depends_on_task_id)
            SELECT t.id, d.id
            FROM tasks t
            JOIN tasks d ON d.name = ?
            WHERE t.name = ?
            """,
            ("alpha", "beta"),
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
            """
            SELECT name, description, specification, created_at, updated_at
            FROM features
            """
        )
        for row in cursor.fetchall():
            record = feature_records[row["name"]]
            assert row["description"] == record["description"]
            assert row["specification"] == record["specification"]
            assert row["created_at"] == record["created_at"]
            assert row["updated_at"] == record["updated_at"]

        cursor.execute(
            """
            SELECT
                t.name,
                t.description,
                t.specification,
                f.name AS feature_name,
                t.tests_required,
                t.priority,
                t.status,
                t.created_at,
                t.updated_at,
                t.started_at,
                t.completed_at
            FROM tasks t
            LEFT JOIN features f ON t.feature_id = f.id
            """
        )
        for row in cursor.fetchall():
            record = task_records[row["name"]]
            assert row["description"] == record["description"]
            assert row["specification"] == record["specification"]
            assert row["feature_name"] == record["feature_name"]
            assert bool(row["tests_required"]) == bool(
                record.get("tests_required", True)
            )
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
