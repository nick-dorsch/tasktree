"""
Tests for start_task tool.
"""

from pathlib import Path

import pytest

import tasktree.database as db
from tasktree.database import DependencyRepository, TaskRepository


def test_start_task_success(test_db: Path, monkeypatch):
    """Test starting a task successfully."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a pending task
    task = TaskRepository.add_task(
        name="test-task", description="Test task", priority=5, status="pending"
    )
    assert task.status == "pending"

    # Start the task
    started_task = TaskRepository.update_task(name="test-task", status="in_progress")

    assert started_task is not None
    assert started_task.name == "test-task"
    assert started_task.status == "in_progress"


def test_start_task_from_completed(test_db: Path, monkeypatch):
    """Test starting a task that is already completed."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a completed task
    TaskRepository.add_task(
        name="completed-task", description="Completed task", status="pending"
    )
    TaskRepository.complete_task("completed-task")

    # Get the task to verify it's completed
    completed = TaskRepository.get_task("completed-task")
    assert completed is not None
    assert completed.status == "completed"

    # Start the task (reopen it)
    started_task = TaskRepository.update_task(
        name="completed-task", status="in_progress"
    )

    assert started_task is not None
    assert started_task.status == "in_progress"


def test_start_task_nonexistent(test_db: Path, monkeypatch):
    """Test starting a task that doesn't exist."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    result = TaskRepository.update_task(name="nonexistent-task", status="in_progress")
    assert result is None


def test_start_task_empty_name(test_db: Path, monkeypatch):
    """Test starting a task with empty name."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.update_task(name="", status="in_progress")


def test_start_task_whitespace_name(test_db: Path, monkeypatch):
    """Test starting a task with whitespace-only name."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.update_task(name="   ", status="in_progress")


def test_start_task_preserves_other_fields(test_db: Path, monkeypatch):
    """Test that starting a task preserves description, priority, and specification."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task with specific fields
    original_task = TaskRepository.add_task(
        name="preserve-test",
        description="Original description",
        priority=8,
        specification="Important details",
    )

    # Start the task
    started_task = TaskRepository.update_task(
        name="preserve-test", status="in_progress"
    )

    # Verify all fields are preserved
    assert started_task is not None
    assert started_task.description == original_task.description
    assert started_task.priority == original_task.priority
    assert started_task.specification == original_task.specification
    assert started_task.status == "in_progress"


def test_start_task_with_dependencies(test_db: Path, monkeypatch):
    """Test starting a task that has dependencies."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create tasks with dependencies
    TaskRepository.add_task(
        name="dependency-task", description="Task that others depend on"
    )
    TaskRepository.add_task(
        name="dependent-task", description="Task that depends on another"
    )

    # Add dependency
    DependencyRepository.add_dependency(
        task_name="dependent-task", depends_on_task_name="dependency-task"
    )

    # Start the dependent task (should be allowed even though dependency is not complete)
    started = TaskRepository.update_task(name="dependent-task", status="in_progress")

    assert started is not None
    assert started.status == "in_progress"


def test_start_task_makes_task_unavailable(test_db: Path, monkeypatch):
    """Test that starting a task removes it from available tasks."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a pending task
    TaskRepository.add_task(name="available-task", description="Available task")

    # Verify it's available
    available = DependencyRepository.get_available_tasks()
    available_names = [t.name for t in available]
    assert "available-task" in available_names

    # Start the task
    TaskRepository.update_task(name="available-task", status="in_progress")

    # Verify it's no longer in available tasks
    available_after = DependencyRepository.get_available_tasks()
    available_names_after = [t.name for t in available_after]
    assert "available-task" not in available_names_after
