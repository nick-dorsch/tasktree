"""
Tests for the list_tasks tool including status/priority filtering and ordering.
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


def test_list_tasks_empty_database(mock_db_path):
    """Test listing tasks when the database is empty."""
    tasks = TaskRepository.list_tasks()
    assert tasks == []
    assert len(tasks) == 0


def test_list_tasks_single_task(mock_db_path):
    """Test listing tasks with a single task in the database."""
    TaskRepository.add_task("single-task", "A single task", priority=5)

    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "single-task"
    assert tasks[0]["description"] == "A single task"
    assert tasks[0]["priority"] == 5


def test_list_tasks_multiple_tasks(mock_db_path):
    """Test listing multiple tasks."""
    TaskRepository.add_task("task-1", "First task", priority=1)
    TaskRepository.add_task("task-2", "Second task", priority=2)
    TaskRepository.add_task("task-3", "Third task", priority=3)

    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 3


def test_list_tasks_ordering_by_priority_descending(mock_db_path):
    """Test that tasks are ordered by priority in descending order."""
    TaskRepository.add_task("low", "Low priority", priority=1)
    TaskRepository.add_task("high", "High priority", priority=10)
    TaskRepository.add_task("mid", "Mid priority", priority=5)

    tasks = TaskRepository.list_tasks()

    # Should be ordered by priority descending
    assert tasks[0]["name"] == "high"
    assert tasks[0]["priority"] == 10
    assert tasks[1]["name"] == "mid"
    assert tasks[1]["priority"] == 5
    assert tasks[2]["name"] == "low"
    assert tasks[2]["priority"] == 1


def test_list_tasks_ordering_by_created_at_when_priority_same(mock_db_path):
    """Test that tasks with same priority are ordered by created_at ascending."""
    # Add tasks with same priority in specific order
    TaskRepository.add_task("first", "First created", priority=5)
    TaskRepository.add_task("second", "Second created", priority=5)
    TaskRepository.add_task("third", "Third created", priority=5)

    tasks = TaskRepository.list_tasks()

    # Should be ordered by created_at ascending when priority is same
    assert tasks[0]["name"] == "first"
    assert tasks[1]["name"] == "second"
    assert tasks[2]["name"] == "third"


def test_list_tasks_filter_by_status_pending(mock_db_path):
    """Test filtering tasks by status='pending'."""
    TaskRepository.add_task("pending-1", "Pending task 1", status="pending")
    TaskRepository.add_task("pending-2", "Pending task 2", status="pending")
    TaskRepository.add_task("in-progress-1", "In progress task", status="in_progress")
    TaskRepository.add_task("completed-1", "Completed task", status="completed")

    tasks = TaskRepository.list_tasks(status="pending")

    assert len(tasks) == 2
    assert all(task["status"] == "pending" for task in tasks)
    assert {task["name"] for task in tasks} == {"pending-1", "pending-2"}


def test_list_tasks_filter_by_status_in_progress(mock_db_path):
    """Test filtering tasks by status='in_progress'."""
    TaskRepository.add_task("pending-1", "Pending task", status="pending")
    TaskRepository.add_task("in-progress-1", "In progress 1", status="in_progress")
    TaskRepository.add_task("in-progress-2", "In progress 2", status="in_progress")
    TaskRepository.add_task("completed-1", "Completed task", status="completed")

    tasks = TaskRepository.list_tasks(status="in_progress")

    assert len(tasks) == 2
    assert all(task["status"] == "in_progress" for task in tasks)


def test_list_tasks_filter_by_status_completed(mock_db_path):
    """Test filtering tasks by status='completed'."""
    TaskRepository.add_task("pending-1", "Pending task", status="pending")
    TaskRepository.add_task("completed-1", "Completed 1", status="completed")
    TaskRepository.add_task("completed-2", "Completed 2", status="completed")
    TaskRepository.add_task("completed-3", "Completed 3", status="completed")

    tasks = TaskRepository.list_tasks(status="completed")

    assert len(tasks) == 3
    assert all(task["status"] == "completed" for task in tasks)


def test_list_tasks_filter_by_priority_min(mock_db_path):
    """Test filtering tasks by minimum priority."""
    TaskRepository.add_task("low", "Low priority", priority=2)
    TaskRepository.add_task("mid", "Mid priority", priority=5)
    TaskRepository.add_task("high", "High priority", priority=8)
    TaskRepository.add_task("max", "Max priority", priority=10)

    tasks = TaskRepository.list_tasks(priority_min=5)

    assert len(tasks) == 3
    assert all(task["priority"] >= 5 for task in tasks)
    assert {task["name"] for task in tasks} == {"mid", "high", "max"}


def test_list_tasks_filter_by_priority_min_zero(mock_db_path):
    """Test filtering with priority_min=0 returns all tasks."""
    TaskRepository.add_task("zero", "Zero priority", priority=0)
    TaskRepository.add_task("five", "Five priority", priority=5)
    TaskRepository.add_task("ten", "Ten priority", priority=10)

    tasks = TaskRepository.list_tasks(priority_min=0)

    assert len(tasks) == 3
    assert all(task["priority"] >= 0 for task in tasks)


def test_list_tasks_filter_by_priority_min_boundary(mock_db_path):
    """Test filtering with priority_min at exact boundary."""
    TaskRepository.add_task("below", "Below threshold", priority=4)
    TaskRepository.add_task("exactly", "Exactly threshold", priority=5)
    TaskRepository.add_task("above", "Above threshold", priority=6)

    tasks = TaskRepository.list_tasks(priority_min=5)

    assert len(tasks) == 2
    assert all(task["priority"] >= 5 for task in tasks)
    assert {task["name"] for task in tasks} == {"exactly", "above"}


def test_list_tasks_filter_by_status_and_priority(mock_db_path):
    """Test filtering by both status and priority_min."""
    TaskRepository.add_task("pending-low", "Pending low", status="pending", priority=2)
    TaskRepository.add_task(
        "pending-high", "Pending high", status="pending", priority=8
    )
    TaskRepository.add_task(
        "completed-low", "Completed low", status="completed", priority=2
    )
    TaskRepository.add_task(
        "completed-high", "Completed high", status="completed", priority=8
    )

    tasks = TaskRepository.list_tasks(status="pending", priority_min=5)

    assert len(tasks) == 1
    assert tasks[0]["name"] == "pending-high"
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["priority"] == 8


def test_list_tasks_filter_status_no_matches(mock_db_path):
    """Test filtering by status with no matching tasks."""
    TaskRepository.add_task("pending-1", "Pending task", status="pending")
    TaskRepository.add_task("pending-2", "Pending task 2", status="pending")

    tasks = TaskRepository.list_tasks(status="completed")

    assert tasks == []
    assert len(tasks) == 0


def test_list_tasks_filter_priority_min_no_matches(mock_db_path):
    """Test filtering by priority_min with no matching tasks."""
    TaskRepository.add_task("low-1", "Low priority 1", priority=1)
    TaskRepository.add_task("low-2", "Low priority 2", priority=2)

    tasks = TaskRepository.list_tasks(priority_min=8)

    assert tasks == []
    assert len(tasks) == 0


def test_list_tasks_filter_combined_no_matches(mock_db_path):
    """Test filtering by both status and priority with no matches."""
    TaskRepository.add_task("pending-low", "Pending low", status="pending", priority=2)
    TaskRepository.add_task(
        "completed-high", "Completed high", status="completed", priority=8
    )

    tasks = TaskRepository.list_tasks(status="pending", priority_min=8)

    assert tasks == []


def test_list_tasks_ordering_with_status_filter(mock_db_path):
    """Test that ordering is maintained when filtering by status."""
    TaskRepository.add_task("pending-low", "Pending low", status="pending", priority=1)
    TaskRepository.add_task("pending-mid", "Pending mid", status="pending", priority=5)
    TaskRepository.add_task(
        "pending-high", "Pending high", status="pending", priority=10
    )
    TaskRepository.add_task(
        "completed-1", "Completed task", status="completed", priority=7
    )

    tasks = TaskRepository.list_tasks(status="pending")

    # Should be ordered by priority descending
    assert len(tasks) == 3
    assert tasks[0]["name"] == "pending-high"
    assert tasks[1]["name"] == "pending-mid"
    assert tasks[2]["name"] == "pending-low"


def test_list_tasks_ordering_with_priority_filter(mock_db_path):
    """Test that ordering is maintained when filtering by priority_min."""
    TaskRepository.add_task("high-1", "High priority 1", priority=10)
    TaskRepository.add_task("high-2", "High priority 2", priority=8)
    TaskRepository.add_task("mid", "Mid priority", priority=5)
    TaskRepository.add_task("low", "Low priority", priority=2)

    tasks = TaskRepository.list_tasks(priority_min=5)

    # Should be ordered by priority descending
    assert len(tasks) == 3
    assert tasks[0]["priority"] == 10
    assert tasks[1]["priority"] == 8
    assert tasks[2]["priority"] == 5


def test_list_tasks_all_fields_present(mock_db_path):
    """Test that all task fields are present in the returned tasks."""
    TaskRepository.add_task(
        name="full-task",
        description="Full description",
        priority=7,
        status="in_progress",
        details="Implementation details",
    )

    tasks = TaskRepository.list_tasks()

    assert len(tasks) == 1
    task = tasks[0]

    # Verify all expected fields are present
    assert "name" in task
    assert "description" in task
    assert "details" in task
    assert "priority" in task
    assert "status" in task
    assert "created_at" in task
    assert "started_at" in task
    assert "completed_at" in task

    # Verify field values
    assert task["name"] == "full-task"
    assert task["description"] == "Full description"
    assert task["details"] == "Implementation details"
    assert task["priority"] == 7
    assert task["status"] == "in_progress"


def test_list_tasks_with_different_statuses(mock_db_path):
    """Test listing tasks with various status values."""
    TaskRepository.add_task("blocked", "Blocked task", status="blocked")
    TaskRepository.add_task("pending", "Pending task", status="pending")
    TaskRepository.add_task("in-progress", "In progress", status="in_progress")
    TaskRepository.add_task("completed", "Completed", status="completed")

    tasks = TaskRepository.list_tasks()

    assert len(tasks) == 4
    statuses = {task["status"] for task in tasks}
    assert statuses == {"blocked", "pending", "in_progress", "completed"}


def test_list_tasks_large_dataset(mock_db_path):
    """Test listing tasks with a large number of tasks."""
    # Create 100 tasks
    for i in range(100):
        TaskRepository.add_task(
            name=f"task-{i:03d}",
            description=f"Task number {i}",
            priority=i % 11,  # Priority from 0 to 10
            status="pending" if i % 2 == 0 else "in_progress",
        )

    tasks = TaskRepository.list_tasks()

    assert len(tasks) == 100

    # Verify ordering (priority descending)
    for i in range(len(tasks) - 1):
        assert tasks[i]["priority"] >= tasks[i + 1]["priority"]


def test_list_tasks_filter_large_dataset_by_status(mock_db_path):
    """Test filtering a large dataset by status."""
    for i in range(100):
        status = ["pending", "in_progress", "completed"][i % 3]
        TaskRepository.add_task(
            name=f"task-{i:03d}", description=f"Task {i}", status=status
        )

    pending_tasks = TaskRepository.list_tasks(status="pending")
    in_progress_tasks = TaskRepository.list_tasks(status="in_progress")
    completed_tasks = TaskRepository.list_tasks(status="completed")

    # Should have roughly equal distribution
    assert len(pending_tasks) + len(in_progress_tasks) + len(completed_tasks) == 100
    assert 30 <= len(pending_tasks) <= 35
    assert 30 <= len(in_progress_tasks) <= 35
    assert 30 <= len(completed_tasks) <= 35


def test_list_tasks_filter_large_dataset_by_priority(mock_db_path):
    """Test filtering a large dataset by priority."""
    for i in range(100):
        TaskRepository.add_task(
            name=f"task-{i:03d}", description=f"Task {i}", priority=i % 11
        )

    high_priority_tasks = TaskRepository.list_tasks(priority_min=7)

    # Should include tasks with priority 7, 8, 9, 10
    expected_count = sum(1 for i in range(100) if (i % 11) >= 7)
    assert len(high_priority_tasks) == expected_count
    assert all(task["priority"] >= 7 for task in high_priority_tasks)


def test_list_tasks_none_parameters(mock_db_path):
    """Test that passing None for optional parameters works correctly."""
    TaskRepository.add_task("task-1", "Task 1", priority=5)
    TaskRepository.add_task("task-2", "Task 2", priority=3)

    # Explicitly pass None for both parameters
    tasks = TaskRepository.list_tasks(status=None, priority_min=None)

    assert len(tasks) == 2
    # Should return all tasks ordered by priority
    assert tasks[0]["name"] == "task-1"
    assert tasks[1]["name"] == "task-2"
