"""
Tests for SQL snapshot JSONL view.
"""

import json
import re
import sqlite3
from pathlib import Path


def _fetch_snapshot_lines(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT record_order, sort_name, sort_secondary, json_line
        FROM v_snapshot_jsonl_lines
        ORDER BY record_order, sort_name, sort_secondary
        """
    )
    return cursor.fetchall()


def test_snapshot_jsonl_view_ordering_and_format(test_db: Path) -> None:
    """View emits deterministic JSONL with ordering and booleans."""
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO features (name, description, specification)
            VALUES (?, ?, ?)
            """,
            ("alpha-feature", "Alpha feature", "Alpha specification"),
        )
        cursor.execute(
            """
            INSERT INTO features (name, description, specification)
            VALUES (?, ?, ?)
            """,
            ("beta-feature", "Beta feature", "Beta specification"),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id, name, description, specification, tests_required, priority, status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "task-b",
                "Task B",
                "Task B",
                0,
                1,
                "pending",
                "alpha-feature",
            ),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id, name, description, specification, tests_required, priority, status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "task-a",
                "Task A",
                "Task A",
                1,
                2,
                "pending",
                "alpha-feature",
            ),
        )
        cursor.execute(
            """
            INSERT INTO tasks (
                feature_id, name, description, specification, tests_required, priority, status
            )
            SELECT id, ?, ?, ?, ?, ?, ?
            FROM features
            WHERE name = ?
            """,
            (
                "task-c",
                "Task C",
                "Task C",
                1,
                3,
                "pending",
                "beta-feature",
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
            ("task-a", "task-b"),
        )
        cursor.execute(
            """
            INSERT INTO dependencies (task_id, depends_on_task_id)
            SELECT t.id, d.id
            FROM tasks t
            JOIN tasks d ON d.name = ?
            WHERE t.name = ?
            """,
            ("task-c", "task-b"),
        )
        cursor.execute(
            """
            INSERT INTO dependencies (task_id, depends_on_task_id)
            SELECT t.id, d.id
            FROM tasks t
            JOIN tasks d ON d.name = ?
            WHERE t.name = ?
            """,
            ("task-a", "task-c"),
        )
        conn.commit()

        rows = _fetch_snapshot_lines(conn)
    finally:
        conn.close()

    records = [json.loads(row["json_line"]) for row in rows]
    record_types = [record["record_type"] for record in records]
    assert record_types[0] == "meta"
    assert all(rt == "feature" for rt in record_types[1:4])
    assert all(rt == "task" for rt in record_types[4:7])
    assert all(rt == "dependency" for rt in record_types[7:])

    feature_names = [
        record["name"] for record in records if record["record_type"] == "feature"
    ]
    assert feature_names == sorted(feature_names)

    task_names = [
        record["name"] for record in records if record["record_type"] == "task"
    ]
    assert task_names == sorted(task_names)

    dependency_pairs = [
        (record["task_name"], record["depends_on_task_name"])
        for record in records
        if record["record_type"] == "dependency"
    ]
    assert dependency_pairs == sorted(dependency_pairs)

    meta_line = rows[0]["json_line"]
    assert re.match(
        r'^\{"record_type":"meta","schema_version":"1","generated_at":"[^"]+","source":"sqlite"\}$',
        meta_line,
    )

    feature_line = next(
        row["json_line"]
        for row in rows
        if '"record_type":"feature"' in row["json_line"]
        and '"name":"alpha-feature"' in row["json_line"]
    )
    assert '"specification":"Alpha specification"' in feature_line
    assert feature_line.index('"record_type"') < feature_line.index('"name"')
    assert feature_line.index('"name"') < feature_line.index('"description"')
    assert feature_line.index('"description"') < feature_line.index('"specification"')
    assert feature_line.index('"specification"') < feature_line.index('"created_at"')
    assert feature_line.index('"created_at"') < feature_line.index('"updated_at"')

    task_line = next(
        row["json_line"]
        for row in rows
        if '"record_type":"task"' in row["json_line"]
        and '"name":"task-b"' in row["json_line"]
    )
    assert '"tests_required":false' in task_line
    assert task_line.index('"record_type"') < task_line.index('"name"')
    assert task_line.index('"name"') < task_line.index('"description"')
    assert task_line.index('"description"') < task_line.index('"specification"')
    assert task_line.index('"specification"') < task_line.index('"feature_name"')
    assert task_line.index('"feature_name"') < task_line.index('"tests_required"')
    assert task_line.index('"tests_required"') < task_line.index('"priority"')
    assert task_line.index('"priority"') < task_line.index('"status"')
    assert task_line.index('"status"') < task_line.index('"created_at"')
    assert task_line.index('"created_at"') < task_line.index('"updated_at"')
    assert task_line.index('"updated_at"') < task_line.index('"started_at"')
    assert task_line.index('"started_at"') < task_line.index('"completed_at"')

    dependency_line = next(
        row["json_line"]
        for row in rows
        if '"record_type":"dependency"' in row["json_line"]
    )
    assert dependency_line.index('"record_type"') < dependency_line.index('"task_name"')
    assert dependency_line.index('"task_name"') < dependency_line.index(
        '"depends_on_task_name"'
    )
