"""
JSONL snapshot export/import utilities for TaskTree.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .db_init import initialize_database

SNAPSHOT_SCHEMA_VERSION = "1"
RECORD_ORDER: Tuple[str, ...] = ("meta", "feature", "task", "dependency")


def export_snapshot(db_path: Path, snapshot_path: Path) -> None:
    """
    Export the TaskTree database to a deterministic JSONL snapshot.

    Args:
        db_path: Path to the SQLite database
        snapshot_path: Path to write the JSONL snapshot

    Raises:
        FileNotFoundError: If the database does not exist
        sqlite3.Error: If database access fails
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        generated_at = _get_current_timestamp(conn)
        meta_record = {
            "record_type": "meta",
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "generated_at": generated_at,
            "source": "sqlite",
        }

        features = _fetch_features(conn)
        tasks = _fetch_tasks(conn)
        dependencies = _fetch_dependencies(conn)

        with snapshot_path.open("w", encoding="utf-8", newline="\n") as handle:
            _write_record(handle, meta_record)
            for record in features:
                _write_record(handle, record)
            for record in tasks:
                _write_record(handle, record)
            for record in dependencies:
                _write_record(handle, record)
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


def _get_current_timestamp(conn: sqlite3.Connection) -> str:
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_TIMESTAMP")
    row = cursor.fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("Failed to retrieve current timestamp")
    return str(row[0])


def _write_record(handle, record: Dict[str, Any]) -> None:
    line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    handle.write(f"{line}\n")


def _fetch_features(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, description, enabled, created_at, updated_at
        FROM features
        ORDER BY name ASC
        """
    )
    rows = cursor.fetchall()
    records: List[Dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "record_type": "feature",
                "name": row["name"],
                "description": row["description"],
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return records


def _fetch_tasks(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
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
        ORDER BY name ASC
        """
    )
    rows = cursor.fetchall()
    records: List[Dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "record_type": "task",
                "name": row["name"],
                "description": row["description"],
                "details": row["details"],
                "feature_name": row["feature_name"],
                "priority": row["priority"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
            }
        )
    return records


def _fetch_dependencies(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT task_name, depends_on_task_name
        FROM dependencies
        ORDER BY task_name ASC, depends_on_task_name ASC
        """
    )
    rows = cursor.fetchall()
    records: List[Dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "record_type": "dependency",
                "task_name": row["task_name"],
                "depends_on_task_name": row["depends_on_task_name"],
            }
        )
    return records


def _parse_snapshot(
    snapshot_path: Path,
) -> Tuple[
    Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]
]:
    meta_record: Optional[Dict[str, Any]] = None
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

            record_type = _require_str_field(record, "record_type", line_number)
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
                _validate_feature(record, line_number)
                features.append(record)
            elif record_type == "task":
                _validate_task(record, line_number)
                tasks.append(record)
            elif record_type == "dependency":
                _validate_dependency(record, line_number)
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


def _validate_feature(record: Dict[str, Any], line_number: int) -> None:
    _require_str_field(record, "name", line_number)
    _require_nullable_str_field(record, "description", line_number)
    _require_bool_field(record, "enabled", line_number)
    _require_str_field(record, "created_at", line_number)
    _require_nullable_str_field(record, "updated_at", line_number)


def _validate_task(record: Dict[str, Any], line_number: int) -> None:
    _require_str_field(record, "name", line_number)
    _require_str_field(record, "description", line_number)
    _require_nullable_str_field(record, "details", line_number)
    _require_str_field(record, "feature_name", line_number)
    _require_int_field(record, "priority", line_number)
    _require_str_field(record, "status", line_number)
    _require_str_field(record, "created_at", line_number)
    _require_str_field(record, "updated_at", line_number)
    _require_nullable_str_field(record, "started_at", line_number)
    _require_nullable_str_field(record, "completed_at", line_number)


def _validate_dependency(record: Dict[str, Any], line_number: int) -> None:
    _require_str_field(record, "task_name", line_number)
    _require_str_field(record, "depends_on_task_name", line_number)


def _require_str_field(record: Dict[str, Any], field: str, line_number: int) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"Field '{field}' must be a non-empty string on line {line_number}"
        )
    return value


def _require_nullable_str_field(
    record: Dict[str, Any], field: str, line_number: int
) -> Optional[str]:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(
            f"Field '{field}' must be a string or null on line {line_number}"
        )
    return value


def _require_int_field(record: Dict[str, Any], field: str, line_number: int) -> int:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Field '{field}' must be an integer on line {line_number}")
    return value


def _require_bool_field(record: Dict[str, Any], field: str, line_number: int) -> bool:
    value = record.get(field)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ValueError(f"Field '{field}' must be a boolean on line {line_number}")


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
                bool(record.get("enabled")),
                record["created_at"],
                updated_at,
            )
        )
    conn.executemany(
        """
        INSERT INTO features (name, description, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_tasks(conn: sqlite3.Connection, tasks: Sequence[Dict[str, Any]]) -> None:
    if not tasks:
        return
    rows = []
    for record in tasks:
        rows.append(
            (
                record["name"],
                record["description"],
                record.get("details"),
                record["feature_name"],
                record["priority"],
                record["status"],
                record["created_at"],
                record["updated_at"],
                record.get("started_at"),
                record.get("completed_at"),
            )
        )
    conn.executemany(
        """
        INSERT INTO tasks (
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
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        INSERT INTO dependencies (task_name, depends_on_task_name)
        VALUES (?, ?)
        """,
        rows,
    )
