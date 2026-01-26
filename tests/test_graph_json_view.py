"""
Tests for the v_graph_json SQL view to ensure it includes the description field.
"""

import json
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


def get_graph_json(test_db: Path) -> dict:
    """Helper to fetch the graph JSON from the view."""
    import sqlite3

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT graph_json FROM v_graph_json")
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        return json.loads(result[0])
    return {"nodes": [], "edges": []}


def test_graph_json_includes_description(mock_db_path):
    """Test that the graph_json view includes the description field."""
    # Add a task with a description
    TaskRepository.add_task(
        name="test-task",
        description="This is a test task description",
        priority=5,
    )

    # Get the graph JSON
    graph = get_graph_json(mock_db_path)

    # Verify structure
    assert "nodes" in graph
    assert "edges" in graph

    # Find our task
    nodes = graph["nodes"]
    assert len(nodes) == 1

    task_node = nodes[0]

    # Verify all expected fields
    assert task_node["name"] == "test-task"
    assert task_node["description"] == "This is a test task description"
    assert task_node["status"] == "pending"
    assert task_node["priority"] == 5
    assert "completed_at" in task_node
    assert "is_available" in task_node


def test_graph_json_multiple_tasks_with_descriptions(mock_db_path):
    """Test that graph_json includes descriptions for multiple tasks."""
    # Add multiple tasks
    TaskRepository.add_task("task-1", "Description for task 1", priority=1)
    TaskRepository.add_task("task-2", "Description for task 2", priority=2)
    TaskRepository.add_task("task-3", "Description for task 3", priority=3)

    # Get the graph JSON
    graph = get_graph_json(mock_db_path)

    # Verify all tasks have descriptions
    nodes = graph["nodes"]
    assert len(nodes) == 3

    descriptions = {node["name"]: node["description"] for node in nodes}
    assert descriptions["task-1"] == "Description for task 1"
    assert descriptions["task-2"] == "Description for task 2"
    assert descriptions["task-3"] == "Description for task 3"


def test_graph_json_with_dependencies_includes_descriptions(mock_db_path):
    """Test that graph_json includes descriptions when tasks have dependencies."""
    # Create tasks with dependencies
    TaskRepository.add_task("base-task", "Base task description")
    TaskRepository.add_task("dependent-task", "Dependent task description")

    DependencyRepository.add_dependency("dependent-task", "base-task")

    # Get the graph JSON
    graph = get_graph_json(mock_db_path)

    # Verify nodes have descriptions
    nodes = graph["nodes"]
    assert len(nodes) == 2

    for node in nodes:
        assert "description" in node
        if node["name"] == "base-task":
            assert node["description"] == "Base task description"
        elif node["name"] == "dependent-task":
            assert node["description"] == "Dependent task description"

    # Verify edges
    edges = graph["edges"]
    assert len(edges) == 1
    assert edges[0]["from"] == "dependent-task"
    assert edges[0]["to"] == "base-task"


def test_graph_json_description_with_special_characters(mock_db_path):
    """Test that descriptions with special characters are properly encoded in JSON."""
    # Add task with special characters
    TaskRepository.add_task(
        name="special-task",
        description='Description with "quotes", newlines\n, and unicode: 你好 🎉',
    )

    # Get the graph JSON
    graph = get_graph_json(mock_db_path)

    # Verify the description is properly encoded
    nodes = graph["nodes"]
    assert len(nodes) == 1

    task_node = nodes[0]
    assert '"quotes"' in task_node["description"]
    assert "你好" in task_node["description"]
    assert "🎉" in task_node["description"]


def test_graph_json_empty_database(mock_db_path):
    """Test that graph_json works with an empty database."""
    # Get the graph JSON with no tasks
    graph = get_graph_json(mock_db_path)

    # Should have empty arrays
    assert graph["nodes"] == []
    assert graph["edges"] == []


def test_graph_json_is_available_field_with_descriptions(mock_db_path):
    """Test that is_available field works correctly along with descriptions."""
    # Create a dependency chain
    TaskRepository.add_task(
        "available-task", "Available task description", status="pending"
    )
    TaskRepository.add_task(
        "blocked-task", "Blocked task description", status="pending"
    )

    DependencyRepository.add_dependency("blocked-task", "available-task")

    # Get the graph JSON
    graph = get_graph_json(mock_db_path)

    # Verify is_available flags
    nodes = graph["nodes"]
    for node in nodes:
        if node["name"] == "available-task":
            assert node["is_available"] == 1
            assert node["description"] == "Available task description"
        elif node["name"] == "blocked-task":
            assert node["is_available"] == 0
            assert node["description"] == "Blocked task description"


def test_graph_json_completed_task_with_description(mock_db_path):
    """Test that completed tasks show their descriptions in graph_json."""
    # Add a task and then mark it as completed (to trigger the timestamp)
    TaskRepository.add_task(
        name="completed-task",
        description="Completed task description",
        status="pending",
    )

    # Update to completed status to trigger the completed_at timestamp
    TaskRepository.update_task(
        name="completed-task",
        status="completed",
    )

    # Get the graph JSON
    graph = get_graph_json(mock_db_path)

    # Verify the completed task has description
    nodes = graph["nodes"]
    assert len(nodes) == 1

    task_node = nodes[0]
    assert task_node["name"] == "completed-task"
    assert task_node["description"] == "Completed task description"
    assert task_node["status"] == "completed"
    assert task_node["completed_at"] is not None


def test_graph_json_long_description(mock_db_path):
    """Test that long descriptions are properly included in graph_json."""
    # Add task with very long description
    long_description = "A" * 1000  # 1000 character description

    TaskRepository.add_task("long-desc-task", long_description)

    # Get the graph JSON
    graph = get_graph_json(mock_db_path)

    # Verify long description is included
    nodes = graph["nodes"]
    assert len(nodes) == 1

    task_node = nodes[0]
    assert task_node["description"] == long_description
    assert len(task_node["description"]) == 1000
