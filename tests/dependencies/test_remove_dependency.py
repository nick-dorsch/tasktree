"""
Tests for the remove_dependency tool verifying relationship removal.
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


def test_remove_dependency_basic(mock_db_path):
    """Test removing a basic dependency between two tasks."""
    # Create tasks and add dependency
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    DependencyRepository.add_dependency("task-b", "task-a")

    # Verify dependency exists
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 1

    # Remove the dependency
    result = DependencyRepository.remove_dependency("task-b", "task-a")

    # Verify removal was successful
    assert result is True

    # Verify dependency no longer exists
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_remove_dependency_nonexistent(mock_db_path):
    """Test removing a dependency that doesn't exist."""
    # Create tasks but no dependency
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")

    # Try to remove non-existent dependency
    result = DependencyRepository.remove_dependency("task-b", "task-a")

    # Should return False (not deleted)
    assert result is False


def test_remove_dependency_nonexistent_tasks(mock_db_path):
    """Test removing a dependency where tasks don't exist."""
    # Try to remove dependency between non-existent tasks
    result = DependencyRepository.remove_dependency("nonexistent-1", "nonexistent-2")

    # Should return False (not deleted)
    assert result is False


def test_remove_dependency_one_of_multiple(mock_db_path):
    """Test removing one dependency when multiple exist for a task."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")

    # task-c depends on both task-a and task-b
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # Verify both dependencies exist
    deps = DependencyRepository.list_dependencies("task-c")
    assert len(deps) == 2

    # Remove one dependency
    result = DependencyRepository.remove_dependency("task-c", "task-a")
    assert result is True

    # Verify only one dependency remains
    deps = DependencyRepository.list_dependencies("task-c")
    assert len(deps) == 1
    assert deps[0].task_name == "task-c"
    assert deps[0].depends_on_task_name == "task-b"


def test_remove_dependency_from_chain(mock_db_path):
    """Test removing a dependency from a chain (A -> B -> C)."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")

    # Create chain: C depends on B, B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # Verify chain exists
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 2

    # Remove middle dependency (B -> A)
    result = DependencyRepository.remove_dependency("task-b", "task-a")
    assert result is True

    # Verify only one dependency remains (C -> B)
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 1
    assert all_deps[0].task_name == "task-c"
    assert all_deps[0].depends_on_task_name == "task-b"


def test_remove_dependency_affects_available_tasks(mock_db_path):
    """Test that removing dependencies affects which tasks are available."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec", status="pending")
    TaskRepository.add_task("task-b", "Task B", specification="Spec", status="pending")

    # Add dependency: B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")

    # Only task-a should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-a"

    # Remove the dependency
    DependencyRepository.remove_dependency("task-b", "task-a")

    # Now both tasks should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 2
    task_names = {task.name for task in available}
    assert task_names == {"task-a", "task-b"}


def test_remove_dependency_wrong_direction(mock_db_path):
    """Test that removing dependency in wrong direction doesn't work."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")

    # Add dependency: B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")

    # Verify dependency exists
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 1

    # Try to remove in opposite direction (A -> B instead of B -> A)
    result = DependencyRepository.remove_dependency("task-a", "task-b")

    # Should return False (nothing removed)
    assert result is False

    # Original dependency should still exist
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 1
    assert deps[0].task_name == "task-b"
    assert deps[0].depends_on_task_name == "task-a"


def test_remove_dependency_diamond_pattern(mock_db_path):
    """Test removing a dependency from a diamond pattern."""
    # Create diamond pattern:
    # D depends on B and C
    # B depends on A
    # C depends on A
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")
    TaskRepository.add_task("task-d", "Task D", specification="Spec")

    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    # Verify all dependencies exist
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 4

    # Remove one dependency from the diamond (D -> B)
    result = DependencyRepository.remove_dependency("task-d", "task-b")
    assert result is True

    # Verify only 3 dependencies remain
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 3

    # Verify the correct dependency was removed
    dep_pairs = {(d.task_name, d.depends_on_task_name) for d in all_deps}
    expected_pairs = {
        ("task-b", "task-a"),
        ("task-c", "task-a"),
        ("task-d", "task-c"),
    }
    assert dep_pairs == expected_pairs


def test_remove_dependency_all_from_task(mock_db_path):
    """Test removing all dependencies from a task one by one."""
    # Create tasks
    TaskRepository.add_task("base-task", "Base Task", specification="Spec")
    TaskRepository.add_task("dependent-1", "Dependent 1", specification="Spec")
    TaskRepository.add_task("dependent-2", "Dependent 2", specification="Spec")
    TaskRepository.add_task("dependent-3", "Dependent 3", specification="Spec")

    # Multiple tasks depend on base-task
    DependencyRepository.add_dependency("dependent-1", "base-task")
    DependencyRepository.add_dependency("dependent-2", "base-task")
    DependencyRepository.add_dependency("dependent-3", "base-task")

    # Verify all dependencies exist
    deps = DependencyRepository.list_dependencies("base-task")
    assert len(deps) == 3

    # Remove dependencies one by one
    result1 = DependencyRepository.remove_dependency("dependent-1", "base-task")
    assert result1 is True
    deps = DependencyRepository.list_dependencies("base-task")
    assert len(deps) == 2

    result2 = DependencyRepository.remove_dependency("dependent-2", "base-task")
    assert result2 is True
    deps = DependencyRepository.list_dependencies("base-task")
    assert len(deps) == 1

    result3 = DependencyRepository.remove_dependency("dependent-3", "base-task")
    assert result3 is True
    deps = DependencyRepository.list_dependencies("base-task")
    assert len(deps) == 0


def test_remove_dependency_idempotent(mock_db_path):
    """Test that removing the same dependency twice is idempotent."""
    # Create tasks and add dependency
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    DependencyRepository.add_dependency("task-b", "task-a")

    # Remove dependency first time
    result1 = DependencyRepository.remove_dependency("task-b", "task-a")
    assert result1 is True

    # Try to remove again
    result2 = DependencyRepository.remove_dependency("task-b", "task-a")
    assert result2 is False


def test_remove_dependency_complex_graph(mock_db_path):
    """Test removing a dependency in a complex graph."""
    # Create a complex graph:
    # E depends on D
    # D depends on B and C
    # B depends on A
    # C depends on A
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    TaskRepository.add_task("task-c", "Task C", specification="Spec")
    TaskRepository.add_task("task-d", "Task D", specification="Spec")
    TaskRepository.add_task("task-e", "Task E", specification="Spec")

    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")
    DependencyRepository.add_dependency("task-e", "task-d")

    # Verify initial state
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 5

    # Remove dependency C -> A
    result = DependencyRepository.remove_dependency("task-c", "task-a")
    assert result is True

    # Verify correct dependency was removed
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 4

    dep_pairs = {(d.task_name, d.depends_on_task_name) for d in all_deps}
    expected_pairs = {
        ("task-b", "task-a"),
        ("task-d", "task-b"),
        ("task-d", "task-c"),
        ("task-e", "task-d"),
    }
    assert dep_pairs == expected_pairs


def test_remove_dependency_allows_circular_after_removal(mock_db_path):
    """Test that removing a dependency allows previously blocked circular dependency."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")

    # Add dependency: B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")

    # Verify circular dependency is blocked
    with pytest.raises(ValueError, match="[Cc]ircular"):
        DependencyRepository.add_dependency("task-a", "task-b")

    # Remove the dependency
    DependencyRepository.remove_dependency("task-b", "task-a")

    # Now adding the reverse dependency should work (no longer circular)
    dep = DependencyRepository.add_dependency("task-a", "task-b")
    assert dep.task_name == "task-a"
    assert dep.depends_on_task_name == "task-b"


def test_remove_dependency_tasks_remain(mock_db_path):
    """Test that removing a dependency doesn't delete the tasks."""
    # Create tasks and add dependency
    TaskRepository.add_task("task-a", "Task A", specification="Spec")
    TaskRepository.add_task("task-b", "Task B", specification="Spec")
    DependencyRepository.add_dependency("task-b", "task-a")

    # Remove dependency
    DependencyRepository.remove_dependency("task-b", "task-a")

    # Verify tasks still exist
    task_a = TaskRepository.get_task("task-a")
    task_b = TaskRepository.get_task("task-b")

    assert task_a is not None
    assert task_a.name == "task-a"
    assert task_b is not None
    assert task_b.name == "task-b"


def test_remove_dependency_long_chain(mock_db_path):
    """Test removing a dependency from a long chain."""
    # Create a long chain of tasks
    chain_length = 8
    for i in range(chain_length):
        TaskRepository.add_task(f"task-{i}", f"Task {i}", specification="Spec")

    # Create chain: each task depends on the previous one
    for i in range(1, chain_length):
        DependencyRepository.add_dependency(f"task-{i}", f"task-{i - 1}")

    # Verify initial chain length
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == chain_length - 1

    # Remove a dependency from the middle (task-4 -> task-3)
    result = DependencyRepository.remove_dependency("task-4", "task-3")
    assert result is True

    # Verify chain length decreased by 1
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == chain_length - 2

    # Verify the correct dependency was removed
    deps_task4 = [d for d in all_deps if d.task_name == "task-4"]
    assert len(deps_task4) == 0


def test_remove_dependency_with_completed_tasks(mock_db_path):
    """Test removing a dependency where tasks are completed."""
    # Create tasks with different statuses
    TaskRepository.add_task("task-a", "Task A", specification="Spec", status="completed")
    TaskRepository.add_task("task-b", "Task B", specification="Spec", status="in_progress")

    # Add dependency
    DependencyRepository.add_dependency("task-b", "task-a")

    # Remove dependency
    result = DependencyRepository.remove_dependency("task-b", "task-a")

    # Should succeed regardless of task status
    assert result is True

    # Verify dependency was removed
    deps = DependencyRepository.list_dependencies()
    assert len(deps) == 0


def test_remove_dependency_multiple_independents(mock_db_path):
    """Test removing dependencies in multiple independent trees."""
    # Create two independent trees
    # Tree 1: B depends on A
    TaskRepository.add_task("tree1-a", "Tree 1 A", specification="Spec")
    TaskRepository.add_task("tree1-b", "Tree 1 B", specification="Spec")
    DependencyRepository.add_dependency("tree1-b", "tree1-a")

    # Tree 2: D depends on C
    TaskRepository.add_task("tree2-c", "Tree 2 C", specification="Spec")
    TaskRepository.add_task("tree2-d", "Tree 2 D", specification="Spec")
    DependencyRepository.add_dependency("tree2-d", "tree2-c")

    # Verify both dependencies exist
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 2

    # Remove dependency from tree 1
    result = DependencyRepository.remove_dependency("tree1-b", "tree1-a")
    assert result is True

    # Verify only tree 2 dependency remains
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 1
    assert all_deps[0].task_name == "tree2-d"
    assert all_deps[0].depends_on_task_name == "tree2-c"
