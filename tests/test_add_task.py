"""
Tests for the add_task tool including validation, duplicate names, details field, and dependencies.
"""

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


def test_add_task_basic(mock_db_path):
    """Test adding a basic task with minimal parameters."""
    task = TaskRepository.add_task(
        name="basic-task",
        description="A basic test task",
    )

    assert task.name == "basic-task"
    assert task.description == "A basic test task"
    assert task.priority == 0
    assert task.status == "pending"
    assert task.details is None
    assert task.tests_required is True
    assert task.created_at is not None


def test_add_task_with_all_parameters(mock_db_path):
    """Test adding a task with all parameters specified."""
    task = TaskRepository.add_task(
        name="full-task",
        description="A task with all parameters",
        priority=8,
        status="in_progress",
        details="Detailed implementation notes",
        tests_required=False,
    )

    assert task.name == "full-task"
    assert task.description == "A task with all parameters"
    assert task.priority == 8
    assert task.status == "in_progress"
    assert task.details == "Detailed implementation notes"
    assert task.tests_required is False


def test_add_task_with_tests_required_flag(mock_db_path):
    """Test adding a task with tests_required flag."""
    task = TaskRepository.add_task(
        name="no-tests-task",
        description="A task without tests",
        tests_required=False,
    )

    assert task.tests_required is False


def test_add_task_with_priority_bounds(mock_db_path):
    """Test adding tasks with minimum and maximum priority values."""
    # Minimum priority
    task_min = TaskRepository.add_task(
        name="min-priority",
        description="Task with minimum priority",
        priority=0,
    )
    assert task_min.priority == 0

    # Maximum priority
    task_max = TaskRepository.add_task(
        name="max-priority",
        description="Task with maximum priority",
        priority=10,
    )
    assert task_max.priority == 10


def test_add_task_with_different_statuses(mock_db_path):
    """Test adding tasks with different valid status values."""
    statuses = ["pending", "in_progress", "completed", "blocked"]

    for status in statuses:
        task = TaskRepository.add_task(
            name=f"task-{status}",
            description=f"Task with {status} status",
            status=status,
        )
        assert task.status == status


def test_add_task_with_details(mock_db_path):
    """Test adding a task with details field."""
    task = TaskRepository.add_task(
        name="task-with-details",
        description="A task",
        details="These are implementation details",
    )

    assert task.details == "These are implementation details"


def test_add_task_with_empty_details(mock_db_path):
    """Test adding a task with empty string details."""
    task = TaskRepository.add_task(
        name="task-empty-details",
        description="A task",
        details="",
    )

    assert task.details == ""


def test_add_task_duplicate_name(mock_db_path):
    """Test that adding a task with duplicate name raises an error."""
    # Add first task
    TaskRepository.add_task(
        name="duplicate-task",
        description="First task",
    )

    # Try to add second task with same name
    with pytest.raises(ValueError, match="already exists"):
        TaskRepository.add_task(
            name="duplicate-task",
            description="Second task",
        )


def test_add_task_creates_timestamps(mock_db_path):
    """Test that add_task creates appropriate timestamps."""
    # Task with pending status
    task_pending = TaskRepository.add_task(
        name="pending-task",
        description="A pending task",
        status="pending",
    )
    assert task_pending.created_at is not None
    assert task_pending.started_at is None
    assert task_pending.completed_at is None

    # Task with in_progress status
    task_in_progress = TaskRepository.add_task(
        name="in-progress-task",
        description="An in-progress task",
        status="in_progress",
    )
    assert task_in_progress.created_at is not None
    # Note: started_at is set by trigger when status changes to in_progress
    # Since we're inserting with that status, we may need to test separately

    # Task with completed status
    task_completed = TaskRepository.add_task(
        name="completed-task",
        description="A completed task",
        status="completed",
    )
    assert task_completed.created_at is not None


def test_add_task_special_characters_in_name(mock_db_path):
    """Test adding a task with special characters in the name."""
    special_names = [
        "task-with-dashes",
        "task_with_underscores",
        "task.with.dots",
        "task:with:colons",
    ]

    for name in special_names:
        task = TaskRepository.add_task(
            name=name,
            description=f"Task with name: {name}",
        )
        assert task.name == name


def test_add_task_long_description(mock_db_path):
    """Test adding a task with a long description."""
    long_desc = "A" * 1000  # 1000 character description

    task = TaskRepository.add_task(
        name="long-desc-task",
        description=long_desc,
    )

    assert task.description == long_desc


def test_add_task_unicode_characters(mock_db_path):
    """Test adding a task with unicode characters."""
    task = TaskRepository.add_task(
        name="unicode-task",
        description="Task with unicode: 你好 🎉 café",
        details="Details with emoji: ✨🚀",
    )

    assert "你好" in task.description
    assert "🎉" in task.description
    assert "✨" in task.details


def test_add_task_ordering(mock_db_path):
    """Test that tasks are returned in correct order (priority desc, created_at asc)."""
    # Add tasks with different priorities
    TaskRepository.add_task("task-low", "Low priority", priority=1)
    TaskRepository.add_task("task-high", "High priority", priority=9)
    TaskRepository.add_task("task-mid", "Mid priority", priority=5)

    # List tasks
    tasks = TaskRepository.list_tasks()

    # Should be ordered by priority (descending)
    assert tasks[0].name == "task-high"
    assert tasks[1].name == "task-mid"
    assert tasks[2].name == "task-low"


def test_add_task_retrieval_after_creation(mock_db_path):
    """Test that a task can be retrieved immediately after creation."""
    created_task = TaskRepository.add_task(
        name="retrieve-task",
        description="Task to retrieve",
        priority=5,
    )

    # Retrieve the task
    retrieved_task = TaskRepository.get_task("retrieve-task")

    # Should match
    assert retrieved_task is not None
    assert retrieved_task.name == created_task.name
    assert retrieved_task.description == created_task.description
    assert retrieved_task.priority == created_task.priority


def test_add_task_with_dependencies_via_tools_wrapper(mock_db_path):
    """Test adding a task with dependencies using the tools wrapper pattern."""
    # First create the dependency tasks
    TaskRepository.add_task("dependency-1", "First dependency")
    TaskRepository.add_task("dependency-2", "Second dependency")

    # Create a task that depends on them
    task = TaskRepository.add_task(
        name="dependent-task",
        description="A task with dependencies",
    )

    # Add dependencies separately (simulating tool behavior)
    DependencyRepository.add_dependency("dependent-task", "dependency-1")
    DependencyRepository.add_dependency("dependent-task", "dependency-2")

    # Verify dependencies were created
    deps = DependencyRepository.list_dependencies("dependent-task")
    assert len(deps) == 2

    # Verify the task exists
    assert task.name == "dependent-task"


def test_add_task_nonexistent_dependency_validation(mock_db_path):
    """Test that adding dependencies to non-existent tasks is handled."""
    # Create a task
    TaskRepository.add_task("task-a", "Task A")

    # Try to add dependency on non-existent task - this should raise an error
    # Note: This tests the validation that should happen at the tools layer
    with pytest.raises(ValueError):
        DependencyRepository.add_dependency("task-a", "nonexistent-task")


def test_add_task_multiple_tasks(mock_db_path):
    """Test adding multiple tasks in sequence."""
    task_names = [f"task-{i}" for i in range(10)]

    for name in task_names:
        task = TaskRepository.add_task(
            name=name,
            description=f"Description for {name}",
            priority=len(task_names) - int(name.split("-")[1]),
        )
        assert task.name == name

    # Verify all tasks exist
    all_tasks = TaskRepository.list_tasks()
    assert len(all_tasks) == 10
