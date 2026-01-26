"""Tests for snapshot workflow documentation."""

from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_root_readme_snapshot_workflow() -> None:
    """Ensure root README documents snapshot workflow details."""
    readme_path = Path(__file__).parent.parent / "README.md"
    contents = _read_text(readme_path)

    assert "Snapshot Workflow" in contents
    assert "task snapshot-export" in contents
    assert "task snapshot-import" in contents
    assert ".tasktree/tasktree.snapshot.jsonl" in contents
    assert "TASKTREE_SNAPSHOT_PATH" in contents
    assert ".tasktree/tasktree.db" in contents


def test_mcp_readme_snapshot_workflow() -> None:
    """Ensure MCP README documents snapshot workflow details."""
    readme_path = Path(__file__).parent.parent / "src" / "tasktree_mcp" / "README.md"
    contents = _read_text(readme_path)

    assert "Snapshot Workflow" in contents
    assert "task snapshot-export" in contents
    assert "task snapshot-import" in contents
    assert ".tasktree/tasktree.snapshot.jsonl" in contents
    assert ".tasktree/tasktree.db" in contents
