#!/usr/bin/env python3
"""
TaskTree MCP Server
A Model Context Protocol server that provides tools for querying and managing tasks
in the TaskTree SQLite database.
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("tasktree")

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "tasktree.db"


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


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
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
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
    conn.close()

    return [dict(row) for row in rows]


@mcp.tool()
def get_task(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific task by name.

    Args:
        name: The name of the task to retrieve

    Returns:
        Task dictionary if found, None otherwise
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


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
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO tasks (name, description, priority, status)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, priority, status),
        )
        conn.commit()

        # Return the created task
        cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
        conn.row_factory = sqlite3.Row
        result = dict(cursor.fetchone())

    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"Task with name '{name}' already exists") from e
    finally:
        conn.close()

    return result


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
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if task exists
    cursor.execute("SELECT * FROM tasks WHERE name = ?", (name,))
    if not cursor.fetchone():
        conn.close()
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
        conn.close()
        return get_task(name)

    query = f"UPDATE tasks SET {', '.join(updates)} WHERE name = ?"
    params.append(name)

    cursor.execute(query, params)
    conn.commit()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tasks WHERE name = ?", (name,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

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
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
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
    conn.close()

    return [dict(row) for row in rows]


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
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verify both tasks exist
        cursor.execute(
            "SELECT name FROM tasks WHERE name IN (?, ?)",
            (task_name, depends_on_task_name),
        )
        if len(cursor.fetchall()) != 2:
            conn.close()
            raise ValueError("Both tasks must exist to create a dependency")

        # Add the dependency
        cursor.execute(
            "INSERT INTO dependencies (task_name, depends_on_task_name) VALUES (?, ?)",
            (task_name, depends_on_task_name),
        )
        conn.commit()

        result = {"task_name": task_name, "depends_on_task_name": depends_on_task_name}

    except sqlite3.IntegrityError as e:
        conn.close()
        if "circular" in str(e).lower():
            raise ValueError("Circular dependencies are not allowed") from e
        raise ValueError("Dependency already exists") from e
    finally:
        conn.close()

    return result


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
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM dependencies WHERE task_name = ? AND depends_on_task_name = ?",
        (task_name, depends_on_task_name),
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


@mcp.tool()
def get_available_tasks() -> List[Dict[str, Any]]:
    """
    Get tasks that can be started (no uncompleted dependencies).

    Returns:
        List of available tasks with their dependencies resolved
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
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
    conn.close()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Simple test mode - call the functions directly without MCP decorators
        print("Testing TaskTree MCP Server...")

        # Direct database functions for testing
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

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
        available_tasks = [dict(row) for row in cursor.fetchall()]

        # Test all tasks query
        cursor.execute("SELECT * FROM tasks ORDER BY priority DESC, created_at ASC")
        all_tasks = [dict(row) for row in cursor.fetchall()]

        conn.close()

        print("Available tasks:", available_tasks)
        print("All tasks:", all_tasks)
        print("Test completed successfully!")
    else:
        # Run the MCP server
        mcp.run()
