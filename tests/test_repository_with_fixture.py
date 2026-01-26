"""
Example tests demonstrating how to use the test_db fixture with repository classes.
"""

from pathlib import Path

import pytest

from tasktree_mcp.database import TaskRepository, DependencyRepository


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


def test_task_repository_add_task(mock_db_path):
    """Test adding a task using TaskRepository with test database."""
    task = TaskRepository.add_task(
        name="test-task", description="A test task", priority=5, status="pending"
    )

    assert task.name == "test-task"
    assert task.description == "A test task"
    assert task.priority == 5
    assert task.status == "pending"
    assert task.created_at is not None


def test_task_repository_list_tasks(mock_db_path):
    """Test listing tasks using TaskRepository."""
    # Add some test tasks
    TaskRepository.add_task("task1", "First task", priority=1)
    TaskRepository.add_task("task2", "Second task", priority=2)
    TaskRepository.add_task("task3", "Third task", priority=3)

    # List all tasks
    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 3

    # Tasks should be ordered by priority (descending)
    assert tasks[0].name == "task3"
    assert tasks[1].name == "task2"
    assert tasks[2].name == "task1"


def test_task_repository_get_task(mock_db_path):
    """Test getting a specific task."""
    # Add a task
    TaskRepository.add_task("my-task", "My test task")

    # Retrieve it
    task = TaskRepository.get_task("my-task")
    assert task is not None
    assert task.name == "my-task"
    assert task.description == "My test task"

    # Try to get non-existent task
    non_existent = TaskRepository.get_task("does-not-exist")
    assert non_existent is None


def test_task_repository_update_task(mock_db_path):
    """Test updating a task."""
    # Add a task
    TaskRepository.add_task("update-me", "Original description", priority=1)

    # Update it
    updated = TaskRepository.update_task(
        "update-me", description="Updated description", priority=5, status="in_progress"
    )

    assert updated is not None
    assert updated.description == "Updated description"
    assert updated.priority == 5
    assert updated.status == "in_progress"
    assert updated.started_at is not None  # Trigger should set this


def test_task_repository_delete_task(mock_db_path):
    """Test deleting a task."""
    # Add a task
    TaskRepository.add_task("delete-me", "Task to delete")

    # Verify it exists
    assert TaskRepository.get_task("delete-me") is not None

    # Delete it
    deleted = TaskRepository.delete_task("delete-me")
    assert deleted is True

    # Verify it's gone
    assert TaskRepository.get_task("delete-me") is None


def test_dependency_repository_add_dependency(mock_db_path):
    """Test adding a dependency between tasks."""
    # Add two tasks
    TaskRepository.add_task("task-a", "First task")
    TaskRepository.add_task("task-b", "Second task")

    # Create dependency: task-b depends on task-a
    dep = DependencyRepository.add_dependency("task-b", "task-a")

    assert dep.task_name == "task-b"
    assert dep.depends_on_task_name == "task-a"


def test_dependency_repository_list_dependencies(mock_db_path):
    """Test listing dependencies."""
    # Set up tasks
    TaskRepository.add_task("task-1", "Task 1")
    TaskRepository.add_task("task-2", "Task 2")
    TaskRepository.add_task("task-3", "Task 3")

    # Create dependencies
    DependencyRepository.add_dependency("task-2", "task-1")
    DependencyRepository.add_dependency("task-3", "task-1")
    DependencyRepository.add_dependency("task-3", "task-2")

    # List all dependencies
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 3


def test_dependency_repository_get_available_tasks(mock_db_path):
    """Test getting available tasks (no uncompleted dependencies)."""
    # Set up a dependency chain
    TaskRepository.add_task("base", "Base task", status="completed")
    TaskRepository.add_task("middle", "Middle task", status="pending")
    TaskRepository.add_task("top", "Top task", status="pending")

    DependencyRepository.add_dependency("middle", "base")
    DependencyRepository.add_dependency("top", "middle")

    # Only 'middle' should be available (base is completed, top depends on middle)
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "middle"

    # Complete middle task
    TaskRepository.update_task("middle", status="completed")

    # Now 'top' should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "top"


def test_database_isolation_between_tests(mock_db_path):
    """Test that database is isolated - this test should start with empty db."""
    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 0  # Should be empty, not affected by previous tests
