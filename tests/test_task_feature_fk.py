"""
Tests for task feature_name foreign key constraint.
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


def test_add_task_default_feature(mock_db_path):
    """Test that tasks get 'default' feature_name by default."""
    task = TaskRepository.add_task(
        name="test-task",
        description="A test task",
    )

    assert task["feature_name"] == "default"


def test_add_task_explicit_default_feature(mock_db_path):
    """Test explicitly setting feature_name to 'default'."""
    task = TaskRepository.add_task(
        name="test-task",
        description="A test task",
        feature_name="default",
    )

    assert task["feature_name"] == "default"


def test_add_task_nonexistent_feature(mock_db_path):
    """Test that adding a task with non-existent feature raises an error."""
    with pytest.raises(ValueError, match="does not exist"):
        TaskRepository.add_task(
            name="test-task",
            description="A test task",
            feature_name="nonexistent-feature",
        )


def test_list_tasks_includes_feature_name(mock_db_path):
    """Test that listing tasks includes feature_name."""
    TaskRepository.add_task(
        name="task-1",
        description="Task 1",
    )

    tasks = TaskRepository.list_tasks()
    assert len(tasks) == 1
    assert "feature_name" in tasks[0]
    assert tasks[0]["feature_name"] == "default"


def test_get_task_includes_feature_name(mock_db_path):
    """Test that getting a task includes feature_name."""
    TaskRepository.add_task(
        name="test-task",
        description="A test task",
    )

    task = TaskRepository.get_task("test-task")
    assert task is not None
    assert "feature_name" in task
    assert task["feature_name"] == "default"


def test_add_task_with_all_parameters_including_feature(mock_db_path):
    """Test adding a task with all parameters including feature_name."""
    task = TaskRepository.add_task(
        name="full-task",
        description="A task with all parameters",
        priority=8,
        status="in_progress",
        details="Detailed implementation notes",
        feature_name="default",
    )

    assert task["name"] == "full-task"
    assert task["description"] == "A task with all parameters"
    assert task["priority"] == 8
    assert task["status"] == "in_progress"
    assert task["details"] == "Detailed implementation notes"
    assert task["feature_name"] == "default"
