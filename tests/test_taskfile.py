"""
Tests for Taskfile.yml content.
"""

from pathlib import Path
import yaml


def test_taskfile_mcp_command():
    """Verify that the mcp task in Taskfile.yml uses the tasktree CLI."""
    taskfile_path = Path(__file__).parent.parent / "Taskfile.yml"
    assert taskfile_path.exists()

    with open(taskfile_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    mcp_task = config.get("tasks", {}).get("mcp", {})
    cmds = mcp_task.get("cmds", [])

    # Check that it uses 'uv run tasktree mcp'
    expected_cmd = "uv run tasktree mcp"
    assert expected_cmd in cmds

    # Verify it no longer uses the direct python script call
    old_cmd = "uv run python src/tasktree/mcp/server.py"
    assert old_cmd not in cmds
