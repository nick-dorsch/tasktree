"""
Database operations for TaskTree.
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import List, Optional

from ..io.snapshot import export_snapshot
from .models import DependencyResponse, FeatureResponse, TaskResponse
from .paths import get_db_path, get_snapshot_path
from .validators import validate_specification

DB_PATH = get_db_path()
logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection():
    """Get a connection to the SQLite database with proper cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_tests_required_column(conn)
    try:
        yield conn
    finally:
        conn.close()


def _ensure_tests_required_column(conn: sqlite3.Connection) -> None:
    """Ensure the tasks table has the tests_required column."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    if cursor.fetchone() is None:
        return

    cursor.execute("PRAGMA table_info(tasks)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "tests_required" in columns:
        return

    conn.execute(
        "ALTER TABLE tasks ADD COLUMN tests_required INTEGER NOT NULL DEFAULT 1 "
        "CHECK (tests_required IN (0, 1))"
    )
    conn.commit()


def _trigger_snapshot_export() -> None:
    """Export the JSONL snapshot."""
    try:
        export_snapshot(DB_PATH, get_snapshot_path())
    except Exception as exc:
        logger.warning("Snapshot export failed: %s", exc)


class TaskRepository:
    """Repository class for task operations."""

    @staticmethod
    def list_tasks(
        status: Optional[str] = None,
        priority_min: Optional[int] = None,
        feature_name: Optional[str] = None,
    ) -> List[TaskResponse]:
        """
        List tasks from the database with optional filtering.

        Args:
            status: Filter by status value
            priority_min: Minimum priority level
            feature_name: Filter by feature name

        Returns:
            List of TaskResponse models matching the filters
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = (
                "SELECT t.*, f.name AS feature_name "
                "FROM tasks t "
                "JOIN features f ON t.feature_id = f.id"
            )
            params = []

            if status or priority_min is not None or feature_name:
                conditions = []
                if status:
                    conditions.append("t.status = ?")
                    params.append(status)
                if priority_min is not None:
                    conditions.append("t.priority >= ?")
                    params.append(priority_min)
                if feature_name:
                    conditions.append("f.name = ?")
                    params.append(feature_name)
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY t.priority DESC, t.created_at ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                TaskResponse.from_dict({key: row[key] for key in row.keys()})
                for row in rows
            ]

    @staticmethod
    def get_task(name: str) -> Optional[TaskResponse]:
        """
        Get a specific task by name.

        Args:
            name: Task name to retrieve

        Returns:
            TaskResponse model if found, None otherwise

        Raises:
            ValueError: If task name is empty
        """
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.*, f.name AS feature_name
                FROM tasks t
                JOIN features f ON t.feature_id = f.id
                WHERE t.name = ?
                ORDER BY t.created_at ASC
                LIMIT 1
                """,
                (name,),
            )
            row = cursor.fetchone()
            return (
                TaskResponse.from_dict({key: row[key] for key in row.keys()})
                if row
                else None
            )

    @staticmethod
    def add_task(
        name: str,
        description: str,
        specification: str,
        priority: int = 0,
        status: str = "pending",
        feature_name: str = "misc",
        tests_required: bool = True,
    ) -> TaskResponse:
        """
        Add a new task to the database.

        Args:
            name: Unique task name
            description: Task description
            specification: Detailed task specification
            priority: Priority level (0-10)
            status: Initial status
            feature_name: Feature this task belongs to
            tests_required: Whether tests are required for this task

        Returns:
            TaskResponse model with the created task data

        Raises:
            ValueError: If task name already exists or feature doesn't exist
        """
        validate_specification(specification)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            try:
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
                    SELECT
                        f.id,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?,
                        ?
                    FROM features f
                    WHERE f.name = ?
                    """,
                    (
                        name,
                        description,
                        specification,
                        int(tests_required),
                        priority,
                        status,
                        feature_name,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Feature '{feature_name}' does not exist")
                conn.commit()

                _trigger_snapshot_export()

                cursor.execute(
                    """
                    SELECT t.*, f.name AS feature_name
                    FROM tasks t
                    JOIN features f ON t.feature_id = f.id
                    WHERE t.name = ? AND f.name = ?
                    ORDER BY t.created_at DESC
                    LIMIT 1
                    """,
                    (name, feature_name),
                )
                row = cursor.fetchone()
                if row:
                    return TaskResponse.from_dict({key: row[key] for key in row.keys()})
                # This should never happen, but for type safety
                raise RuntimeError("Failed to retrieve newly created task")

            except sqlite3.IntegrityError as e:
                raise ValueError(f"Task with name '{name}' already exists") from e

    @staticmethod
    def update_task(
        name: str,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        specification: Optional[str] = None,
        tests_required: Optional[bool] = None,
    ) -> Optional[TaskResponse]:
        """Update an existing task."""
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
            if not cursor.fetchone():
                return None

            updates = []
            params = []

            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if priority is not None:
                updates.append("priority = ?")
                params.append(priority)
            if specification is not None:
                updates.append("specification = ?")
                params.append(specification)
            if tests_required is not None:
                updates.append("tests_required = ?")
                params.append(int(tests_required))

            if not updates:
                return TaskRepository.get_task(name)

            query = f"UPDATE tasks SET {', '.join(updates)} WHERE name = ?"
            params.append(name)

            cursor.execute(query, params)
            conn.commit()

            _trigger_snapshot_export()

            return TaskRepository.get_task(name)

    @staticmethod
    def delete_task(name: str) -> bool:
        """
        Delete a task from the database.

        Also deletes all dependencies associated with this task (both incoming
        and outgoing dependencies) to maintain referential integrity.
        """
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty")

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # First delete all dependencies associated with this task
            # This includes both:
            # - Dependencies where this task depends on others (task_id = target id)
            # - Dependencies where other tasks depend on this task (depends_on_task_id = target id)
            cursor.execute(
                """
                WITH target AS (
                    SELECT id FROM tasks WHERE name = ?
                )
                DELETE FROM dependencies
                WHERE task_id IN (SELECT id FROM target)
                   OR depends_on_task_id IN (SELECT id FROM target)
                """,
                (name,),
            )

            # Then delete the task itself
            cursor.execute("DELETE FROM tasks WHERE name = ?", (name,))
            deleted = cursor.rowcount > 0

            conn.commit()
            _trigger_snapshot_export()
            return deleted

    @staticmethod
    def complete_task(name: str) -> Optional[TaskResponse]:
        """Mark a task as completed."""
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty")

        return TaskRepository.update_task(name=name, status="completed")


class FeatureRepository:
    """Repository class for feature operations."""

    @staticmethod
    def add_feature(
        name: str,
        description: str,
        specification: str,
    ) -> FeatureResponse:
        """Add a new feature to the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO features (name, description, specification)
                    VALUES (?, ?, ?)
                    """,
                    (name, description, specification),
                )
                conn.commit()

                _trigger_snapshot_export()

                cursor.execute("SELECT * FROM features WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    return FeatureResponse.from_dict(
                        {key: row[key] for key in row.keys()}
                    )
                # This should never happen, but for type safety
                raise RuntimeError("Failed to retrieve newly created feature")

            except sqlite3.IntegrityError as e:
                raise ValueError(f"Feature with name '{name}' already exists") from e

    @staticmethod
    def list_features() -> List[FeatureResponse]:
        """List features from the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM features ORDER BY name ASC")
            rows = cursor.fetchall()

            return [
                FeatureResponse.from_dict({key: row[key] for key in row.keys()})
                for row in rows
            ]

    @staticmethod
    def get_feature(name: str) -> Optional[FeatureResponse]:
        """
        Get a specific feature by name.

        Args:
            name: Feature name to retrieve

        Returns:
            FeatureResponse model if found, None otherwise
        """
        if not name or not name.strip():
            raise ValueError("Feature name cannot be empty")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM features WHERE name = ?", (name,))
            row = cursor.fetchone()
            return (
                FeatureResponse.from_dict({key: row[key] for key in row.keys()})
                if row
                else None
            )

    @staticmethod
    def delete_feature(name: str) -> bool:
        """
        Delete a feature from the database.

        Args:
            name: Feature name to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete the 'misc' feature
        """
        if name == "misc":
            raise ValueError("The 'misc' feature cannot be deleted")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM features WHERE name = ?", (name,))
            deleted = cursor.rowcount > 0
            conn.commit()
            _trigger_snapshot_export()
            return deleted


class DependencyRepository:
    """Repository class for dependency operations."""

    @staticmethod
    def list_dependencies(task_name: Optional[str] = None) -> List[DependencyResponse]:
        """List task dependencies."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if task_name:
                cursor.execute(
                    """
                    SELECT t.name AS task_name, d.name AS depends_on_task_name
                    FROM dependencies dep
                    JOIN tasks t ON dep.task_id = t.id
                    JOIN tasks d ON dep.depends_on_task_id = d.id
                    WHERE t.name = ? OR d.name = ?
                    ORDER BY t.name, d.name
                    """,
                    (task_name, task_name),
                )
            else:
                cursor.execute(
                    """
                    SELECT t.name AS task_name, d.name AS depends_on_task_name
                    FROM dependencies dep
                    JOIN tasks t ON dep.task_id = t.id
                    JOIN tasks d ON dep.depends_on_task_id = d.id
                    ORDER BY t.name, d.name
                    """
                )

            rows = cursor.fetchall()
            return [
                DependencyResponse.from_dict({key: row[key] for key in row.keys()})
                for row in rows
            ]

    @staticmethod
    def add_dependency(task_name: str, depends_on_task_name: str) -> DependencyResponse:
        """Add a dependency relationship between tasks."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    SELECT name, id
                    FROM tasks
                    WHERE name IN (?, ?)
                    """,
                    (task_name, depends_on_task_name),
                )
                rows = cursor.fetchall()
                task_ids = {row["name"]: row["id"] for row in rows}
                if task_name not in task_ids or depends_on_task_name not in task_ids:
                    raise ValueError("Both tasks must exist to create a dependency")

                cursor.execute(
                    """
                    INSERT INTO dependencies (task_id, depends_on_task_id)
                    VALUES (?, ?)
                    """,
                    (task_ids[task_name], task_ids[depends_on_task_name]),
                )
                conn.commit()

                _trigger_snapshot_export()

                return DependencyResponse(
                    task_name=task_name,
                    depends_on_task_name=depends_on_task_name,
                )

            except sqlite3.IntegrityError as e:
                if "circular" in str(e).lower():
                    raise ValueError("Circular dependencies are not allowed") from e
                raise ValueError("Dependency already exists") from e

    @staticmethod
    def remove_dependency(task_name: str, depends_on_task_name: str) -> bool:
        """Remove a dependency relationship."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM dependencies
                WHERE task_id = (SELECT id FROM tasks WHERE name = ? LIMIT 1)
                  AND depends_on_task_id = (SELECT id FROM tasks WHERE name = ? LIMIT 1)
                """,
                (task_name, depends_on_task_name),
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            _trigger_snapshot_export()
            return deleted

    @staticmethod
    def get_available_tasks() -> List[TaskResponse]:
        """Get pending tasks that can be started (no uncompleted dependencies)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM v_available_tasks
                ORDER BY priority DESC, created_at ASC
                """
            )

            rows = cursor.fetchall()
            return [
                TaskResponse.from_dict({key: row[key] for key in row.keys()})
                for row in rows
            ]
