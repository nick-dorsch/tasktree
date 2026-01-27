"""
Tests for the add_dependency tool including circular dependency prevention.
"""

from pathlib import Path

import pytest

from tasktree.database import DependencyRepository, TaskRepository


@pytest.fixture
def mock_db_path(test_db: Path, monkeypatch):
    """
    Mock the DB_PATH to use the test database.

    This fixture modifies the database.DB_PATH to point to the test database,
    ensuring all repository operations use the isolated test database.
    """
    import tasktree.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


def test_add_dependency_basic(mock_db_path):
    """Test adding a basic dependency between two tasks."""
    # Create two tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")

    # Add dependency: task-b depends on task-a
    dep = DependencyRepository.add_dependency("task-b", "task-a")

    assert dep.task_name == "task-b"
    assert dep.depends_on_task_name == "task-a"


def test_add_dependency_multiple_dependencies_single_task(mock_db_path):
    """Test adding multiple dependencies for a single task."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # task-c depends on both task-a and task-b
    dep1 = DependencyRepository.add_dependency("task-c", "task-a")
    dep2 = DependencyRepository.add_dependency("task-c", "task-b")

    assert dep1.task_name == "task-c"
    assert dep1.depends_on_task_name == "task-a"
    assert dep2.task_name == "task-c"
    assert dep2.depends_on_task_name == "task-b"

    # Verify both dependencies exist
    deps = DependencyRepository.list_dependencies("task-c")
    assert len(deps) == 2


def test_add_dependency_chain(mock_db_path):
    """Test creating a dependency chain (A -> B -> C)."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # Create chain: C depends on B, B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # Verify chain exists
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 2


def test_add_dependency_nonexistent_task(mock_db_path):
    """Test that adding dependency with non-existent task raises error."""
    # Create only one task
    TaskRepository.add_task("task-a", "Task A")

    # Try to add dependency on non-existent task
    with pytest.raises(ValueError, match="Both tasks must exist"):
        DependencyRepository.add_dependency("task-a", "nonexistent-task")


def test_add_dependency_both_tasks_nonexistent(mock_db_path):
    """Test that adding dependency with both tasks non-existent raises error."""
    # Don't create any tasks

    # Try to add dependency between non-existent tasks
    with pytest.raises(ValueError, match="Both tasks must exist"):
        DependencyRepository.add_dependency("nonexistent-1", "nonexistent-2")


def test_add_dependency_duplicate(mock_db_path):
    """Test that adding the same dependency twice raises an error."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")

    # Add dependency
    DependencyRepository.add_dependency("task-b", "task-a")

    # Try to add same dependency again
    with pytest.raises(ValueError, match="already exists"):
        DependencyRepository.add_dependency("task-b", "task-a")


def test_add_dependency_circular_direct(mock_db_path):
    """Test that direct circular dependencies are prevented (A -> B, B -> A)."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")

    # Add first dependency: B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")

    # Try to add circular dependency: A depends on B
    with pytest.raises(ValueError, match="[Cc]ircular"):
        DependencyRepository.add_dependency("task-a", "task-b")


def test_add_dependency_circular_indirect(mock_db_path):
    """Test that indirect circular dependencies are prevented (A -> B -> C -> A)."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # Create chain: B depends on A, C depends on B
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # Try to create circular dependency: A depends on C (would create A -> B -> C -> A)
    with pytest.raises(ValueError, match="[Cc]ircular"):
        DependencyRepository.add_dependency("task-a", "task-c")


def test_add_dependency_circular_complex(mock_db_path):
    """Test circular dependency prevention in a complex graph."""
    # Create a more complex dependency graph
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    # Create dependencies:
    # D depends on B and C
    # B depends on A
    # C depends on A
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    # Try to create circular dependency: A depends on D
    with pytest.raises(ValueError, match="[Cc]ircular"):
        DependencyRepository.add_dependency("task-a", "task-d")


def test_add_dependency_diamond_pattern(mock_db_path):
    """Test that diamond dependency patterns are allowed (not circular)."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    # Create diamond pattern:
    # D depends on B and C
    # B depends on A
    # C depends on A
    # This is NOT circular, just a diamond pattern
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    # Verify all dependencies were created successfully
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 4


def test_add_dependency_affects_available_tasks(mock_db_path):
    """Test that adding dependencies affects which tasks are available."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", status="pending")
    TaskRepository.add_task("task-b", "Task B", status="pending")

    # Initially, both tasks should be available
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 2

    # Add dependency: B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")

    # Now only task-a should be available (task-b depends on it)
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-a"


def test_add_dependency_with_completed_dependency(mock_db_path):
    """Test adding a dependency where the dependency task is already completed."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A", status="completed")
    TaskRepository.add_task("task-b", "Task B", status="pending")

    # Add dependency: B depends on A (which is already completed)
    dep = DependencyRepository.add_dependency("task-b", "task-a")

    assert dep.task_name == "task-b"
    assert dep.depends_on_task_name == "task-a"

    # task-b should be available since its dependency is completed
    available = DependencyRepository.get_available_tasks()
    assert len(available) == 1
    assert available[0].name == "task-b"


def test_add_dependency_list_by_task(mock_db_path):
    """Test listing dependencies for a specific task after adding."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    # Add dependencies
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-c")

    # List dependencies for task-a (both where it's the source and target)
    deps_a = DependencyRepository.list_dependencies("task-a")
    # task-a is depended on by task-b and task-c
    assert len(deps_a) == 2

    # List dependencies for task-c
    deps_c = DependencyRepository.list_dependencies("task-c")
    # task-c depends on task-a, and task-d depends on task-c
    assert len(deps_c) == 2


def test_add_dependency_ordering(mock_db_path):
    """Test that dependencies are returned in a consistent order."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # Add dependencies in random order
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # List all dependencies
    deps = DependencyRepository.list_dependencies()

    # Should be ordered by task_name, depends_on_task_name
    assert deps[0].task_name == "task-b"
    assert deps[1].task_name == "task-c"
    assert deps[2].task_name == "task-c"


def test_add_dependency_self_dependency_prevented(mock_db_path):
    """Test that self-dependencies are prevented (task depending on itself)."""
    # Create a task
    TaskRepository.add_task("task-a", "Task A")

    # Try to create self-dependency
    # This should be prevented by the CHECK constraint in the schema
    with pytest.raises(Exception):  # Could be IntegrityError or ValueError
        DependencyRepository.add_dependency("task-a", "task-a")


def test_add_dependency_multiple_dependents(mock_db_path):
    """Test that multiple tasks can depend on the same task."""
    # Create tasks
    TaskRepository.add_task("base-task", "Base Task")
    TaskRepository.add_task("dependent-1", "Dependent 1")
    TaskRepository.add_task("dependent-2", "Dependent 2")
    TaskRepository.add_task("dependent-3", "Dependent 3")

    # Multiple tasks depend on base-task
    DependencyRepository.add_dependency("dependent-1", "base-task")
    DependencyRepository.add_dependency("dependent-2", "base-task")
    DependencyRepository.add_dependency("dependent-3", "base-task")

    # Verify all dependencies
    deps = DependencyRepository.list_dependencies("base-task")
    assert len(deps) == 3


def test_add_dependency_long_chain(mock_db_path):
    """Test creating a long chain of dependencies."""
    # Create a long chain of tasks
    chain_length = 8
    for i in range(chain_length):
        TaskRepository.add_task(f"task-{i}", f"Task {i}")

    # Create chain: each task depends on the previous one
    for i in range(1, chain_length):
        DependencyRepository.add_dependency(f"task-{i}", f"task-{i - 1}")

    # Verify chain length
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == chain_length - 1

    # Try to create circular dependency with long chain
    with pytest.raises(ValueError, match="[Cc]ircular"):
        DependencyRepository.add_dependency("task-0", f"task-{chain_length - 1}")
