"""
Tests for the get_available_tasks tool.

These tests verify:
1. Dependency resolution - tasks are only available when dependencies are completed
2. Priority ordering - higher priority tasks appear first
3. Status filtering - only non-completed tasks are returned
4. Complex dependency chains - multi-level dependencies work correctly
"""

import pytest

from tasktree_mcp.database import DependencyRepository, TaskRepository


@pytest.fixture
def mock_db_path(test_db, monkeypatch):
    """
    Mock the DB_PATH to use the test database.

    This fixture modifies the database.DB_PATH to point to the test database,
    ensuring all repository operations use the isolated test database.
    """
    import tasktree_mcp.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


def test_get_available_tasks_empty_database(mock_db_path):
    """Test that get_available_tasks returns empty list when no tasks exist."""
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 0


def test_get_available_tasks_no_dependencies(mock_db_path):
    """Test that all pending tasks are available when there are no dependencies."""
    # Create tasks with different priorities
    TaskRepository.add_task(
        "low-priority", "Low priority task", priority=1, status="pending"
    )
    TaskRepository.add_task(
        "high-priority", "High priority task", priority=10, status="pending"
    )
    TaskRepository.add_task(
        "medium-priority", "Medium priority task", priority=5, status="pending"
    )

    available = DependencyRepository.get_available_tasks()

    # All three tasks should be available
    assert len(available) == 3

    # Should be ordered by priority (descending)
    assert available[0].name == "high-priority"
    assert available[0].priority == 10
    assert available[1].name == "medium-priority"
    assert available[1].priority == 5
    assert available[2].name == "low-priority"
    assert available[2].priority == 1


def test_get_available_tasks_excludes_completed(mock_db_path):
    """Test that only pending tasks are available."""
    TaskRepository.add_task("completed-task", "Already done", status="completed")
    TaskRepository.add_task("pending-task", "Not yet done", status="pending")
    TaskRepository.add_task(
        "in-progress-task", "Currently working", status="in_progress"
    )

    available = DependencyRepository.get_available_tasks()

    # Only pending tasks should be available
    assert len(available) == 1
    task_names = {task.name for task in available}
    assert "pending-task" in task_names
    assert "completed-task" not in task_names
    assert "in-progress-task" not in task_names


def test_get_available_tasks_simple_dependency_chain(mock_db_path):
    """Test that tasks with uncompleted dependencies are not available."""
    # Create a simple chain: task-a -> task-b -> task-c
    TaskRepository.add_task("task-a", "First task", status="pending")
    TaskRepository.add_task("task-b", "Second task", status="pending")
    TaskRepository.add_task("task-c", "Third task", status="pending")

    # task-b depends on task-a, task-c depends on task-b
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # Only task-a should be available (no dependencies)
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-a"

    # Complete task-a
    TaskRepository.update_task("task-a", status="completed")

    # Now task-b should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-b"

    # Complete task-b
    TaskRepository.update_task("task-b", status="completed")

    # Now task-c should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-c"


def test_get_available_tasks_multiple_dependencies(mock_db_path):
    """Test that tasks with multiple dependencies are only available when all are completed."""
    # Create tasks
    TaskRepository.add_task("dep-1", "First dependency", status="pending")
    TaskRepository.add_task("dep-2", "Second dependency", status="pending")
    TaskRepository.add_task("dep-3", "Third dependency", status="pending")
    TaskRepository.add_task(
        "main-task", "Task with multiple dependencies", status="pending"
    )

    # main-task depends on all three deps
    DependencyRepository.add_dependency("main-task", "dep-1")
    DependencyRepository.add_dependency("main-task", "dep-2")
    DependencyRepository.add_dependency("main-task", "dep-3")

    # Initially, only the dependencies should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 3
    task_names = {task.name for task in available}
    assert "dep-1" in task_names
    assert "dep-2" in task_names
    assert "dep-3" in task_names
    assert "main-task" not in task_names

    # Complete two of the dependencies
    TaskRepository.update_task("dep-1", status="completed")
    TaskRepository.update_task("dep-2", status="completed")

    # main-task should still not be available (dep-3 is not completed)
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "dep-3"

    # Complete the last dependency
    TaskRepository.update_task("dep-3", status="completed")

    # Now main-task should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "main-task"


def test_get_available_tasks_priority_ordering(mock_db_path):
    """Test that available tasks are ordered by priority (highest first)."""
    # Create tasks with different priorities, all available
    TaskRepository.add_task("priority-1", "Priority 1", priority=1)
    TaskRepository.add_task("priority-10", "Priority 10", priority=10)
    TaskRepository.add_task("priority-5", "Priority 5", priority=5)
    TaskRepository.add_task("priority-7", "Priority 7", priority=7)
    TaskRepository.add_task("priority-3", "Priority 3", priority=3)

    available = DependencyRepository.get_available_tasks()

    # Check they're ordered by priority descending
    assert len(available) == 5
    assert available[0].priority == 10
    assert available[1].priority == 7
    assert available[2].priority == 5
    assert available[3].priority == 3
    assert available[4].priority == 1


def test_get_available_tasks_created_at_secondary_sort(mock_db_path):
    """Test that tasks with same priority are ordered by created_at (oldest first)."""
    # Create tasks with same priority
    TaskRepository.add_task("task-1", "First created", priority=5)
    TaskRepository.add_task("task-2", "Second created", priority=5)
    TaskRepository.add_task("task-3", "Third created", priority=5)

    available = DependencyRepository.get_available_tasks()

    # Should be ordered by created_at (ascending) when priority is the same
    assert len(available) == 3
    assert available[0].name == "task-1"
    assert available[1].name == "task-2"
    assert available[2].name == "task-3"


def test_get_available_tasks_complex_dependency_graph(mock_db_path):
    """Test a complex dependency graph with multiple branches."""
    # Create a dependency graph:
    #       base
    #      /    \
    #   left    right
    #      \    /
    #       top

    TaskRepository.add_task("base", "Base task", status="completed", priority=5)
    TaskRepository.add_task("left", "Left branch", status="pending", priority=10)
    TaskRepository.add_task("right", "Right branch", status="pending", priority=8)
    TaskRepository.add_task("top", "Top task", status="pending", priority=9)

    DependencyRepository.add_dependency("left", "base")
    DependencyRepository.add_dependency("right", "base")
    DependencyRepository.add_dependency("top", "left")
    DependencyRepository.add_dependency("top", "right")

    # Both left and right should be available (base is completed)
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 2
    # Should be ordered by priority: left (10) before right (8)
    assert available[0].name == "left"
    assert available[1].name == "right"

    # Complete left branch
    TaskRepository.update_task("left", status="completed")

    # Only right should be available now
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "right"

    # Complete right branch
    TaskRepository.update_task("right", status="completed")

    # Now top should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "top"


def test_get_available_tasks_in_progress_dependencies(mock_db_path):
    """Test that tasks with in_progress dependencies are not available."""
    TaskRepository.add_task("dep-task", "Dependency", status="in_progress")
    TaskRepository.add_task("main-task", "Main task", status="pending")

    DependencyRepository.add_dependency("main-task", "dep-task")

    # main-task should not be available (dep-task is in_progress, not completed)
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 0


def test_get_available_tasks_no_uncompleted_dependencies_only(mock_db_path):
    """Test that a task with some completed and some uncompleted dependencies is not available."""
    TaskRepository.add_task("completed-dep", "Completed dependency", status="completed")
    TaskRepository.add_task("pending-dep", "Pending dependency", status="pending")
    TaskRepository.add_task("main-task", "Main task", status="pending")

    DependencyRepository.add_dependency("main-task", "completed-dep")
    DependencyRepository.add_dependency("main-task", "pending-dep")

    # main-task should not be available (pending-dep is not completed)
    available = DependencyRepository.get_available_tasks()
    task_names = {task.name for task in available}
    assert "pending-dep" in task_names
    assert "main-task" not in task_names


def test_get_available_tasks_handles_orphaned_tasks(mock_db_path):
    """Test that only pending orphans are available."""
    TaskRepository.add_task("orphan-1", "Orphan task 1", status="pending", priority=5)
    TaskRepository.add_task(
        "orphan-2", "Orphan task 2", status="in_progress", priority=3
    )
    TaskRepository.add_task(
        "with-deps", "Task with deps", status="pending", priority=10
    )
    TaskRepository.add_task("dep", "Dependency", status="pending", priority=1)

    DependencyRepository.add_dependency("with-deps", "dep")

    # Only pending orphans and dep should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 2
    task_names = {task.name for task in available}
    assert "orphan-1" in task_names
    assert "dep" in task_names
    assert "with-deps" not in task_names
    assert "orphan-2" not in task_names


def test_get_available_tasks_all_completed(mock_db_path):
    """Test that when all tasks are completed, no tasks are available."""
    TaskRepository.add_task("task-1", "Task 1", status="completed")
    TaskRepository.add_task("task-2", "Task 2", status="completed")
    TaskRepository.add_task("task-3", "Task 3", status="completed")

    available = DependencyRepository.get_available_tasks()
    assert len(available) == 0
