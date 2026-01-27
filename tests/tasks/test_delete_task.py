"""
Tests for the delete_task tool including cascading dependency cleanup.
"""

from pathlib import Path

import pytest

from tasktree.core.database import DependencyRepository, TaskRepository


@pytest.fixture
def mock_db_path(test_db: Path, monkeypatch):
    """
    Mock the DB_PATH to use the test database.

    This fixture modifies the database.DB_PATH to point to the test database,
    ensuring all repository operations use the isolated test database.
    """
    import tasktree.core.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


def test_delete_task_basic(mock_db_path):
    """Test deleting a task with no dependencies."""
    # Create a task
    TaskRepository.add_task("task-to-delete", "Task to delete", specification="Spec")

    # Verify it exists
    task = TaskRepository.get_task("task-to-delete")
    assert task is not None

    # Delete it
    deleted = TaskRepository.delete_task("task-to-delete")
    assert deleted is True

    # Verify it's gone
    task = TaskRepository.get_task("task-to-delete")
    assert task is None


def test_delete_task_nonexistent(mock_db_path):
    """Test deleting a task that doesn't exist returns False."""
    # Try to delete a task that doesn't exist
    deleted = TaskRepository.delete_task("nonexistent-task")
    assert deleted is False


def test_delete_task_empty_name(mock_db_path):
    """Test that deleting a task with empty name raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        TaskRepository.delete_task("")


def test_delete_task_whitespace_name(mock_db_path):
    """Test that deleting a task with whitespace-only name raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        TaskRepository.delete_task("   ")


def test_delete_task_with_outgoing_dependencies(mock_db_path):
    """Test deleting a task that depends on other tasks (has outgoing dependencies)."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")

    # task-b depends on task-a
    DependencyRepository.add_dependency("task-b", "task-a")

    # Delete task-b (which has outgoing dependency to task-a)
    deleted = TaskRepository.delete_task("task-b")
    assert deleted is True

    # Verify task-b is gone
    assert TaskRepository.get_task("task-b") is None

    # Verify task-a still exists
    assert TaskRepository.get_task("task-a") is not None

    # Verify the dependency is also gone
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_delete_task_with_incoming_dependencies(mock_db_path):
    """Test deleting a task that other tasks depend on (has incoming dependencies)."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")

    # task-b depends on task-a
    DependencyRepository.add_dependency("task-b", "task-a")

    # Delete task-a (which task-b depends on)
    deleted = TaskRepository.delete_task("task-a")
    assert deleted is True

    # Verify task-a is gone
    assert TaskRepository.get_task("task-a") is None

    # Verify task-b still exists
    assert TaskRepository.get_task("task-b") is not None

    # Verify the dependency is also gone (cascading delete)
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_delete_task_with_multiple_outgoing_dependencies(mock_db_path):
    """Test deleting a task that depends on multiple other tasks."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")

    # task-c depends on both task-a and task-b
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # Verify dependencies exist
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 2

    # Delete task-c
    deleted = TaskRepository.delete_task("task-c")
    assert deleted is True

    # Verify task-c is gone
    assert TaskRepository.get_task("task-c") is None

    # Verify task-a and task-b still exist
    assert TaskRepository.get_task("task-a") is not None
    assert TaskRepository.get_task("task-b") is not None

    # Verify all dependencies involving task-c are gone
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_delete_task_with_multiple_incoming_dependencies(mock_db_path):
    """Test deleting a task that multiple other tasks depend on."""
    # Create tasks
    TaskRepository.add_task("base-task", "Base Task", specification="Spec")
    TaskRepository.add_task("dependent-1", "Dependent 1", specification="Spec")
    TaskRepository.add_task("dependent-2", "Dependent 2", specification="Spec")
    TaskRepository.add_task("dependent-3", "Dependent 3", specification="Spec")

    # Multiple tasks depend on base-task
    DependencyRepository.add_dependency("dependent-1", "base-task")
    DependencyRepository.add_dependency("dependent-2", "base-task")
    DependencyRepository.add_dependency("dependent-3", "base-task")

    # Verify dependencies exist
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 3

    # Delete base-task
    deleted = TaskRepository.delete_task("base-task")
    assert deleted is True

    # Verify base-task is gone
    assert TaskRepository.get_task("base-task") is None

    # Verify dependent tasks still exist
    assert TaskRepository.get_task("dependent-1") is not None
    assert TaskRepository.get_task("dependent-2") is not None
    assert TaskRepository.get_task("dependent-3") is not None

    # Verify all dependencies involving base-task are gone
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_delete_task_in_dependency_chain(mock_db_path):
    """Test deleting a task in the middle of a dependency chain."""
    # Create a chain: task-c depends on task-b, task-b depends on task-a
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")

    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # Verify chain exists
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 2

    # Delete task-b (in the middle)
    deleted = TaskRepository.delete_task("task-b")
    assert deleted is True

    # Verify task-b is gone
    assert TaskRepository.get_task("task-b") is None

    # Verify task-a and task-c still exist
    assert TaskRepository.get_task("task-a") is not None
    assert TaskRepository.get_task("task-c") is not None

    # Verify only dependencies involving task-b are gone
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_delete_task_in_complex_graph(mock_db_path):
    """Test deleting a task in a complex dependency graph."""
    # Create a diamond pattern:
    # task-d depends on task-b and task-c
    # task-b depends on task-a
    # task-c depends on task-a
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")
    TaskRepository.add_task("task-d", "Task D", specification="Spec")

    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    # Verify graph exists
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 4

    # Delete task-a (at the base)
    deleted = TaskRepository.delete_task("task-a")
    assert deleted is True

    # Verify task-a is gone
    assert TaskRepository.get_task("task-a") is None

    # Verify other tasks still exist
    assert TaskRepository.get_task("task-b") is not None
    assert TaskRepository.get_task("task-c") is not None
    assert TaskRepository.get_task("task-d") is not None

    # Verify only dependencies involving task-a are gone
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 2  # Only task-d -> task-b and task-d -> task-c remain


def test_delete_task_with_different_statuses(mock_db_path):
    """Test deleting tasks with different status values."""
    statuses = ["pending", "in_progress", "completed", "blocked"]

    for status in statuses:
        task_name = f"task-{status}"
        TaskRepository.add_task(
            task_name, f"Task with {status} status", specification="Spec", status=status
        )

        # Delete it
        deleted = TaskRepository.delete_task(task_name)
        assert deleted is True

        # Verify it's gone
        assert TaskRepository.get_task(task_name) is None


def test_delete_task_affects_available_tasks(mock_db_path):
    """Test that deleting a task affects the available tasks list."""
    # Create tasks with dependencies
    TaskRepository.add_task("task-a", "Task A", specification="Spec", status="pending")
    TaskRepository.add_task("task-b", "Task B", specification="Spec", status="pending")

    # task-b depends on task-a
    DependencyRepository.add_dependency("task-b", "task-a")

    # Only task-a should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-a"

    # Delete task-a
    TaskRepository.delete_task("task-a")

    # Now task-b should be available (no more dependencies)
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-b"


def test_delete_multiple_tasks_in_sequence(mock_db_path):
    """Test deleting multiple tasks in sequence."""
    # Create multiple tasks
    task_names = [f"task-{i}" for i in range(5)]
    for name in task_names:
        TaskRepository.add_task(name, f"Description for {name}", specification="Spec")

    # Delete them one by one
    for name in task_names:
        deleted = TaskRepository.delete_task(name)
        assert deleted is True
        assert TaskRepository.get_task(name) is None

    # Verify all tasks are gone
    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 0


def test_delete_task_and_verify_list_count(mock_db_path):
    """Test that deleting a task updates the task count correctly."""
    # Create tasks
    TaskRepository.add_task("task-1", "Task 1", specification="Spec")
    TaskRepository.add_task("task-2", "Task 2", specification="Spec")
    TaskRepository.add_task("task-3", "Task 3", specification="Spec")

    # Verify count
    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 3

    # Delete one task
    TaskRepository.delete_task("task-2")

    # Verify count decreased
    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 2
    assert all(task.name != "task-2" for task in tasks)


def test_delete_task_with_bidirectional_dependencies(mock_db_path):
    """Test deleting a task that has both incoming and outgoing dependencies."""
    # Create tasks: A <- B <- C, B <- D
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")
    TaskRepository.add_task("task-d", "Task D", specification="Spec")

    # Create dependencies
    DependencyRepository.add_dependency("task-b", "task-a")  # B depends on A
    DependencyRepository.add_dependency("task-c", "task-b")  # C depends on B
    DependencyRepository.add_dependency("task-d", "task-b")  # D depends on B

    # Verify dependencies exist
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 3

    # Delete task-b (has both incoming and outgoing dependencies)
    deleted = TaskRepository.delete_task("task-b")
    assert deleted is True

    # Verify task-b is gone
    assert TaskRepository.get_task("task-b") is None

    # Verify other tasks still exist
    assert TaskRepository.get_task("task-a") is not None
    assert TaskRepository.get_task("task-c") is not None
    assert TaskRepository.get_task("task-d") is not None

    # Verify all dependencies involving task-b are gone
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_delete_task_idempotency(mock_db_path):
    """Test that deleting a task multiple times is safe."""
    # Create a task
    TaskRepository.add_task("task-to-delete", "Task to delete", specification="Spec")

    # Delete it first time
    deleted = TaskRepository.delete_task("task-to-delete")
    assert deleted is True

    # Try to delete it again
    deleted = TaskRepository.delete_task("task-to-delete")
    assert deleted is False


def test_delete_task_preserves_other_dependencies(mock_db_path):
    """Test that deleting a task doesn't affect unrelated dependencies."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")
    TaskRepository.add_task("task-d", "Task D", specification="Spec")

    # Create dependencies
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-d", "task-c")

    # Delete task-a
    TaskRepository.delete_task("task-a")

    # Verify task-d -> task-c dependency still exists
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 1
    assert deps[0].task_name == "task-d"
    assert deps[0].depends_on_task_name == "task-c"


def test_delete_task_special_characters(mock_db_path):
    """Test deleting tasks with special characters in names."""
    special_names = [
        "task-with-dashes",
        "task_with_underscores",
        "task.with.dots",
        "task:with:colons",
    ]

    for name in special_names:
        TaskRepository.add_task(name, f"Task with name: {name}", specification="Spec")
        deleted = TaskRepository.delete_task(name)
        assert deleted is True
        assert TaskRepository.get_task(name) is None


def test_delete_task_with_specification_field(mock_db_path):
    """Test deleting a task that has specification field populated."""
    # Create a task with specification
    TaskRepository.add_task(
        "task-with-details",
        "A task",
        specification="These are detailed implementation notes",
    )

    # Delete it
    deleted = TaskRepository.delete_task("task-with-details")
    assert deleted is True

    # Verify it's gone
    assert TaskRepository.get_task("task-with-details") is None
