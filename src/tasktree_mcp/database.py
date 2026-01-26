"""
Database operations for TaskTree.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "tasktree.db"


@contextmanager
def get_db_connection():
    """Get a connection to the SQLite database with proper cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class TaskRepository:
    """Repository class for task operations."""

    @staticmethod
    def list_tasks(
        status: Optional[str] = None, priority_min: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List tasks from the database with optional filtering."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM tasks"
            params = []

            if status or priority_min is not None:
                conditions = []
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                if priority_min is not None:
                    conditions.append("priority >= ?")
                    params.append(priority_min)
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY priority DESC, created_at ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [{key: row[key] for key in row.keys()} for row in rows]

    @staticmethod
    def get_task(name: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by name."""
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
            row = cursor.fetchone()
            return {key: row[key] for key in row.keys()} if row else None

    @staticmethod
    def add_task(
        name: str,
        description: str,
        priority: int = 0,
        status: str = "pending",
        details: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a new task to the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO tasks (name, description, details, priority, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (name, description, details, priority, status),
                )
                conn.commit()

                cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    return {key: row[key] for key in row.keys()}
                return {}

            except sqlite3.IntegrityError as e:
                raise ValueError(f"Task with name '{name}' already exists") from e

    @staticmethod
    def update_task(
        name: str,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        details: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
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
            if details is not None:
                updates.append("details = ?")
                params.append(details)

            if not updates:
                return TaskRepository.get_task(name)

            query = f"UPDATE tasks SET {', '.join(updates)} WHERE name = ?"
            params.append(name)

            cursor.execute(query, params)
            conn.commit()

            return TaskRepository.get_task(name)

    @staticmethod
    def delete_task(name: str) -> bool:
        """Delete a task from the database."""
        if not name or not name.strip():
            raise ValueError("Task name cannot be empty")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE name = ?", (name,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted


class DependencyRepository:
    """Repository class for dependency operations."""

    @staticmethod
    def list_dependencies(task_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List task dependencies."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if task_name:
                cursor.execute(
                    """
                    SELECT task_name, depends_on_task_name
                    FROM dependencies
                    WHERE task_name = ? OR depends_on_task_name = ?
                    ORDER BY task_name, depends_on_task_name
                    """,
                    (task_name, task_name),
                )
            else:
                cursor.execute(
                    """
                    SELECT task_name, depends_on_task_name
                    FROM dependencies
                    ORDER BY task_name, depends_on_task_name
                    """
                )

            rows = cursor.fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]

    @staticmethod
    def add_dependency(task_name: str, depends_on_task_name: str) -> Dict[str, Any]:
        """Add a dependency relationship between tasks."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT name FROM tasks WHERE name IN (?, ?)",
                    (task_name, depends_on_task_name),
                )
                if len(cursor.fetchall()) != 2:
                    raise ValueError("Both tasks must exist to create a dependency")

                cursor.execute(
                    "INSERT INTO dependencies (task_name, depends_on_task_name) VALUES (?, ?)",
                    (task_name, depends_on_task_name),
                )
                conn.commit()

                return {
                    "task_name": task_name,
                    "depends_on_task_name": depends_on_task_name,
                }

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
                "DELETE FROM dependencies WHERE task_name = ? AND depends_on_task_name = ?",
                (task_name, depends_on_task_name),
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    @staticmethod
    def get_available_tasks() -> List[Dict[str, Any]]:
        """Get tasks that can be started (no uncompleted dependencies)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT t.* FROM tasks t
                WHERE t.status != 'completed'
                AND NOT EXISTS (
                    SELECT 1 FROM dependencies d
                    WHERE d.task_name = t.name
                    AND EXISTS (
                        SELECT 1 FROM tasks t2
                        WHERE t2.name = d.depends_on_task_name
                        AND t2.status != 'completed'
                    )
                )
                ORDER BY t.priority DESC, t.created_at ASC
                """
            )

            rows = cursor.fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]
