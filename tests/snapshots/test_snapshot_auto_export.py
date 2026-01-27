"""
Tests for automatic snapshot export after write operations.
"""

import sqlite3
from pathlib import Path

import pytest

from tasktree.core.database import (
    DependencyRepository,
    FeatureRepository,
    TaskRepository,
)


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


def _read_snapshot_lines(snapshot_path: Path) -> list[str]:
    if not snapshot_path.exists():
        return []
    return [
        line for line in snapshot_path.read_text(encoding="utf-8").splitlines() if line
    ]


def _assert_snapshot_matches(db_path: Path, snapshot_path: Path) -> None:
    assert snapshot_path.exists()
    assert _read_snapshot_lines(snapshot_path) == _fetch_snapshot_view_lines(db_path)


@pytest.fixture
def snapshot_env(test_db: Path, tmp_path: Path, monkeypatch) -> Path:
    import tasktree.core.database as db_module

    snapshot_path = tmp_path / "snapshot.jsonl"
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    monkeypatch.setenv("TASKTREE_SNAPSHOT_PATH", str(snapshot_path))
    return snapshot_path


def test_auto_export_after_task_writes(snapshot_env: Path, test_db: Path) -> None:
    TaskRepository.add_task(
        name="auto-task",
        description="Auto export task",
        specification="Auto export task spec",
    )
    _assert_snapshot_matches(test_db, snapshot_env)

    TaskRepository.update_task(
        name="auto-task",
        description="Updated description",
    )
    _assert_snapshot_matches(test_db, snapshot_env)

    TaskRepository.delete_task("auto-task")
    _assert_snapshot_matches(test_db, snapshot_env)


def test_auto_export_after_dependency_writes(snapshot_env: Path, test_db: Path) -> None:
    TaskRepository.add_task("dependency-a", "Dep A", "Spec A")
    TaskRepository.add_task("dependency-b", "Dep B", "Spec B")

    DependencyRepository.add_dependency("dependency-b", "dependency-a")
    _assert_snapshot_matches(test_db, snapshot_env)

    DependencyRepository.remove_dependency("dependency-b", "dependency-a")
    _assert_snapshot_matches(test_db, snapshot_env)


def test_auto_export_after_feature_write(snapshot_env: Path, test_db: Path) -> None:
    FeatureRepository.add_feature(
        name="insights",
        description="Insights feature",
        specification="Insights spec",
    )
    _assert_snapshot_matches(test_db, snapshot_env)


def test_auto_export_failure_does_not_break_write(
    snapshot_env: Path, monkeypatch
) -> None:
    import tasktree.core.database as db_module

    def _raise_export(*_args, **_kwargs) -> None:
        raise RuntimeError("export failed")

    monkeypatch.setattr(db_module, "export_snapshot", _raise_export)

    task = TaskRepository.add_task(
        name="error-task",
        description="Should still add",
        specification="Spec",
    )

    assert task.name == "error-task"
