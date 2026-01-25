#!/usr/bin/env python3
"""
TaskTree MCP Server
A Model Context Protocol server that provides tools for querying and managing tasks
in the TaskTree SQLite database.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("tasktree")

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "tasktree.db"


class TaskStatus(str, Enum):
    """Valid task status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Task(BaseModel):
    """Task model with validation."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    priority: int = Field(default=0, ge=0, le=10)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> TaskStatus:
        """Validate status is one of the allowed values."""
        if isinstance(v, TaskStatus):
            return v
        if isinstance(v, str):
            v = v.lower()
            for status in TaskStatus:
                if status.value == v:
                    return status
            raise ValueError(
                f"Status must be one of: {', '.join([s.value for s in TaskStatus])}"
            )
        raise ValueError(f"Invalid status type: {type(v)}")


class Dependency(BaseModel):
    """Dependency relationship model."""

    task_name: str = Field(..., min_length=1, max_length=255)
    depends_on_task_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("depends_on_task_name")
    @classmethod
    def validate_no_self_dependency(cls, v: str, info) -> str:
        """Ensure a task doesn't depend on itself."""
        if "task_name" in info.data and v == info.data["task_name"]:
            raise ValueError("A task cannot depend on itself")
        return v


@contextmanager
def get_db_connection():
    """Get a connection to the SQLite database with proper cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@mcp.tool()
def list_tasks(
    status: Optional[str] = None, priority_min: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    List tasks from the database with optional filtering.

    Args:
        status: Filter by status ('pending', 'in_progress', 'completed')
        priority_min: Minimum priority filter (0-10, higher is more important)

    Returns:
        List of task dictionaries with name, description, status, priority, and timestamps
    """
    # Validate status if provided
    if status is not None:
        status = status.lower()
        if status not in [s.value for s in TaskStatus]:
            raise ValueError(
                f"Invalid status. Must be one of: {', '.join([s.value for s in TaskStatus])}"
            )

    # Validate priority_min if provided
    if priority_min is not None and (priority_min < 0 or priority_min > 10):
        raise ValueError("priority_min must be between 0 and 10")

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


@mcp.tool()
def get_task(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific task by name.

    Args:
        name: The name of the task to retrieve

    Returns:
        Task dictionary if found, None otherwise
    """
    if not name or not name.strip():
        raise ValueError("Task name cannot be empty")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
        row = cursor.fetchone()
        return {key: row[key] for key in row.keys()} if row else None


@mcp.tool()
def add_task(
    name: str, description: str, priority: int = 0, status: str = "pending"
) -> Dict[str, Any]:
    """
    Add a new task to the database.

    Args:
        name: Unique name for the task
        description: Description of what the task involves
        priority: Priority level (0-10, higher is more important)
        status: Initial status ('pending', 'in_progress', 'completed')

    Returns:
        The created task dictionary
    """
    # Validate input using Pydantic (validator converts string to TaskStatus enum)
    task = Task(name=name, description=description, priority=priority, status=status)  # type: ignore[arg-type]

    with get_db_connection() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO tasks (name, description, priority, status)
                VALUES (?, ?, ?, ?)
                """,
                (task.name, task.description, task.priority, task.status.value),
            )
            conn.commit()

            # Return the created task
            cursor.execute("SELECT * FROM tasks WHERE name = ?", (task.name,))
            row = cursor.fetchone()
            if row:
                return {key: row[key] for key in row.keys()}
            return {}

        except sqlite3.IntegrityError as e:
            raise ValueError(f"Task with name '{name}' already exists") from e


@mcp.tool()
def update_task(
    name: str,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update an existing task.

    Args:
        name: Name of the task to update
        description: New description (optional)
        status: New status (optional)
        priority: New priority (optional)
        started_at: ISO timestamp when task was started (optional)
        completed_at: ISO timestamp when task was completed (optional)

    Returns:
        Updated task dictionary if found, None otherwise
    """
    if not name or not name.strip():
        raise ValueError("Task name cannot be empty")

    # Validate status if provided
    if status is not None:
        status = status.lower()
        if status not in [s.value for s in TaskStatus]:
            raise ValueError(
                f"Invalid status. Must be one of: {', '.join([s.value for s in TaskStatus])}"
            )

    # Validate priority if provided
    if priority is not None and (priority < 0 or priority > 10):
        raise ValueError("Priority must be between 0 and 10")

    # Validate description if provided
    if description is not None and not description.strip():
        raise ValueError("Description cannot be empty")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if task exists
        cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
        if not cursor.fetchone():
            return None

        # Build dynamic update query
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
        if started_at is not None:
            updates.append("started_at = ?")
            params.append(started_at)
        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(completed_at)

        if not updates:
            return get_task(name)

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE name = ?"
        params.append(name)

        cursor.execute(query, params)
        conn.commit()

        return get_task(name)


@mcp.tool()
def delete_task(name: str) -> bool:
    """
    Delete a task from the database.

    Args:
        name: Name of the task to delete

    Returns:
        True if task was deleted, False if task was not found
    """
    if not name or not name.strip():
        raise ValueError("Task name cannot be empty")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE name = ?", (name,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted


@mcp.tool()
def list_dependencies(task_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List task dependencies.

    Args:
        task_name: Filter dependencies for a specific task (optional)

    Returns:
        List of dependency relationships
    """
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


@mcp.tool()
def add_dependency(task_name: str, depends_on_task_name: str) -> Dict[str, Any]:
    """
    Add a dependency relationship between tasks.

    Args:
        task_name: Name of the task that depends on another task
        depends_on_task_name: Name of the task that must be completed first

    Returns:
        The created dependency relationship
    """
    # Validate input using Pydantic
    dependency = Dependency(
        task_name=task_name, depends_on_task_name=depends_on_task_name
    )

    with get_db_connection() as conn:
        cursor = conn.cursor()

        try:
            # Verify both tasks exist
            cursor.execute(
                "SELECT name FROM tasks WHERE name IN (?, ?)",
                (dependency.task_name, dependency.depends_on_task_name),
            )
            if len(cursor.fetchall()) != 2:
                raise ValueError("Both tasks must exist to create a dependency")

            # Add the dependency
            cursor.execute(
                "INSERT INTO dependencies (task_name, depends_on_task_name) VALUES (?, ?)",
                (dependency.task_name, dependency.depends_on_task_name),
            )
            conn.commit()

            return {
                "task_name": dependency.task_name,
                "depends_on_task_name": dependency.depends_on_task_name,
            }

        except sqlite3.IntegrityError as e:
            if "circular" in str(e).lower():
                raise ValueError("Circular dependencies are not allowed") from e
            raise ValueError("Dependency already exists") from e


@mcp.tool()
def remove_dependency(task_name: str, depends_on_task_name: str) -> bool:
    """
    Remove a dependency relationship.

    Args:
        task_name: Name of the task
        depends_on_task_name: Name of the task it depends on

    Returns:
        True if dependency was removed, False if not found
    """
    # Validate input using Pydantic
    dependency = Dependency(
        task_name=task_name, depends_on_task_name=depends_on_task_name
    )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM dependencies WHERE task_name = ? AND depends_on_task_name = ?",
            (dependency.task_name, dependency.depends_on_task_name),
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted


@mcp.tool()
def get_available_tasks() -> List[Dict[str, Any]]:
    """
    Get tasks that can be started (no uncompleted dependencies).

    Returns:
        List of available tasks with their dependencies resolved
    """
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


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Simple test mode - test database connection and queries
        print("Testing TaskTree MCP Server...")

        # Test basic database connection and queries
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Test all tasks query
            cursor.execute("SELECT * FROM tasks ORDER BY priority DESC, created_at ASC")
            all_tasks = [
                {key: row[key] for key in row.keys()} for row in cursor.fetchall()
            ]
            print(f"All tasks: {all_tasks}")

            # Test available tasks query
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
            available_tasks = [
                {key: row[key] for key in row.keys()} for row in cursor.fetchall()
            ]
            print(f"Available tasks: {available_tasks}")

        print("Test completed successfully!")
    else:
        # Run the MCP server
        mcp.run()
