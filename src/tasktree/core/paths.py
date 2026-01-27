"""
Database path resolution for TaskTree.

This module handles the strategy for locating the TaskTree database file:
1. Check TASKTREE_DB_PATH environment variable (absolute override)
2. Walk up from cwd to find repo root (look for .git directory)
3. Use .tasktree/tasktree.db relative to repo root
4. Fall back to user home directory if no repo found

Constraints and Failure Modes:
- TASKTREE_DB_PATH must be an absolute path if provided
- Repo root discovery stops at filesystem root (no infinite loops)
- .tasktree directory is created automatically if missing
- Failure to create .tasktree directory raises PermissionError
- Multiple .git directories in hierarchy: uses the first one found (nearest parent)
"""

import os
from pathlib import Path
from typing import Optional


def find_repo_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the repository root by walking up from start_path looking for .git.

    Args:
        start_path: Directory to start searching from (defaults to cwd)

    Returns:
        Path to the repository root directory (parent of .git), or None if not found

    Example:
        /home/user/repos/myproject/src/module/file.py
        -> walks up to /home/user/repos/myproject (if .git exists there)
    """
    current = start_path or Path.cwd()
    current = current.resolve()  # Resolve symlinks and make absolute

    # Walk up the directory tree until we find .git or hit the root
    while True:
        git_dir = current / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return current

        # Check if we've reached the filesystem root
        parent = current.parent
        if parent == current:
            # We've hit the root without finding .git
            return None

        current = parent


def get_db_path() -> Path:
    """
    Get the database path using the following priority:

    1. TASKTREE_DB_PATH environment variable (if set, must be absolute)
    2. .tasktree/tasktree.db in repository root (if in a git repo)
    3. ~/.tasktree/tasktree.db (fallback for non-repo usage)

    Returns:
        Path: Absolute path to the database file

    Raises:
        ValueError: If TASKTREE_DB_PATH is set but not an absolute path
        PermissionError: If .tasktree directory cannot be created

    Side effects:
        - Creates .tasktree directory if it doesn't exist
        - Does NOT create the database file itself (that's handled elsewhere)
    """
    # Priority 1: Environment variable override
    env_path = os.getenv("TASKTREE_DB_PATH")
    if env_path:
        db_path = Path(env_path)
        if not db_path.is_absolute():
            raise ValueError(
                f"TASKTREE_DB_PATH must be an absolute path, got: {env_path}"
            )
        # Ensure parent directory exists
        _ensure_parent_dir(db_path)
        return db_path

    # Priority 2: Repository-local database
    repo_root = find_repo_root()
    if repo_root:
        db_dir = repo_root / ".tasktree"
        _ensure_dir_exists(db_dir)
        return db_dir / "tasktree.db"

    # Priority 3: User home directory fallback
    home_dir = Path.home() / ".tasktree"
    _ensure_dir_exists(home_dir)
    return home_dir / "tasktree.db"


def get_snapshot_path() -> Path:
    """
    Get the snapshot path using the following priority:

    1. TASKTREE_SNAPSHOT_PATH environment variable (if set, must be absolute)
    2. .tasktree/tasktree.io.snapshot.jsonl in repository root (if in a git repo)
    3. ~/.tasktree/tasktree.io.snapshot.jsonl (fallback for non-repo usage)

    Returns:
        Path: Absolute path to the snapshot file

    Raises:
        ValueError: If TASKTREE_SNAPSHOT_PATH is set but not an absolute path
        PermissionError: If the parent directory cannot be created

    Side effects:
        - Creates parent directory if it doesn't exist
        - Does NOT create the snapshot file itself
    """
    env_path = os.getenv("TASKTREE_SNAPSHOT_PATH")
    if env_path:
        snapshot_path = Path(env_path)
        if not snapshot_path.is_absolute():
            raise ValueError(
                f"TASKTREE_SNAPSHOT_PATH must be an absolute path, got: {env_path}"
            )
        _ensure_parent_dir(snapshot_path)
        return snapshot_path

    repo_root = find_repo_root()
    if repo_root:
        snapshot_dir = repo_root / ".tasktree"
        _ensure_dir_exists(snapshot_dir)
        return snapshot_dir / "tasktree.io.snapshot.jsonl"

    home_dir = Path.home() / ".tasktree"
    _ensure_dir_exists(home_dir)
    return home_dir / "tasktree.io.snapshot.jsonl"


def _ensure_dir_exists(dir_path: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        dir_path: Directory path to ensure exists

    Raises:
        PermissionError: If directory cannot be created due to permissions
    """
    if not dir_path.exists():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise PermissionError(f"Cannot create directory {dir_path}: {e}") from e


def _ensure_parent_dir(file_path: Path) -> None:
    """
    Ensure the parent directory of a file exists.

    Args:
        file_path: File path whose parent should be ensured

    Raises:
        PermissionError: If parent directory cannot be created
    """
    parent = file_path.parent
    if not parent.exists():
        _ensure_dir_exists(parent)
