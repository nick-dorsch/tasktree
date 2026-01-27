"""
JSONL snapshot export/import utilities for TaskTree.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from ..db.init import initialize_database

SNAPSHOT_SCHEMA_VERSION = "1"
RECORD_ORDER: Tuple[str, ...] = ("meta", "feature", "task", "dependency")


def export_snapshot(db_path: Path, snapshot_path: Path) -> None:
    """
    Export the TaskTree database to a deterministic JSONL snapshot.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot_path.exists():
        snapshot_path.touch()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        with snapshot_path.open("w", encoding="utf-8", newline="\n") as handle:
            _write_snapshot_from_view(conn, handle)
    finally:
        conn.close()


def import_snapshot(db_path: Path, snapshot_path: Path, overwrite: bool = True) -> None:
    """
    Import a JSONL snapshot into a TaskTree database.

    Args:
        db_path: Path to the SQLite database to create or update
        snapshot_path: Path to the JSONL snapshot to import
        overwrite: If True, recreate the database before import

    Raises:
        FileNotFoundError: If the snapshot file does not exist
        ValueError: If snapshot records are invalid
        sqlite3.Error: If database operations fail
    """
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

    meta_record, features, tasks, dependencies = _parse_snapshot(snapshot_path)
    _validate_meta(meta_record)

    if overwrite and db_path.exists():
        db_path.unlink()

    if overwrite or not db_path.exists():
        initialize_database(db_path, apply_views_flag=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        with conn:
            if overwrite:
                _clear_database(conn)

            _insert_features(conn, features)
            _insert_tasks(conn, tasks)
            _insert_dependencies(conn, dependencies)
    finally:
        conn.close()


def _write_snapshot_from_view(conn: sqlite3.Connection, handle) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT json_line
        FROM v_snapshot_jsonl_lines
        ORDER BY record_order, sort_name, sort_secondary
        """
    )
    for row in cursor:
        json_line = row["json_line"]
        handle.write(f"{json_line}\n")


def _parse_snapshot(
    snapshot_path: Path,
) -> Tuple[
    Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]
]:
    meta_record: Dict[str, Any] | None = None
    features: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []
    dependencies: List[Dict[str, Any]] = []

    current_index = -1

    with snapshot_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Snapshot record on line {line_number} must be an object"
                )

            record_type = record.get("record_type")
            if not isinstance(record_type, str) or not record_type:
                raise ValueError(
                    f"Field 'record_type' must be a non-empty string on line {line_number}"
                )
            if record_type not in RECORD_ORDER:
                raise ValueError(
                    f"Invalid record_type '{record_type}' on line {line_number}"
                )

            index = RECORD_ORDER.index(record_type)
            if index < current_index:
                raise ValueError(
                    f"Record ordering violation on line {line_number}: {record_type}"
                )
            if record_type != "meta" and meta_record is None:
                raise ValueError("Snapshot must start with a meta record")
            if record_type == "meta":
                if meta_record is not None:
                    raise ValueError("Snapshot must contain only one meta record")
                meta_record = record
            elif record_type == "feature":
                features.append(record)
            elif record_type == "task":
                tasks.append(record)
            elif record_type == "dependency":
                dependencies.append(record)

            current_index = max(current_index, index)

    if meta_record is None:
        raise ValueError("Snapshot must include a meta record")

    return meta_record, features, tasks, dependencies


def _validate_meta(meta_record: Dict[str, Any]) -> None:
    schema_version = meta_record.get("schema_version")
    if schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported snapshot schema version: {schema_version}")
    generated_at = meta_record.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at:
        raise ValueError("Meta record must include generated_at")


def _clear_database(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dependencies")
    cursor.execute("DELETE FROM tasks")
    cursor.execute("DELETE FROM features")


def _insert_features(
    conn: sqlite3.Connection, features: Sequence[Dict[str, Any]]
) -> None:
    if not features:
        return
    rows = []
    for record in features:
        updated_at = record.get("updated_at")
        if updated_at is None:
            updated_at = record["created_at"]
        rows.append(
            (
                record["name"],
                record.get("description"),
                record.get("specification"),
                record["created_at"],
                updated_at,
            )
        )

    conn.executemany(
        """
        INSERT INTO features (name, description, specification, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_tasks(conn: sqlite3.Connection, tasks: Sequence[Dict[str, Any]]) -> None:
    if not tasks:
        return
    rows = []
    for record in tasks:
        tests_required = record.get("tests_required", True)
        rows.append(
            (
                record["name"],
                record["description"],
                record.get("specification"),
                int(bool(tests_required)),
                record["priority"],
                record["status"],
                record["created_at"],
                record["updated_at"],
                record.get("started_at"),
                record.get("completed_at"),
                record["feature_name"],
            )
        )

    conn.executemany(
        """
        INSERT INTO tasks (
            feature_id,
            name,
            description,
            specification,
            tests_required,
            priority,
            status,
            created_at,
            updated_at,
            started_at,
            completed_at
        )
        SELECT
            f.id,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        FROM features f
        WHERE f.name = ?
        """,
        rows,
    )


def _insert_dependencies(
    conn: sqlite3.Connection, dependencies: Sequence[Dict[str, Any]]
) -> None:
    if not dependencies:
        return
    rows = []
    for record in dependencies:
        rows.append((record["task_name"], record["depends_on_task_name"]))

    conn.executemany(
        """
        INSERT INTO dependencies (task_id, depends_on_task_id)
        SELECT t.id, d.id
        FROM tasks t, tasks d
        WHERE t.name = ? AND d.name = ?
        """,
        rows,
    )
