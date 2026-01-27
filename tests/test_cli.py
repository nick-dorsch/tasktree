"""
Tests for TaskTree CLI commands.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tasktree.cli.main import cli

# Test runner for Typer CLI
runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_snapshot_path():
    """Mock get_snapshot_path to return a non-existent path by default."""
    with patch("tasktree.cli.main.get_snapshot_path") as mock:
        mock.return_value = Path("/non/existent/snapshot.jsonl")
        yield mock


@pytest.fixture(scope="function")
def cli_test_db() -> Generator[Path, None, None]:
    """
    Create a temporary test database path for CLI tests.

    Unlike test_db, this fixture does NOT initialize the database,
    allowing CLI tests to test the init command themselves.

    Yields:
        Path: Path to a temporary database file (not yet created)
    """
    # Create a temporary file and delete it immediately
    # We just want a valid path for testing
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    db_path = Path(temp_db.name)
    temp_db.close()
    db_path.unlink()  # Delete the file, we just want the path

    try:
        yield db_path
    finally:
        # Clean up: remove the database file if it was created
        if db_path.exists():
            db_path.unlink()


class TestCLIInit:
    """Test CLI init command."""

    def test_init_creates_database(self, cli_test_db: Path):
        """Test that init creates a new database."""
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert "Database initialized successfully!" in result.stdout
            assert cli_test_db.exists()

            # Verify database has tables
            conn = sqlite3.connect(cli_test_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            assert "tasks" in tables
            assert "features" in tables
            assert "dependencies" in tables

    def test_init_force_overwrites_existing(self, cli_test_db: Path):
        """Test that init with --force overwrites existing database."""
        # Create initial database
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            runner.invoke(cli, ["init"])

            # Verify it exists
            assert cli_test_db.exists()

            # Get initial modification time
            initial_mtime = cli_test_db.stat().st_mtime

            # Sleep to ensure different timestamp
            import time

            time.sleep(0.01)

            # Run with force
            result = runner.invoke(cli, ["init", "--force"])

            assert result.exit_code == 0
            assert "Database initialized successfully!" in result.stdout
            assert cli_test_db.exists()

            # Verify database was overwritten (newer modification time)
            new_mtime = cli_test_db.stat().st_mtime
            assert new_mtime > initial_mtime

    def test_init_fails_on_existing_without_force(self, cli_test_db: Path):
        """Test that init fails on existing database without --force."""
        # Create initial database
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            runner.invoke(cli, ["init"])

            # Try to init again without force
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 1
            assert "Database already exists" in result.output


class TestCLIStart:
    """Test CLI start command."""

    def test_start_fails_on_missing_database(self, cli_test_db: Path):
        """Test that start fails when database doesn't exist."""
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            result = runner.invoke(cli, ["start"])

            assert result.exit_code == 1
            assert "Database not found" in result.output

    def test_start_with_valid_database(self, cli_test_db: Path):
        """Test that start command works with valid database."""
        # Initialize database first
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            runner.invoke(cli, ["init"])

            # Mock the server to avoid actually starting it
            # run_server is imported inside the start function, so we patch it there
            with patch("tasktree.graph.server.run_server") as mock_server:
                result = runner.invoke(cli, ["start", "--port", "9999"])

                assert result.exit_code == 0
                mock_server.assert_called_once_with(9999, cli_test_db)


class TestCLIReset:
    """Test CLI reset command."""

    def test_reset_fails_on_missing_database(self, cli_test_db: Path):
        """Test that reset fails when database doesn't exist."""
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            result = runner.invoke(cli, ["reset"])

            assert result.exit_code == 1
            assert "Database not found" in result.output

    def test_reset_with_confirmation(self, cli_test_db: Path):
        """Test that reset works with user confirmation."""
        # Initialize database and add some data
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            runner.invoke(cli, ["init"])

            # Add test data
            conn = sqlite3.connect(cli_test_db)
            conn.execute(
                "INSERT INTO features (name, description, specification) VALUES (?, ?, ?)",
                ("test-feature", "Test feature", "Test spec"),
            )
            conn.commit()

            # Get the feature_id for the foreign key
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM features WHERE name = ?", ("test-feature",))
            feature_id = cursor.fetchone()[0]

            conn.execute(
                "INSERT INTO tasks (name, description, specification, priority, status, feature_id, tests_required) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("test-task", "Test task", "Test spec", 5, "pending", feature_id, True),
            )
            conn.commit()

            # Verify data exists
            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
            conn.close()

            assert task_count == 1

            # Reset with confirmation
            result = runner.invoke(cli, ["reset", "--confirm"])

            assert result.exit_code == 0
            assert "Database reset successfully!" in result.stdout

            # Verify data is gone but schema remains
            conn = sqlite3.connect(cli_test_db)
            cursor = conn.cursor()

            # Check tables still exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "tasks" in tables
            assert "features" in tables

            # Check data is gone
            cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM features")
            feature_count = cursor.fetchone()[0]

            conn.close()

            assert task_count == 0
            assert feature_count == 0

    def test_reset_without_confirmation_prompts(self, cli_test_db: Path):
        """Test that reset prompts for confirmation without --confirm flag."""
        # Initialize database
        with patch("tasktree.cli.main.get_db_path", return_value=cli_test_db):
            runner.invoke(cli, ["init"])

            # Try reset without confirmation (should prompt)
            result = runner.invoke(cli, ["reset"], input="n\n")

            assert result.exit_code == 0
            assert "Operation cancelled" in result.stdout


class TestCLIGeneral:
    """Test general CLI behavior."""

    def test_cli_help(self):
        """Test that CLI shows help."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "TaskTree CLI" in result.stdout
        assert "init" in result.stdout
        assert "start" in result.stdout
        assert "reset" in result.stdout

    def test_cli_no_args_shows_help(self):
        """Test that CLI with no args shows help."""
        result = runner.invoke(cli, [])

        # Exit code 2 is standard Click/Typer behavior for missing required command
        # (vs exit code 0 for explicit --help flag)
        assert result.exit_code == 2
        assert "TaskTree CLI" in result.stdout or "Usage:" in result.stdout


class TestCLIEntryPoint:
    """Test console script entry point."""

    def test_console_script_entry_point(self):
        """Test that the tasktree console script entry point is correctly configured."""
        # Test that the CLI app is importable and has the expected structure
        from tasktree.cli.main import cli

        # Verify it's a Typer app
        assert hasattr(cli, "registered_commands") or hasattr(cli, "info")

        # Verify the main commands are registered by invoking with --help
        # This is a more reliable way to test that commands are available
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.stdout
        assert "start" in result.stdout
        assert "reset" in result.stdout


class TestCLIInitSnapshot:
    """Test CLI init command with snapshot integration."""

    @pytest.fixture(scope="function")
    def temp_paths(self) -> Generator[tuple[Path, Path], None, None]:
        """
        Create temporary test database and snapshot paths.

        Yields:
            tuple[Path, Path]: (db_path, snapshot_path)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            db_path = temp_dir_path / "test.db"
            snapshot_path = temp_dir_path / "snapshot.jsonl"
            yield db_path, snapshot_path

    def test_init_restores_from_snapshot(self, temp_paths: tuple[Path, Path]):
        """Test that init restores data if snapshot exists."""
        db_path, snapshot_path = temp_paths

        # Create a valid snapshot file
        snapshot_data = [
            {
                "record_type": "meta",
                "schema_version": "1",
                "generated_at": "2026-01-27T22:00:00Z",
            },
            {
                "record_type": "feature",
                "name": "feat1",
                "description": "desc1",
                "specification": "spec1",
                "created_at": "2026-01-27T22:00:00Z",
                "updated_at": "2026-01-27T22:00:00Z",
            },
            {
                "record_type": "task",
                "name": "task1",
                "description": "desc1",
                "specification": "spec1",
                "priority": 5,
                "status": "pending",
                "feature_name": "feat1",
                "created_at": "2026-01-27T22:00:00Z",
                "updated_at": "2026-01-27T22:00:00Z",
                "tests_required": True,
            },
        ]

        with snapshot_path.open("w", encoding="utf-8") as f:
            for record in snapshot_data:
                f.write(json.dumps(record) + "\n")

        with (
            patch("tasktree.cli.main.get_db_path", return_value=db_path),
            patch("tasktree.cli.main.get_snapshot_path", return_value=snapshot_path),
        ):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert "Database initialized successfully!" in result.stdout
            assert f"Restoring database from snapshot: {snapshot_path}" in result.stdout
            assert "✓ Database restored from snapshot." in result.stdout
            assert db_path.exists()

            # Verify database contains records from snapshot
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name, description FROM features")
            features = cursor.fetchall()
            feature_names = [f["name"] for f in features]
            assert "feat1" in feature_names
            assert "misc" in feature_names
            assert len(features) == 2

            cursor.execute("SELECT name, description, priority FROM tasks")
            tasks = cursor.fetchall()
            assert len(tasks) == 1
            assert tasks[0]["name"] == "task1"
            assert tasks[0]["priority"] == 5

            conn.close()

    def test_init_works_without_snapshot(self, temp_paths: tuple[Path, Path]):
        """Test that init works fine if no snapshot exists."""
        db_path, snapshot_path = temp_paths
        # Ensure snapshot path does NOT exist
        assert not snapshot_path.exists()

        with (
            patch("tasktree.cli.main.get_db_path", return_value=db_path),
            patch("tasktree.cli.main.get_snapshot_path", return_value=snapshot_path),
        ):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert "Database initialized successfully!" in result.stdout
            assert "Restoring database from snapshot" not in result.stdout
            assert db_path.exists()

            # Verify database is empty but schema exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            assert cursor.fetchone()[0] == 0
            conn.close()
