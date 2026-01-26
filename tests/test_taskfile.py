"""
Tests for Taskfile.yml configuration.

Validates that the Taskfile is properly structured and contains all expected tasks.
"""

import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def taskfile_path() -> Path:
    """Return the path to the Taskfile.yml."""
    return Path(__file__).parent.parent / "Taskfile.yml"


@pytest.fixture
def taskfile_config(taskfile_path: Path) -> dict:
    """Load and parse the Taskfile.yml."""
    with open(taskfile_path) as f:
        return yaml.safe_load(f)


def test_taskfile_exists(taskfile_path: Path):
    """Test that Taskfile.yml exists."""
    assert taskfile_path.exists()
    assert taskfile_path.is_file()


def test_taskfile_is_valid_yaml(taskfile_path: Path):
    """Test that Taskfile.yml is valid YAML."""
    with open(taskfile_path) as f:
        config = yaml.safe_load(f)
    assert config is not None
    assert isinstance(config, dict)


def test_taskfile_has_version(taskfile_config: dict):
    """Test that Taskfile specifies a version."""
    assert "version" in taskfile_config
    assert taskfile_config["version"] == "3"


def test_taskfile_has_tasks_section(taskfile_config: dict):
    """Test that Taskfile has a tasks section."""
    assert "tasks" in taskfile_config
    assert isinstance(taskfile_config["tasks"], dict)


def test_all_expected_tasks_exist(taskfile_config: dict):
    """Test that all expected tasks are defined."""
    expected_tasks = [
        "mcp",
        "init-db",
        "create-db",
        "seed-db",
        "refresh-views",
        "graph-json",
        "draw",
        "web-graph",
    ]

    tasks = taskfile_config.get("tasks", {})
    for task_name in expected_tasks:
        assert task_name in tasks, f"Expected task '{task_name}' not found"


def test_graph_task_exists(taskfile_config: dict):
    """Test that the graph task is defined."""
    tasks = taskfile_config.get("tasks", {})
    assert "web-graph" in tasks


def test_graph_task_has_description(taskfile_config: dict):
    """Test that the graph task has a description."""
    graph_task = taskfile_config["tasks"]["web-graph"]
    assert "desc" in graph_task
    assert isinstance(graph_task["desc"], str)
    assert len(graph_task["desc"]) > 0


def test_graph_task_has_commands(taskfile_config: dict):
    """Test that the graph task has commands defined."""
    graph_task = taskfile_config["tasks"]["web-graph"]
    assert "cmds" in graph_task
    assert isinstance(graph_task["cmds"], list)
    assert len(graph_task["cmds"]) > 0


def test_graph_task_starts_server(taskfile_config: dict):
    """Test that the graph task includes server startup command."""
    graph_task = taskfile_config["tasks"]["web-graph"]
    commands = graph_task.get("cmds", [])

    # Commands can be strings or multi-line strings
    all_commands = " ".join(str(cmd) for cmd in commands)

    # Should reference the graph-server.py script
    assert "graph-server.py" in all_commands

    # Should use uv run
    assert "uv run" in all_commands


def test_graph_task_opens_browser(taskfile_config: dict):
    """Test that the graph task includes browser opening logic."""
    graph_task = taskfile_config["tasks"]["web-graph"]
    commands = graph_task.get("cmds", [])

    all_commands = " ".join(str(cmd) for cmd in commands)

    # Should have browser opener logic (xdg-open for Linux, open for macOS, start for Windows)
    assert (
        "xdg-open" in all_commands or "open" in all_commands or "start" in all_commands
    )

    # Should reference the HTML viewer
    assert "graph-viewer.html" in all_commands


def test_graph_task_references_correct_port(taskfile_config: dict):
    """Test that the graph task uses the correct port (8000)."""
    graph_task = taskfile_config["tasks"]["web-graph"]
    commands = graph_task.get("cmds", [])

    all_commands = " ".join(str(cmd) for cmd in commands)

    # Should specify port 8000
    assert "8000" in all_commands


def test_graph_task_references_database(taskfile_config: dict):
    """Test that the graph task references the database."""
    graph_task = taskfile_config["tasks"]["web-graph"]
    commands = graph_task.get("cmds", [])

    all_commands = " ".join(str(cmd) for cmd in commands)

    # Should reference the database path
    assert ".tasktree/tasktree.db" in all_commands


def test_all_tasks_have_descriptions(taskfile_config: dict):
    """Test that all tasks have descriptions."""
    tasks = taskfile_config.get("tasks", {})
    for task_name, task_config in tasks.items():
        assert "desc" in task_config, f"Task '{task_name}' missing description"
        assert isinstance(task_config["desc"], str)
        assert len(task_config["desc"]) > 0


def test_task_command_available():
    """Test that the 'task' command is available in the system."""
    try:
        result = subprocess.run(
            ["task", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("Task command not available in test environment")


def test_task_list_runs_successfully():
    """Test that 'task --list' runs successfully."""
    try:
        result = subprocess.run(
            ["task", "--list"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0

        # Should list the graph task
        assert "web-graph" in result.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pytest.skip("Task command not available in test environment")


def test_graph_task_script_exists():
    """Test that the graph-server.py script exists."""
    script_path = Path(__file__).parent.parent / "scripts" / "graph-server.py"
    assert script_path.exists()
    assert script_path.is_file()


def test_graph_viewer_html_exists():
    """Test that the graph-viewer.html file exists."""
    html_path = Path(__file__).parent.parent / "scripts" / "graph-viewer.html"
    assert html_path.exists()
    assert html_path.is_file()


def test_other_tasks_not_affected(taskfile_config: dict):
    """Test that other tasks are still properly defined."""
    tasks = taskfile_config.get("tasks", {})

    # Check a few key tasks to ensure they haven't been corrupted
    assert "mcp" in tasks
    assert "init-db" in tasks
    assert "draw" in tasks

    # Verify they still have their commands
    assert "cmds" in tasks["mcp"]
    assert "cmds" in tasks["init-db"]
    assert "cmds" in tasks["draw"]
