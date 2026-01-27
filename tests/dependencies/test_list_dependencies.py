"""
Tests for the list_dependencies tool with and without task name filter.
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


def test_list_dependencies_empty_database(mock_db_path):
    """Test listing dependencies when database is empty."""
    deps = DependencyRepository.list_dependencies()
    assert deps == []


def test_list_dependencies_no_dependencies(mock_db_path):
    """Test listing dependencies when tasks exist but no dependencies."""
    # Create tasks without dependencies
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")

    deps = DependencyRepository.list_dependencies()
    assert deps == []


def test_list_dependencies_all_basic(mock_db_path):
    """Test listing all dependencies with a basic setup."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")

    # Add dependency: task-b depends on task-a
    DependencyRepository.add_dependency("task-b", "task-a")

    # List all dependencies
    deps = DependencyRepository.list_dependencies()

    assert len(deps) == 1
    assert deps[0].task_name == "task-b"
    assert deps[0].depends_on_task_name == "task-a"


def test_list_dependencies_all_multiple(mock_db_path):
    """Test listing all dependencies with multiple dependencies."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # Add dependencies
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # List all dependencies
    deps = DependencyRepository.list_dependencies()

    assert len(deps) == 3
    # Verify ordering by task_name, depends_on_task_name
    assert deps[0].task_name == "task-b"
    assert deps[0].depends_on_task_name == "task-a"
    assert deps[1].task_name == "task-c"
    assert deps[1].depends_on_task_name == "task-a"
    assert deps[2].task_name == "task-c"
    assert deps[2].depends_on_task_name == "task-b"


def test_list_dependencies_all_ordering(mock_db_path):
    """Test that listing all dependencies returns them in correct order."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    # Add dependencies in non-alphabetical order
    DependencyRepository.add_dependency("task-d", "task-c")
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")

    # List all dependencies
    deps = DependencyRepository.list_dependencies()

    # Should be ordered by task_name, depends_on_task_name
    assert len(deps) == 4
    assert deps[0].task_name == "task-b"
    assert deps[1].task_name == "task-c"
    assert deps[2].task_name == "task-d"
    assert deps[2].depends_on_task_name == "task-b"
    assert deps[3].task_name == "task-d"
    assert deps[3].depends_on_task_name == "task-c"


def test_list_dependencies_filtered_task_as_dependent(mock_db_path):
    """Test listing dependencies filtered by a task that depends on others."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # Add dependencies: task-c depends on both task-a and task-b
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # List dependencies for task-c
    deps = DependencyRepository.list_dependencies("task-c")

    assert len(deps) == 2
    assert all(dep.task_name == "task-c" for dep in deps)
    assert {dep.depends_on_task_name for dep in deps} == {"task-a", "task-b"}


def test_list_dependencies_filtered_task_as_dependency(mock_db_path):
    """Test listing dependencies filtered by a task that others depend on."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # Add dependencies: both task-b and task-c depend on task-a
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")

    # List dependencies for task-a
    deps = DependencyRepository.list_dependencies("task-a")

    assert len(deps) == 2
    assert all(dep.depends_on_task_name == "task-a" for dep in deps)
    assert {dep.task_name for dep in deps} == {"task-b", "task-c"}


def test_list_dependencies_filtered_task_both_roles(mock_db_path):
    """Test listing dependencies for a task that is both dependent and dependency."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    # Create chain: C depends on B, B depends on A
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")

    # List dependencies for task-b (depends on A, depended on by C)
    deps = DependencyRepository.list_dependencies("task-b")

    assert len(deps) == 2
    # Should include both: where task-b is the dependent and where it's the dependency
    task_names = {dep.task_name for dep in deps}
    depends_on_names = {dep.depends_on_task_name for dep in deps}

    assert "task-b" in task_names
    assert "task-b" in depends_on_names
    assert "task-a" in depends_on_names
    assert "task-c" in task_names


def test_list_dependencies_filtered_nonexistent_task(mock_db_path):
    """Test listing dependencies for a task that doesn't exist."""
    # Create some tasks and dependencies
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    DependencyRepository.add_dependency("task-b", "task-a")

    # List dependencies for non-existent task
    deps = DependencyRepository.list_dependencies("nonexistent-task")

    # Should return empty list, not error
    assert deps == []


def test_list_dependencies_filtered_task_no_dependencies(mock_db_path):
    """Test listing dependencies for a task that exists but has no dependencies."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("isolated-task", "Isolated Task")

    # Add dependency between task-a and task-b
    DependencyRepository.add_dependency("task-b", "task-a")

    # List dependencies for isolated-task
    deps = DependencyRepository.list_dependencies("isolated-task")

    # Should return empty list
    assert deps == []


def test_list_dependencies_filtered_complex_graph(mock_db_path):
    """Test listing dependencies in a complex dependency graph."""
    # Create a complex graph:
    # D depends on B and C
    # B depends on A
    # C depends on A
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    # List dependencies for task-a (should be depended on by task-b and task-c)
    deps_a = DependencyRepository.list_dependencies("task-a")
    assert len(deps_a) == 2
    assert all(dep.depends_on_task_name == "task-a" for dep in deps_a)

    # List dependencies for task-d (should depend on task-b and task-c)
    deps_d = DependencyRepository.list_dependencies("task-d")
    assert len(deps_d) == 2
    assert all(dep.task_name == "task-d" for dep in deps_d)


def test_list_dependencies_all_diamond_pattern(mock_db_path):
    """Test listing all dependencies in a diamond pattern."""
    # Create diamond pattern:
    # D depends on B and C
    # B depends on A
    # C depends on A
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    # List all dependencies
    deps = DependencyRepository.list_dependencies()

    assert len(deps) == 4
    # Verify all dependencies are present
    dep_pairs = {(d.task_name, d.depends_on_task_name) for d in deps}
    expected_pairs = {
        ("task-b", "task-a"),
        ("task-c", "task-a"),
        ("task-d", "task-b"),
        ("task-d", "task-c"),
    }
    assert dep_pairs == expected_pairs


def test_list_dependencies_filtered_ordering(mock_db_path):
    """Test that filtered dependencies are returned in correct order."""
    # Create tasks
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    # Create dependencies where task-c is in the middle
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    # List dependencies for task-c
    deps = DependencyRepository.list_dependencies("task-c")

    # Should be ordered by task_name, depends_on_task_name
    assert len(deps) == 3
    # First two should be where task-c is the dependent (task_name = task-c)
    assert deps[0].task_name == "task-c"
    assert deps[0].depends_on_task_name == "task-a"
    assert deps[1].task_name == "task-c"
    assert deps[1].depends_on_task_name == "task-b"
    # Last one should be where task-c is the dependency (depends_on_task_name = task-c)
    assert deps[2].task_name == "task-d"
    assert deps[2].depends_on_task_name == "task-c"


def test_list_dependencies_long_chain(mock_db_path):
    """Test listing dependencies in a long chain."""
    # Create a long chain: task-0 <- task-1 <- task-2 <- ... <- task-7
    chain_length = 8
    for i in range(chain_length):
        TaskRepository.add_task(f"task-{i}", f"Task {i}")

    for i in range(1, chain_length):
        DependencyRepository.add_dependency(f"task-{i}", f"task-{i - 1}")

    # List all dependencies
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == chain_length - 1

    # List dependencies for middle task (task-4)
    deps_middle = DependencyRepository.list_dependencies("task-4")
    # task-4 depends on task-3, and task-5 depends on task-4
    assert len(deps_middle) == 2


def test_list_dependencies_multiple_independents(mock_db_path):
    """Test listing dependencies with multiple independent dependency trees."""
    # Create two independent trees
    # Tree 1: B depends on A
    TaskRepository.add_task("tree1-a", "Tree 1 A")
    TaskRepository.add_task("tree1-b", "Tree 1 B")
    DependencyRepository.add_dependency("tree1-b", "tree1-a")

    # Tree 2: D depends on C
    TaskRepository.add_task("tree2-c", "Tree 2 C")
    TaskRepository.add_task("tree2-d", "Tree 2 D")
    DependencyRepository.add_dependency("tree2-d", "tree2-c")

    # List all dependencies
    all_deps = DependencyRepository.list_dependencies()
    assert len(all_deps) == 2

    # List dependencies for tree1-a (only tree 1 should appear)
    deps_tree1 = DependencyRepository.list_dependencies("tree1-a")
    assert len(deps_tree1) == 1
    assert deps_tree1[0].task_name == "tree1-b"
