"""
Tests for database path resolution logic.
"""

from pathlib import Path

import pytest

from tasktree_mcp.paths import find_repo_root, get_db_path, get_snapshot_path


class TestFindRepoRoot:
    """Tests for find_repo_root function."""

    def test_find_repo_root_from_repo_directory(self, tmp_path):
        """Test finding repo root when starting from repo directory."""
        # Create a mock git repo structure
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        # Should find the repo root
        result = find_repo_root(repo_root)
        assert result == repo_root

    def test_find_repo_root_from_nested_directory(self, tmp_path):
        """Test finding repo root from deeply nested subdirectory."""
        # Create a mock git repo structure
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        # Create nested subdirectories
        nested = repo_root / "src" / "module" / "submodule"
        nested.mkdir(parents=True)

        # Should find the repo root from nested directory
        result = find_repo_root(nested)
        assert result == repo_root

    def test_find_repo_root_no_git_directory(self, tmp_path):
        """Test behavior when no .git directory exists."""
        # Create a directory without .git
        no_repo = tmp_path / "not_a_repo"
        no_repo.mkdir()

        # Should return None
        result = find_repo_root(no_repo)
        assert result is None

    def test_find_repo_root_defaults_to_cwd(self, tmp_path, monkeypatch):
        """Test that find_repo_root defaults to current working directory."""
        # Create a mock git repo
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        # Change to the repo directory
        monkeypatch.chdir(repo_root)

        # Should find repo root from cwd
        result = find_repo_root()
        assert result == repo_root

    def test_find_repo_root_with_git_file(self, tmp_path):
        """Test that only .git directories are recognized, not files."""
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()

        # Create .git as a file (not a directory)
        (repo_root / ".git").touch()

        # Should not recognize .git file as repo marker
        result = find_repo_root(repo_root)
        assert result is None

    def test_find_repo_root_nested_git_directories(self, tmp_path):
        """Test that nearest .git directory is found (not parent repos)."""
        # Create outer repo
        outer_repo = tmp_path / "outer"
        outer_repo.mkdir()
        (outer_repo / ".git").mkdir()

        # Create inner repo (submodule scenario)
        inner_repo = outer_repo / "inner"
        inner_repo.mkdir()
        (inner_repo / ".git").mkdir()

        # Should find the inner repo, not outer
        result = find_repo_root(inner_repo)
        assert result == inner_repo


class TestGetDbPath:
    """Tests for get_db_path function."""

    def test_get_db_path_with_env_override(self, tmp_path, monkeypatch):
        """Test that TASKTREE_DB_PATH environment variable takes priority."""
        db_path = tmp_path / "custom" / "my_db.db"
        monkeypatch.setenv("TASKTREE_DB_PATH", str(db_path))

        result = get_db_path()
        assert result == db_path
        # Parent directory should be created
        assert db_path.parent.exists()

    def test_get_db_path_env_must_be_absolute(self, monkeypatch):
        """Test that TASKTREE_DB_PATH must be an absolute path."""
        monkeypatch.setenv("TASKTREE_DB_PATH", "relative/path/db.db")

        with pytest.raises(ValueError, match="must be an absolute path"):
            get_db_path()

    def test_get_db_path_in_git_repo(self, tmp_path, monkeypatch):
        """Test that .tasktree/tasktree.db is used when in a git repo."""
        # Create mock git repo
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        # Change to repo directory
        monkeypatch.chdir(repo_root)
        # Ensure no env override
        monkeypatch.delenv("TASKTREE_DB_PATH", raising=False)

        result = get_db_path()
        expected = repo_root / ".tasktree" / "tasktree.db"

        assert result == expected
        # .tasktree directory should be created
        assert (repo_root / ".tasktree").exists()
        assert (repo_root / ".tasktree").is_dir()

    def test_get_db_path_fallback_to_home(self, tmp_path, monkeypatch):
        """Test fallback to ~/.tasktree/tasktree.db when not in a repo."""
        # Create a non-repo directory
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        # Mock home directory
        mock_home = tmp_path / "home"
        mock_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: mock_home)

        # Change to non-repo directory
        monkeypatch.chdir(non_repo)
        # Ensure no env override
        monkeypatch.delenv("TASKTREE_DB_PATH", raising=False)

        result = get_db_path()
        expected = mock_home / ".tasktree" / "tasktree.db"

        assert result == expected
        # .tasktree directory should be created in home
        assert (mock_home / ".tasktree").exists()

    def test_get_db_path_creates_tasktree_directory(self, tmp_path, monkeypatch):
        """Test that .tasktree directory is automatically created."""
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        monkeypatch.chdir(repo_root)
        monkeypatch.delenv("TASKTREE_DB_PATH", raising=False)

        # .tasktree should not exist yet
        assert not (repo_root / ".tasktree").exists()

        result = get_db_path()

        # .tasktree should now exist
        assert (repo_root / ".tasktree").exists()
        assert result == repo_root / ".tasktree" / "tasktree.db"

    def test_get_db_path_from_nested_directory_in_repo(self, tmp_path, monkeypatch):
        """Test that database path is correctly resolved from nested repo directory."""
        # Create repo with nested structure
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        nested = repo_root / "src" / "module"
        nested.mkdir(parents=True)

        # Change to nested directory
        monkeypatch.chdir(nested)
        monkeypatch.delenv("TASKTREE_DB_PATH", raising=False)

        result = get_db_path()
        expected = repo_root / ".tasktree" / "tasktree.db"

        # Should still resolve to repo root's .tasktree
        assert result == expected
        assert (repo_root / ".tasktree").exists()

    def test_get_db_path_env_override_takes_precedence_over_repo(
        self, tmp_path, monkeypatch
    ):
        """Test that env var takes precedence even when in a git repo."""
        # Create git repo
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        # Set env override
        custom_db = tmp_path / "custom_db.db"
        monkeypatch.setenv("TASKTREE_DB_PATH", str(custom_db))
        monkeypatch.chdir(repo_root)

        result = get_db_path()

        # Should use env var, not repo .tasktree
        assert result == custom_db
        assert not (repo_root / ".tasktree").exists()

    def test_get_db_path_permission_error_handling(self, tmp_path, monkeypatch):
        """Test that PermissionError is raised when directory cannot be created."""
        # This test is tricky to implement portably since we need to simulate
        # permission errors. We'll test the error path by mocking mkdir.
        from unittest.mock import patch

        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        monkeypatch.chdir(repo_root)
        monkeypatch.delenv("TASKTREE_DB_PATH", raising=False)

        # Mock mkdir to raise PermissionError
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError, match="Cannot create directory"):
                get_db_path()


class TestPathResolutionIntegration:
    """Integration tests for path resolution with actual database operations."""

    def test_db_path_resolution_in_real_repo(self, monkeypatch):
        """Test that we correctly identify the tasktree repo root."""
        # We're running in the tasktree repo itself
        # Find the actual repo root
        from tasktree_mcp.paths import find_repo_root

        repo_root = find_repo_root()

        # We should find a repo root (since tests run in the tasktree repo)
        assert repo_root is not None
        assert (repo_root / ".git").exists()

    def test_db_path_is_absolute(self, tmp_path, monkeypatch):
        """Test that get_db_path always returns an absolute path."""
        # Test in repo
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        monkeypatch.chdir(repo_root)
        monkeypatch.delenv("TASKTREE_DB_PATH", raising=False)

        result = get_db_path()
        assert result.is_absolute()

    def test_multiple_calls_return_same_path(self, tmp_path, monkeypatch):
        """Test that multiple calls to get_db_path return consistent results."""
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        monkeypatch.chdir(repo_root)
        monkeypatch.delenv("TASKTREE_DB_PATH", raising=False)

        path1 = get_db_path()
        path2 = get_db_path()

        assert path1 == path2


class TestGetSnapshotPath:
    """Tests for get_snapshot_path function."""

    def test_get_snapshot_path_with_env_override(self, tmp_path, monkeypatch):
        """Test that TASKTREE_SNAPSHOT_PATH environment variable takes priority."""
        snapshot_path = tmp_path / "snapshots" / "tasktree.snapshot.jsonl"
        monkeypatch.setenv("TASKTREE_SNAPSHOT_PATH", str(snapshot_path))

        result = get_snapshot_path()

        assert result == snapshot_path
        assert snapshot_path.parent.exists()

    def test_get_snapshot_path_env_must_be_absolute(self, monkeypatch):
        """Test that TASKTREE_SNAPSHOT_PATH must be an absolute path."""
        monkeypatch.setenv("TASKTREE_SNAPSHOT_PATH", "relative/snapshot.jsonl")

        with pytest.raises(ValueError, match="must be an absolute path"):
            get_snapshot_path()

    def test_get_snapshot_path_in_git_repo(self, tmp_path, monkeypatch):
        """Test that repo root snapshot path is used when in a git repo."""
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()
        (repo_root / ".git").mkdir()

        monkeypatch.chdir(repo_root)
        monkeypatch.delenv("TASKTREE_SNAPSHOT_PATH", raising=False)

        result = get_snapshot_path()
        expected = repo_root / "tasktree.snapshot.jsonl"

        assert result == expected
        assert result.is_absolute()

    def test_get_snapshot_path_fallback_to_cwd(self, tmp_path, monkeypatch):
        """Test fallback to cwd when not in a git repo."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        monkeypatch.chdir(non_repo)
        monkeypatch.delenv("TASKTREE_SNAPSHOT_PATH", raising=False)

        result = get_snapshot_path()
        expected = non_repo.resolve() / "tasktree.snapshot.jsonl"

        assert result == expected
        assert result.is_absolute()
