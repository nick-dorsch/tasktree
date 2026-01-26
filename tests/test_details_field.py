"""
Tests for the details field in add_task and update_task functionality.
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


def test_add_task_with_details(mock_db_path):
    """Test adding a task with details parameter."""
    task = TaskRepository.add_task(
        name="task-with-details",
        description="A test task",
        priority=5,
        status="pending",
        details="These are detailed implementation notes for the task",
    )

    assert task.name == "task-with-details"
    assert task.description == "A test task"
    assert task.details == "These are detailed implementation notes for the task"
    assert task.priority == 5
    assert task.status == "pending"


def test_add_task_without_details(mock_db_path):
    """Test adding a task without details parameter (should default to None)."""
    task = TaskRepository.add_task(
        name="task-without-details",
        description="A test task",
        priority=3,
        status="pending",
    )

    assert task.name == "task-without-details"
    assert task.description == "A test task"
    assert task.details is None
    assert task.priority == 3


def test_add_task_with_empty_details(mock_db_path):
    """Test adding a task with empty string details."""
    task = TaskRepository.add_task(
        name="task-empty-details",
        description="A test task",
        details="",
    )

    assert task.name == "task-empty-details"
    assert task.details == ""


def test_update_task_add_details(mock_db_path):
    """Test updating a task to add details."""
    # Add a task without details
    TaskRepository.add_task(
        name="update-add-details",
        description="Original description",
    )

    # Update to add details
    updated = TaskRepository.update_task(
        name="update-add-details",
        details="New detailed implementation notes",
    )

    assert updated is not None
    assert updated.details == "New detailed implementation notes"
    assert updated.description == "Original description"


def test_update_task_modify_details(mock_db_path):
    """Test updating a task to modify existing details."""
    # Add a task with details
    TaskRepository.add_task(
        name="update-modify-details",
        description="A task",
        details="Original details",
    )

    # Update the details
    updated = TaskRepository.update_task(
        name="update-modify-details",
        details="Updated details",
    )

    assert updated is not None
    assert updated.details == "Updated details"


def test_update_task_clear_details(mock_db_path):
    """Test updating a task to clear details."""
    # Add a task with details
    TaskRepository.add_task(
        name="update-clear-details",
        description="A task",
        details="Some details",
    )

    # Update to clear details (set to empty string)
    updated = TaskRepository.update_task(
        name="update-clear-details",
        details="",
    )

    assert updated is not None
    assert updated.details == ""


def test_update_task_multiple_fields_including_details(mock_db_path):
    """Test updating multiple fields including details."""
    # Add a task
    TaskRepository.add_task(
        name="update-multiple",
        description="Original description",
        priority=1,
        details="Original details",
    )

    # Update multiple fields
    updated = TaskRepository.update_task(
        name="update-multiple",
        description="New description",
        priority=8,
        status="in_progress",
        details="New details",
    )

    assert updated is not None
    assert updated.description == "New description"
    assert updated.priority == 8
    assert updated.status == "in_progress"
    assert updated.details == "New details"
    assert updated.started_at is not None  # Trigger should set this


def test_update_task_without_details_preserves_existing(mock_db_path):
    """Test that updating without specifying details preserves existing details."""
    # Add a task with details
    TaskRepository.add_task(
        name="preserve-details",
        description="Original description",
        details="Important details",
    )

    # Update other fields without touching details
    updated = TaskRepository.update_task(
        name="preserve-details",
        description="New description",
        priority=7,
    )

    assert updated is not None
    assert updated.description == "New description"
    assert updated.priority == 7
    assert updated.details == "Important details"  # Should be preserved


def test_get_task_returns_details(mock_db_path):
    """Test that get_task returns the details field."""
    # Add a task with details
    TaskRepository.add_task(
        name="get-with-details",
        description="A task",
        details="Task details",
    )

    # Retrieve the task
    task = TaskRepository.get_task("get-with-details")

    assert task is not None
    assert task.details == "Task details"


def test_list_tasks_includes_details(mock_db_path):
    """Test that list_tasks includes the details field."""
    # Add tasks with varying details
    TaskRepository.add_task(
        name="task1",
        description="First task",
        details="Details for task 1",
    )
    TaskRepository.add_task(
        name="task2",
        description="Second task",
        details=None,
    )
    TaskRepository.add_task(
        name="task3",
        description="Third task",
        details="",
    )

    # List all tasks
    tasks = TaskRepository.list_tasks()

    assert len(tasks) == 3

    # Find each task and verify details
    task1 = next(t for t in tasks if t.name == "task1")
    assert task1.details == "Details for task 1"

    task2 = next(t for t in tasks if t.name == "task2")
    assert task2.details is None

    task3 = next(t for t in tasks if t.name == "task3")
    assert task3.details == ""
