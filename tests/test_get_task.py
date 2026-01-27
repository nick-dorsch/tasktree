"""
Tests for the get_task tool including valid and invalid task names.
"""

from pathlib import Path

import pytest

from tasktree_mcp.database import TaskRepository


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


def test_get_task_valid_task(mock_db_path):
    """Test getting a task that exists in the database."""
    # Create a task
    TaskRepository.add_task(
        name="existing-task",
        description="A task that exists",
        priority=5,
    )

    # Get the task
    task = TaskRepository.get_task("existing-task")

    # Verify the task was retrieved
    assert task is not None
    assert task.name == "existing-task"
    assert task.description == "A task that exists"
    assert task.priority == 5


def test_get_task_nonexistent_task(mock_db_path):
    """Test getting a task that does not exist returns None."""
    # Try to get a task that doesn't exist
    task = TaskRepository.get_task("nonexistent-task")

    # Should return None
    assert task is None


def test_get_task_empty_string(mock_db_path):
    """Test that getting a task with empty string name raises ValueError."""
    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.get_task("")


def test_get_task_whitespace_only(mock_db_path):
    """Test that getting a task with whitespace-only name raises ValueError."""
    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.get_task("   ")


def test_get_task_with_all_fields(mock_db_path):
    """Test getting a task with all fields populated."""
    # Create a task with all fields
    TaskRepository.add_task(
        name="full-task",
        description="Complete description",
        priority=8,
        status="in_progress",
        specification="Detailed implementation notes",
    )

    # Get the task
    task = TaskRepository.get_task("full-task")

    # Verify all fields are present and correct
    assert task is not None
    assert task.name == "full-task"
    assert task.description == "Complete description"
    assert task.priority == 8
    assert task.status == "in_progress"
    assert task.specification == "Detailed implementation notes"
    assert hasattr(task, "created_at")
    assert hasattr(task, "started_at")
    assert hasattr(task, "completed_at")


def test_get_task_with_minimal_fields(mock_db_path):
    """Test getting a task with minimal fields (defaults)."""
    # Create a task with minimal parameters
    TaskRepository.add_task(
        name="minimal-task",
        description="Minimal description",
    )

    # Get the task
    task = TaskRepository.get_task("minimal-task")

    # Verify defaults are applied
    assert task is not None
    assert task.name == "minimal-task"
    assert task.description == "Minimal description"
    assert task.priority == 0
    assert task.status == "pending"
    assert task.specification == "Minimal description"


def test_get_task_immediately_after_creation(mock_db_path):
    """Test that get_task works immediately after creating a task."""
    # Create and immediately retrieve
    created = TaskRepository.add_task(
        name="immediate-task",
        description="Created just now",
        priority=7,
    )

    retrieved = TaskRepository.get_task("immediate-task")

    # Should match the created task
    assert retrieved is not None
    assert retrieved.name == created.name
    assert retrieved.description == created.description
    assert retrieved.priority == created.priority
    assert retrieved.created_at == created.created_at


def test_get_task_after_update(mock_db_path):
    """Test getting a task after it has been updated."""
    # Create a task
    TaskRepository.add_task(
        name="update-task",
        description="Original description",
        priority=3,
    )

    # Update the task
    TaskRepository.update_task(
        name="update-task",
        description="Updated description",
        priority=7,
    )

    # Get the task
    task = TaskRepository.get_task("update-task")

    # Should have updated values
    assert task is not None
    assert task.description == "Updated description"
    assert task.priority == 7


def test_get_task_completed_task(mock_db_path):
    """Test getting a completed task."""
    # Create and complete a task
    TaskRepository.add_task(
        name="completed-task",
        description="This task is done",
    )
    TaskRepository.complete_task("completed-task")

    # Get the task
    task = TaskRepository.get_task("completed-task")

    # Should be retrievable and marked as completed
    assert task is not None
    assert task.status == "completed"
    assert task.completed_at is not None


def test_get_task_multiple_tasks_exist(mock_db_path):
    """Test getting a specific task when multiple tasks exist."""
    # Create multiple tasks
    for i in range(5):
        TaskRepository.add_task(
            name=f"task-{i}",
            description=f"Task number {i}",
            priority=i,
        )

    # Get a specific task
    task = TaskRepository.get_task("task-2")

    # Should get the correct task
    assert task is not None
    assert task.name == "task-2"
    assert task.description == "Task number 2"
    assert task.priority == 2


def test_get_task_after_delete_returns_none(mock_db_path):
    """Test that getting a deleted task returns None."""
    # Create a task
    TaskRepository.add_task(
        name="delete-task",
        description="To be deleted",
    )

    # Verify it exists
    task = TaskRepository.get_task("delete-task")
    assert task is not None

    # Delete the task
    TaskRepository.delete_task("delete-task")

    # Try to get it again
    task = TaskRepository.get_task("delete-task")
    assert task is None
