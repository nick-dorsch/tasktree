"""
Tests for database initialization using bundled SQL assets.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from tasktree_mcp.db_init import (
    apply_schemas,
    apply_views,
    get_sql_files,
    initialize_database,
    refresh_views,
)


def test_get_sql_files_schemas():
    """Test getting schema SQL files from bundled resources."""
    files = get_sql_files("tasktree_mcp.sql.schemas")

    # Should have at least 3 schema files
    assert len(files) >= 3

    # All should be tuples of (filename, content)
    for filename, content in files:
        assert filename.endswith(".sql")
        assert isinstance(content, str)
        assert len(content) > 0

    # Files should be sorted
    filenames = [f[0] for f in files]
    assert filenames == sorted(filenames)


def test_get_sql_files_views():
    """Test getting view SQL files from bundled resources."""
    files = get_sql_files("tasktree_mcp.sql.views")

    # Should have at least 6 view files
    assert len(files) >= 6

    # All should be tuples of (filename, content)
    for filename, content in files:
        assert filename.endswith(".sql")
        assert isinstance(content, str)
        assert len(content) > 0


def test_apply_schemas():
    """Test applying schemas to a database."""
    # Create a temporary database
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    db_path = Path(temp_db.name)
    temp_db.close()

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Apply schemas
        apply_schemas(conn)

        # Verify tables exist
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "features" in tables
        assert "tasks" in tables
        assert "dependencies" in tables

        conn.close()

    finally:
        if db_path.exists():
            db_path.unlink()


def test_apply_views():
    """Test applying views to a database."""
    # Create a temporary database with schema
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    db_path = Path(temp_db.name)
    temp_db.close()

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        # Apply schemas first
        apply_schemas(conn)

        # Apply views
        apply_views(conn)

        # Verify views exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = [row[0] for row in cursor.fetchall()]

        assert "v_available_tasks" in views
        assert "v_dependency_tree" in views
        assert "v_graph_json" in views

        conn.close()

    finally:
        if db_path.exists():
            db_path.unlink()


def test_initialize_database():
    """Test full database initialization."""
    # Create a temporary database
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    db_path = Path(temp_db.name)
    temp_db.close()

    try:
        # Initialize database
        initialize_database(db_path, apply_views_flag=True)

        # Verify database exists and has tables/views
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "features" in tables
        assert "tasks" in tables
        assert "dependencies" in tables

        # Check views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = [row[0] for row in cursor.fetchall()]
        assert "v_available_tasks" in views

        # Check foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result is not None

        conn.close()

    finally:
        if db_path.exists():
            db_path.unlink()


def test_initialize_database_without_views():
    """Test database initialization without views."""
    # Create a temporary database
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    db_path = Path(temp_db.name)
    temp_db.close()

    try:
        # Initialize database without views
        initialize_database(db_path, apply_views_flag=False)

        # Verify database exists and has tables but no views
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "tasks" in tables

        # Check views
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = [row[0] for row in cursor.fetchall()]
        assert len(views) == 0

        conn.close()

    finally:
        if db_path.exists():
            db_path.unlink()


def test_refresh_views():
    """Test refreshing views in an existing database."""
    # Create a temporary database
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    db_path = Path(temp_db.name)
    temp_db.close()

    try:
        # Initialize database
        initialize_database(db_path, apply_views_flag=True)

        # Refresh views
        refresh_views(db_path)

        # Verify views still exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = [row[0] for row in cursor.fetchall()]
        assert "v_available_tasks" in views
        conn.close()

    finally:
        if db_path.exists():
            db_path.unlink()


def test_refresh_views_nonexistent_database():
    """Test refresh_views raises error for nonexistent database."""
    nonexistent_path = Path("/tmp/nonexistent_tasktree_test.db")

    with pytest.raises(FileNotFoundError):
        refresh_views(nonexistent_path)
