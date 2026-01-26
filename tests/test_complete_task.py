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
    assert task.status == "in_progress"

    # Complete the task
    completed_task = TaskRepository.complete_task("test-task")

    assert completed_task is not None
    assert completed_task.name == "test-task"
    assert completed_task.status == "completed"


def test_complete_task_from_pending(test_db: Path, monkeypatch):
    """Test completing a task that is in pending status."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a pending task
    task = TaskRepository.add_task(
        name="pending-task", description="Pending task", status="pending"
    )
    assert task.status == "pending"

    # Complete the task
    completed_task = TaskRepository.complete_task("pending-task")

    assert completed_task is not None
    assert completed_task.status == "completed"


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


def test_complete_task_twice(test_db: Path, monkeypatch):
    """Test completing a task that is already completed."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create and complete a task
    TaskRepository.add_task(name="already-done", description="Already completed")
    TaskRepository.complete_task("already-done")

    # Complete it again
    second_completion = TaskRepository.complete_task("already-done")

    assert second_completion is not None
    assert second_completion.status == "completed"


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
    assert completed.status == "completed"

    # Verify the dependent task is now available
    available = DependencyRepository.get_available_tasks()
    available_names = [t.name for t in available]
    assert "dependent-task" in available_names
