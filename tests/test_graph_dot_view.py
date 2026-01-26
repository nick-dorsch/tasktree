"""
Tests for the v_graph_dot SQL view to ensure status-based color coding.

Tests that the DOT format graph includes:
- Status-based fill colors (pending=blue, in_progress=yellow, completed=green)
- Available tasks marked with thicker borders
- Proper Graphviz DOT format
"""

from pathlib import Path

import pytest

from tasktree_mcp.database import DependencyRepository, TaskRepository


@pytest.fixture
def mock_db_path(test_db: Path, monkeypatch):
    """
    Mock the DB_PATH to use the test database.

    This fixture modifies the database.DB_PATH to point to the test database,
    ensuring all repository operations use the isolated test database.
    """
    import tasktree_mcp.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


def get_graph_dot(test_db: Path) -> str:
    """Helper to fetch the DOT graph from the view."""
    import sqlite3

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT dot_graph FROM v_graph_dot")
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        return result[0]
    return ""


def test_graph_dot_has_pending_color(mock_db_path):
    """Test that pending tasks are colored blue."""
    TaskRepository.add_task(
        name="pending-task",
        description="A pending task",
        status="pending",
    )

    dot = get_graph_dot(mock_db_path)

    # Should contain the task with lightblue color
    assert '"pending-task"' in dot
    assert "fillcolor=lightblue" in dot


def test_graph_dot_has_in_progress_color(mock_db_path):
    """Test that in_progress tasks are colored yellow."""
    TaskRepository.add_task(
        name="active-task",
        description="A task in progress",
        status="in_progress",
    )

    dot = get_graph_dot(mock_db_path)

    # Should contain the task with yellow color
    assert '"active-task"' in dot
    assert "fillcolor=yellow" in dot


def test_graph_dot_has_completed_color(mock_db_path):
    """Test that completed tasks are colored green."""
    TaskRepository.add_task(
        name="done-task",
        description="A completed task",
        status="completed",
    )

    dot = get_graph_dot(mock_db_path)

    # Should contain the task with lightgreen color
    assert '"done-task"' in dot
    assert "fillcolor=lightgreen" in dot


def test_graph_dot_has_blocked_color(mock_db_path):
    """Test that blocked tasks are colored gray."""
    TaskRepository.add_task(
        name="blocked-task",
        description="A blocked task",
        status="blocked",
    )

    dot = get_graph_dot(mock_db_path)

    # Should contain the task with lightgray color
    assert '"blocked-task"' in dot
    assert "fillcolor=lightgray" in dot


def test_graph_dot_available_task_has_thick_border(mock_db_path):
    """Test that available tasks have a thicker border (penwidth=3)."""
    TaskRepository.add_task(
        name="available-task",
        description="An available task",
        status="pending",
    )

    dot = get_graph_dot(mock_db_path)

    # Available pending task should have lightblue color and thick border
    assert '"available-task"' in dot
    assert "fillcolor=lightblue" in dot
    assert "penwidth=3" in dot


def test_graph_dot_non_available_task_no_thick_border(mock_db_path):
    """Test that non-available tasks don't have thick borders."""
    # Create two tasks with a dependency
    TaskRepository.add_task("base-task", "Base task", status="pending")
    TaskRepository.add_task("dependent-task", "Dependent task", status="pending")
    DependencyRepository.add_dependency("dependent-task", "base-task")

    dot = get_graph_dot(mock_db_path)

    # dependent-task should not have thick border (not available)
    # We need to check that its node definition doesn't include penwidth=3
    lines = dot.split("\n")
    dependent_line = [line for line in lines if '"dependent-task"' in line][0]

    # Should have color but no thick border
    assert "fillcolor=lightblue" in dependent_line
    assert "penwidth=3" not in dependent_line


def test_graph_dot_multiple_statuses(mock_db_path):
    """Test that different task statuses get different colors."""
    TaskRepository.add_task("task-1", "Pending task", status="pending")
    TaskRepository.add_task("task-2", "In progress task", status="in_progress")
    TaskRepository.add_task("task-3", "Completed task", status="completed")
    TaskRepository.add_task("task-4", "Blocked task", status="blocked")

    dot = get_graph_dot(mock_db_path)

    # Verify all tasks are present with their respective colors
    assert '"task-1"' in dot
    assert '"task-2"' in dot
    assert '"task-3"' in dot
    assert '"task-4"' in dot

    # Check colors - need to verify each task has its color
    lines = dot.split("\n")

    task1_line = [line for line in lines if '"task-1"' in line][0]
    assert "fillcolor=lightblue" in task1_line

    task2_line = [line for line in lines if '"task-2"' in line][0]
    assert "fillcolor=yellow" in task2_line

    task3_line = [line for line in lines if '"task-3"' in line][0]
    assert "fillcolor=lightgreen" in task3_line

    task4_line = [line for line in lines if '"task-4"' in line][0]
    assert "fillcolor=lightgray" in task4_line


def test_graph_dot_has_valid_structure(mock_db_path):
    """Test that the DOT graph has valid Graphviz structure."""
    TaskRepository.add_task("test-task", "Test task")

    dot = get_graph_dot(mock_db_path)

    # Should start with digraph declaration
    assert dot.startswith("digraph TaskTree {")
    assert dot.endswith("}")

    # Should have rankdir
    assert "rankdir=TB" in dot

    # Should have node styling
    assert "node [shape=box, style=rounded]" in dot


def test_graph_dot_with_dependencies(mock_db_path):
    """Test that dependencies are shown as edges in DOT format."""
    TaskRepository.add_task("task-a", "Task A", status="completed")
    TaskRepository.add_task("task-b", "Task B", status="pending")
    DependencyRepository.add_dependency("task-b", "task-a")

    dot = get_graph_dot(mock_db_path)

    # Should have edge from task-a to task-b
    assert '"task-a" -> "task-b"' in dot

    # Verify colors are correct
    assert "fillcolor=lightgreen" in dot  # task-a is completed
    assert "fillcolor=lightblue" in dot  # task-b is pending


def test_graph_dot_empty_database(mock_db_path):
    """Test that DOT graph works with an empty database."""
    dot = get_graph_dot(mock_db_path)

    # Should still have valid structure
    assert dot.startswith("digraph TaskTree {")
    assert dot.endswith("}")


def test_graph_dot_all_nodes_have_style_filled(mock_db_path):
    """Test that all nodes use filled style with rounded shape."""
    TaskRepository.add_task("task-1", "Task 1", status="pending")
    TaskRepository.add_task("task-2", "Task 2", status="completed")

    dot = get_graph_dot(mock_db_path)

    lines = dot.split("\n")

    # Find all task node lines
    task_lines = [line for line in lines if '"task-' in line and "[" in line]

    # All should have style="rounded,filled"
    for line in task_lines:
        assert 'style="rounded,filled"' in line


def test_graph_dot_completed_dependency_makes_task_available(mock_db_path):
    """Test that completing a dependency makes dependent task available with thick border."""
    TaskRepository.add_task("base", "Base task", status="completed")
    TaskRepository.add_task("dependent", "Dependent task", status="pending")
    DependencyRepository.add_dependency("dependent", "base")

    dot = get_graph_dot(mock_db_path)

    lines = dot.split("\n")

    # Find the dependent task line
    dependent_line = [line for line in lines if '"dependent"' in line and "[" in line][
        0
    ]

    # Should be available (all dependencies completed) so should have thick border
    assert "penwidth=3" in dependent_line
    assert "fillcolor=lightblue" in dependent_line  # Still pending status
