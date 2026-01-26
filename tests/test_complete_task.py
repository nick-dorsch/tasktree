"""
Tests for complete_task tool.
"""

from pathlib import Path

import pytest

import tasktree_mcp.database as db
from tasktree_mcp.database import TaskRepository


def test_complete_task_success(test_db: Path, monkeypatch):
    """Test completing a task successfully."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task
    task = TaskRepository.add_task(
        name="test-task", description="Test task", priority=5, status="in_progress"
    )
    assert task["status"] == "in_progress"
    assert task["completed_at"] is None

    # Complete the task
    completed_task = TaskRepository.complete_task("test-task")

    assert completed_task is not None
    assert completed_task["name"] == "test-task"
    assert completed_task["status"] == "completed"
    assert completed_task["completed_at"] is not None


def test_complete_task_from_pending(test_db: Path, monkeypatch):
    """Test completing a task that is in pending status."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a pending task
    task = TaskRepository.add_task(
        name="pending-task", description="Pending task", status="pending"
    )
    assert task["status"] == "pending"

    # Complete the task
    completed_task = TaskRepository.complete_task("pending-task")

    assert completed_task is not None
    assert completed_task["status"] == "completed"
    assert completed_task["completed_at"] is not None


def test_complete_task_nonexistent(test_db: Path, monkeypatch):
    """Test completing a task that doesn't exist."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    result = TaskRepository.complete_task("nonexistent-task")
    assert result is None


def test_complete_task_empty_name(test_db: Path, monkeypatch):
    """Test completing a task with empty name."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.complete_task("")


def test_complete_task_whitespace_name(test_db: Path, monkeypatch):
    """Test completing a task with whitespace-only name."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.complete_task("   ")


def test_complete_task_sets_completed_at_timestamp(test_db: Path, monkeypatch):
    """Test that completing a task sets the completed_at timestamp and preserves started_at."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create and start a task
    TaskRepository.add_task(
        name="timestamp-task", description="Task for timestamp test"
    )
    TaskRepository.update_task(name="timestamp-task", status="in_progress")

    # Get the task before completion
    task_before = TaskRepository.get_task("timestamp-task")
    assert task_before["completed_at"] is None
    assert task_before["started_at"] is not None

    # Complete the task
    completed_task = TaskRepository.complete_task("timestamp-task")

    assert completed_task["completed_at"] is not None
    # started_at should be preserved for audit trail
    assert completed_task["started_at"] is not None


def test_complete_task_twice(test_db: Path, monkeypatch):
    """Test completing a task that is already completed."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create and complete a task
    TaskRepository.add_task(name="already-done", description="Already completed")
    TaskRepository.complete_task("already-done")

    # Complete it again
    second_completion = TaskRepository.complete_task("already-done")

    assert second_completion is not None
    assert second_completion["status"] == "completed"
    # The timestamp might be the same or different depending on trigger behavior
    assert second_completion["completed_at"] is not None


def test_complete_task_with_dependencies(test_db: Path, monkeypatch):
    """Test completing a task that has dependent tasks."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create tasks with dependencies
    TaskRepository.add_task(
        name="dependency-task", description="Task that others depend on"
    )
    TaskRepository.add_task(
        name="dependent-task", description="Task that depends on another"
    )

    # Add dependency
    from tasktree_mcp.database import DependencyRepository

    DependencyRepository.add_dependency(
        task_name="dependent-task", depends_on_task_name="dependency-task"
    )

    # Complete the dependency
    completed = TaskRepository.complete_task("dependency-task")

    assert completed is not None
    assert completed["status"] == "completed"

    # Verify the dependent task is now available
    available = DependencyRepository.get_available_tasks()
    available_names = [t["name"] for t in available]
    assert "dependent-task" in available_names
