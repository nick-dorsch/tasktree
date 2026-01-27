"""
Database initialization utilities for TaskTree.

This module provides functions to initialize the TaskTree database
using bundled SQL assets (schemas and views).
"""

import sqlite3
from importlib.resources import files
from pathlib import Path
from typing import List


def get_sql_files(resource_package: str) -> List[tuple[str, str]]:
    """
    Get SQL files from a resource package.

    Args:
        resource_package: Package path (e.g., "tasktree_mcp.sql.schemas")

    Returns:
        List of tuples (filename, content) sorted by filename
    """
    sql_files = []
    package = files(resource_package)

    # Collect all items first, then sort by name
    items = list(package.iterdir())
    items.sort(key=lambda x: x.name)

    for item in items:
        if item.name.endswith(".sql"):
            content = item.read_text(encoding="utf-8")
            sql_files.append((item.name, content))

    return sql_files


def apply_schemas(conn: sqlite3.Connection) -> None:
    """
    Apply database schemas from bundled SQL assets.

    Args:
        conn: Active database connection

    Raises:
        sqlite3.Error: If schema application fails
    """
    schema_files = get_sql_files("tasktree_mcp.sql.schemas")

    for filename, content in schema_files:
        conn.executescript(content)

    conn.commit()


def apply_views(conn: sqlite3.Connection) -> None:
    """
    Apply database views from bundled SQL assets.

    Args:
        conn: Active database connection

    Raises:
        sqlite3.Error: If view application fails
    """
    view_files = get_sql_files("tasktree_mcp.sql.views")

    for filename, content in view_files:
        conn.executescript(content)

    conn.commit()


def initialize_database(db_path: Path, apply_views_flag: bool = True) -> None:
    """
    Initialize a new TaskTree database with schemas and optionally views.

    This function:
    1. Creates the database file if it doesn't exist
    2. Applies all schema files from tasktree_mcp.sql.schemas
    3. Optionally applies all view files from tasktree_mcp.sql.views
    4. Enables foreign key constraints

    Args:
        db_path: Path to the database file to initialize
        apply_views_flag: Whether to apply views (default: True)

    Raises:
        sqlite3.Error: If database initialization fails
        PermissionError: If database file cannot be created
    """
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")

        # Apply schemas
        apply_schemas(conn)

        # Apply views if requested
        if apply_views_flag:
            apply_views(conn)

    finally:
        conn.close()


def refresh_views(db_path: Path) -> None:
    """
    Refresh all views in an existing database.

    This drops and recreates all views from the bundled SQL assets.
    Useful after modifying view definitions.

    Args:
        db_path: Path to the existing database file

    Raises:
        FileNotFoundError: If database file doesn't exist
        sqlite3.Error: If view refresh fails
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")

        # Apply views (DROP IF EXISTS is in the view files)
        apply_views(conn)

    finally:
        conn.close()
