"""
Tests for the update_task tool including partial updates, specification field updates, and validation.
"""

from pathlib import Path

import pytest

import tasktree.database as db
from tasktree.database import TaskRepository


def test_update_task_description_only(test_db: Path, monkeypatch):
    """Test updating only the description field."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task
    TaskRepository.add_task(
        name="test-task",
        description="Original description",
        priority=5,
        status="pending",
    )

    # Update only description
    updated = TaskRepository.update_task(
        name="test-task",
        description="Updated description",
    )

    assert updated is not None
    assert updated.description == "Updated description"
    assert updated.priority == 5  # Unchanged
    assert updated.status == "pending"  # Unchanged


def test_update_task_priority_only(test_db: Path, monkeypatch):
    """Test updating only the priority field."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task
    TaskRepository.add_task(
        name="priority-task",
        description="Test task",
        priority=3,
    )

    # Update only priority
    updated = TaskRepository.update_task(
        name="priority-task",
        priority=8,
    )

    assert updated is not None
    assert updated.priority == 8
    assert updated.description == "Test task"  # Unchanged


def test_update_task_status_only(test_db: Path, monkeypatch):
    """Test updating only the status field."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task
    TaskRepository.add_task(
        name="status-task",
        description="Test task",
        status="pending",
    )

    # Update only status
    updated = TaskRepository.update_task(
        name="status-task",
        status="in_progress",
    )

    assert updated is not None
    assert updated.status == "in_progress"
    assert updated.started_at is not None  # Trigger should set this


def test_update_task_specification_only(test_db: Path, monkeypatch):
    """Test updating only the specification field."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task without specification
    TaskRepository.add_task(
        name="details-task",
        description="Test task",
    )

    # Update only specification
    updated = TaskRepository.update_task(
        name="details-task",
        specification="New implementation details",
    )

    assert updated is not None
    assert updated.specification == "New implementation details"
    assert updated.description == "Test task"  # Unchanged


def test_update_task_multiple_fields(test_db: Path, monkeypatch):
    """Test updating multiple fields at once."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task
    TaskRepository.add_task(
        name="multi-update",
        description="Original",
        priority=1,
        status="pending",
        specification="Old details",
    )

    # Update multiple fields
    updated = TaskRepository.update_task(
        name="multi-update",
        description="New description",
        priority=9,
        status="in_progress",
        specification="New details",
    )

    assert updated is not None
    assert updated.description == "New description"
    assert updated.priority == 9
    assert updated.status == "in_progress"
    assert updated.specification == "New details"
    assert updated.started_at is not None


def test_update_task_add_specification_to_task_without_specification(
    test_db: Path, monkeypatch
):
    """Test adding specification to a task that didn't have any."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task without specification
    TaskRepository.add_task(
        name="add-details",
        description="Task without details",
    )

    # Add specification
    updated = TaskRepository.update_task(
        name="add-details",
        specification="Newly added details",
    )

    assert updated is not None
    assert updated.specification == "Newly added details"


def test_update_task_modify_existing_specification(test_db: Path, monkeypatch):
    """Test modifying existing specification."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task with specification
    TaskRepository.add_task(
        name="modify-details",
        description="Task with details",
        specification="Original details",
    )

    # Modify specification
    updated = TaskRepository.update_task(
        name="modify-details",
        specification="Modified details",
    )

    assert updated is not None
    assert updated.specification == "Modified details"


def test_update_task_clear_specification(test_db: Path, monkeypatch):
    """Test clearing specification by setting to empty string."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task with specification
    TaskRepository.add_task(
        name="clear-details",
        description="Task with details",
        specification="Some details to clear",
    )

    # Clear specification
    updated = TaskRepository.update_task(
        name="clear-details",
        specification="",
    )

    assert updated is not None
    assert updated.specification == ""


def test_update_task_nonexistent_task(test_db: Path, monkeypatch):
    """Test updating a task that doesn't exist."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    result = TaskRepository.update_task(
        name="nonexistent",
        description="New description",
    )

    assert result is None


def test_update_task_empty_name(test_db: Path, monkeypatch):
    """Test updating with empty task name raises error."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.update_task(
            name="",
            description="New description",
        )


def test_update_task_whitespace_name(test_db: Path, monkeypatch):
    """Test updating with whitespace-only task name raises error."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    with pytest.raises(ValueError, match="Task name cannot be empty"):
        TaskRepository.update_task(
            name="   ",
            description="New description",
        )


def test_update_task_no_fields_specified(test_db: Path, monkeypatch):
    """Test updating with no fields specified returns unchanged task."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create a task
    original = TaskRepository.add_task(
        name="no-update",
        description="Original description",
        priority=5,
    )

    # Update with no fields
    result = TaskRepository.update_task(name="no-update")

    assert result is not None
    assert result.description == original.description
    assert result.priority == original.priority


def test_update_task_preserves_unspecified_fields(test_db: Path, monkeypatch):
    """Test that unspecified fields are preserved during update."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task with all fields
    TaskRepository.add_task(
        name="preserve-test",
        description="Original description",
        priority=7,
        status="pending",
        specification="Original details",
    )

    # Update only priority
    updated = TaskRepository.update_task(
        name="preserve-test",
        priority=9,
    )

    assert updated is not None
    assert updated.priority == 9  # Changed
    assert updated.description == "Original description"  # Preserved
    assert updated.status == "pending"  # Preserved
    assert updated.specification == "Original details"  # Preserved


def test_update_task_status_from_pending_to_completed(test_db: Path, monkeypatch):
    """Test transitioning directly from pending to completed."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create pending task
    TaskRepository.add_task(
        name="skip-in-progress",
        description="Skip in_progress",
        status="pending",
    )

    # Update directly to completed
    updated = TaskRepository.update_task(
        name="skip-in-progress",
        status="completed",
    )

    assert updated is not None
    assert updated.status == "completed"
    assert updated.completed_at is not None
    # started_at might be None since we skipped in_progress


def test_update_task_priority_bounds(test_db: Path, monkeypatch):
    """Test updating priority to minimum and maximum values."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task
    TaskRepository.add_task(
        name="priority-bounds",
        description="Test priority bounds",
        priority=5,
    )

    # Update to minimum
    updated_min = TaskRepository.update_task(
        name="priority-bounds",
        priority=0,
    )
    assert updated_min is not None
    assert updated_min.priority == 0

    # Update to maximum
    updated_max = TaskRepository.update_task(
        name="priority-bounds",
        priority=10,
    )
    assert updated_max is not None
    assert updated_max.priority == 10


def test_update_task_with_long_specification(test_db: Path, monkeypatch):
    """Test updating with very long specification."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task
    TaskRepository.add_task(
        name="long-details",
        description="Task for long details",
    )

    # Update with long specification
    long_specification = "A" * 5000
    updated = TaskRepository.update_task(
        name="long-details",
        specification=long_specification,
    )

    assert updated is not None
    assert updated.specification == long_specification
    assert updated.specification is not None
    assert len(updated.specification) == 5000


def test_update_task_with_unicode_specification(test_db: Path, monkeypatch):
    """Test updating with unicode characters in specification."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task
    TaskRepository.add_task(
        name="unicode-details",
        description="Task for unicode",
    )

    # Update with unicode specification
    updated = TaskRepository.update_task(
        name="unicode-details",
        specification="Unicode: 你好 🚀 café ✨",
    )

    assert updated is not None
    assert updated.specification is not None
    assert "你好" in updated.specification
    assert "🚀" in updated.specification
    assert "✨" in updated.specification


def test_update_task_status_preserves_timestamps(test_db: Path, monkeypatch):
    """Test that updating status preserves existing timestamps."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task and transition through statuses
    TaskRepository.add_task(
        name="timestamp-preserve",
        description="Test timestamp preservation",
        status="pending",
    )

    # Start task
    TaskRepository.update_task(name="timestamp-preserve", status="in_progress")
    started = TaskRepository.get_task("timestamp-preserve")
    assert started is not None
    started_at_original = started.started_at

    # Complete task
    TaskRepository.update_task(name="timestamp-preserve", status="completed")
    completed = TaskRepository.get_task("timestamp-preserve")
    assert completed is not None

    # started_at should be preserved
    assert completed.started_at == started_at_original
    assert completed.completed_at is not None


def test_update_task_different_status_values(test_db: Path, monkeypatch):
    """Test updating to different valid status values."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    TaskRepository.add_task(
        name="status-values",
        description="Test status values",
    )

    # Test each valid status
    for status in ["pending", "in_progress", "completed", "blocked"]:
        updated = TaskRepository.update_task(
            name="status-values",
            status=status,
        )
        assert updated is not None
        assert updated.status == status


def test_update_task_multiple_consecutive_updates(test_db: Path, monkeypatch):
    """Test performing multiple consecutive updates on the same task."""
    monkeypatch.setattr(db, "DB_PATH", test_db)

    # Create task
    TaskRepository.add_task(
        name="consecutive-updates",
        description="Original",
        priority=1,
    )

    # First update
    updated1 = TaskRepository.update_task(
        name="consecutive-updates",
        priority=5,
    )
    assert updated1 is not None
    assert updated1.priority == 5

    # Second update
    updated2 = TaskRepository.update_task(
        name="consecutive-updates",
        description="Updated description",
    )
    assert updated2 is not None
    assert updated2.description == "Updated description"
    assert updated2.priority == 5  # Should be preserved

    # Third update
    updated3 = TaskRepository.update_task(
        name="consecutive-updates",
        specification="Added details",
    )
    assert updated3 is not None
    assert updated3.specification == "Added details"
    assert updated3.description == "Updated description"  # Should be preserved
    assert updated3.priority == 5  # Should be preserved
