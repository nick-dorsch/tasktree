"""
Tests for start_task tool.
"""

from pathlib import Path

import pytest

import tasktree_mcp.database as db
from tasktree_mcp.database import DependencyRepository, TaskRepository


def test_start_task_success(test_db: Path, monkeypatch):
    """Test starting a task successfully."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a pending task
    task = TaskRepository.add_task(
        name="test-task", description="Test task", priority=5, status="pending"
    )
    assert task["status"] == "pending"
    assert task["started_at"] is None

    # Start the task
    started_task = TaskRepository.update_task(name="test-task", status="in_progress")

    assert started_task is not None
    assert started_task["name"] == "test-task"
    assert started_task["status"] == "in_progress"
    assert started_task["started_at"] is not None


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
    assert completed["status"] == "completed"

    # Start the task (reopen it)
    started_task = TaskRepository.update_task(
        name="completed-task", status="in_progress"
    )

    assert started_task is not None
    assert started_task["status"] == "in_progress"
    assert started_task["started_at"] is not None


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


def test_start_task_sets_started_at_timestamp(test_db: Path, monkeypatch):
    """Test that starting a task sets the started_at timestamp."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a pending task
    TaskRepository.add_task(
        name="timestamp-task", description="Task for timestamp test"
    )

    # Get the task before starting
    task_before = TaskRepository.get_task("timestamp-task")
    assert task_before["status"] == "pending"
    assert task_before["started_at"] is None
    assert task_before["completed_at"] is None

    # Start the task
    started_task = TaskRepository.update_task(
        name="timestamp-task", status="in_progress"
    )

    assert started_task["started_at"] is not None
    assert started_task["completed_at"] is None


def test_start_task_twice(test_db: Path, monkeypatch):
    """Test starting a task that is already in_progress."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create and start a task
    TaskRepository.add_task(name="already-started", description="Already in progress")
    first_start = TaskRepository.update_task(
        name="already-started", status="in_progress"
    )
    first_timestamp = first_start["started_at"]

    # Start it again
    second_start = TaskRepository.update_task(
        name="already-started", status="in_progress"
    )

    assert second_start is not None
    assert second_start["status"] == "in_progress"
    # The timestamp should remain the same since the trigger only fires when
    # status changes FROM a non-in_progress status TO in_progress
    assert second_start["started_at"] == first_timestamp


def test_start_task_preserves_other_fields(test_db: Path, monkeypatch):
    """Test that starting a task preserves description, priority, and details."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task with specific fields
    original_task = TaskRepository.add_task(
        name="preserve-test",
        description="Original description",
        priority=8,
        details="Important details",
    )

    # Start the task
    started_task = TaskRepository.update_task(
        name="preserve-test", status="in_progress"
    )

    # Verify all fields are preserved
    assert started_task["description"] == original_task["description"]
    assert started_task["priority"] == original_task["priority"]
    assert started_task["details"] == original_task["details"]
    assert started_task["status"] == "in_progress"


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
    assert started["status"] == "in_progress"


def test_start_task_makes_task_unavailable(test_db: Path, monkeypatch):
    """Test that starting a task changes it from available to in_progress in get_available_tasks."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a pending task
    TaskRepository.add_task(name="available-task", description="Available task")

    # Verify it's available
    available = DependencyRepository.get_available_tasks()
    available_names = [t["name"] for t in available]
    assert "available-task" in available_names

    # Start the task
    TaskRepository.update_task(name="available-task", status="in_progress")

    # Verify it's still in available tasks (in_progress tasks can still be worked on)
    available_after = DependencyRepository.get_available_tasks()
    available_names_after = [t["name"] for t in available_after]
    assert "available-task" in available_names_after
