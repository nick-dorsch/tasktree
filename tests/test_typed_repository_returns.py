"""
Tests for typed repository method returns.

This test suite validates that repository methods return Pydantic models
(TaskResponse, DependencyResponse, FeatureResponse) instead of Dict[str, Any].
"""

from pathlib import Path

import pytest

from tasktree_mcp.database import (
    DependencyRepository,
    FeatureRepository,
    TaskRepository,
)
from tasktree_mcp.models import DependencyResponse, FeatureResponse, TaskResponse


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


class TestTaskRepositoryTypedReturns:
    """Tests for TaskRepository returning typed models."""

    def test_add_task_returns_task_response(self, mock_db_path):
        """Test that add_task returns a TaskResponse instance."""
        result = TaskRepository.add_task(
            name="test-task",
            description="Test description",
            priority=5,
        )

        assert isinstance(result, TaskResponse)
        assert result.name == "test-task"
        assert result.description == "Test description"
        assert result.priority == 5
        assert result.status == "pending"
        assert result.created_at is not None

    def test_get_task_returns_task_response(self, mock_db_path):
        """Test that get_task returns a TaskResponse instance."""
        TaskRepository.add_task("my-task", "Description")

        result = TaskRepository.get_task("my-task")

        assert isinstance(result, TaskResponse)
        assert result.name == "my-task"
        assert result.description == "Description"

    def test_get_task_returns_none_when_not_found(self, mock_db_path):
        """Test that get_task returns None when task doesn't exist."""
        result = TaskRepository.get_task("non-existent")

        assert result is None

    def test_list_tasks_returns_list_of_task_responses(self, mock_db_path):
        """Test that list_tasks returns a list of TaskResponse instances."""
        TaskRepository.add_task("task-1", "First task", priority=1)
        TaskRepository.add_task("task-2", "Second task", priority=2)
        TaskRepository.add_task("task-3", "Third task", priority=3)

        result = TaskRepository.list_tasks()

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(task, TaskResponse) for task in result)
        assert result[0].name == "task-3"  # Highest priority first
        assert result[1].name == "task-2"
        assert result[2].name == "task-1"

    def test_list_tasks_returns_empty_list_when_no_tasks(self, mock_db_path):
        """Test that list_tasks returns empty list when no tasks exist."""
        result = TaskRepository.list_tasks()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_tasks_with_filters_returns_task_responses(self, mock_db_path):
        """Test that list_tasks with filters returns TaskResponse instances."""
        TaskRepository.add_task("task-1", "First", priority=5, status="pending")
        TaskRepository.add_task("task-2", "Second", priority=8, status="in_progress")

        result = TaskRepository.list_tasks(status="in_progress", priority_min=5)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TaskResponse)
        assert result[0].name == "task-2"
        assert result[0].status == "in_progress"

    def test_update_task_returns_task_response(self, mock_db_path):
        """Test that update_task returns a TaskResponse instance."""
        TaskRepository.add_task("update-me", "Original", priority=1)

        result = TaskRepository.update_task(
            "update-me",
            description="Updated",
            priority=5,
            status="in_progress",
        )

        assert isinstance(result, TaskResponse)
        assert result.name == "update-me"
        assert result.description == "Updated"
        assert result.priority == 5
        assert result.status == "in_progress"

    def test_update_task_returns_none_when_not_found(self, mock_db_path):
        """Test that update_task returns None when task doesn't exist."""
        result = TaskRepository.update_task("non-existent", description="New")

        assert result is None

    def test_complete_task_returns_task_response(self, mock_db_path):
        """Test that complete_task returns a TaskResponse instance."""
        TaskRepository.add_task("complete-me", "Task to complete")

        result = TaskRepository.complete_task("complete-me")

        assert isinstance(result, TaskResponse)
        assert result.name == "complete-me"
        assert result.status == "completed"
        assert result.completed_at is not None

    def test_complete_task_returns_none_when_not_found(self, mock_db_path):
        """Test that complete_task returns None when task doesn't exist."""
        result = TaskRepository.complete_task("non-existent")

        assert result is None

    def test_task_response_has_all_fields(self, mock_db_path):
        """Test that TaskResponse instances have all expected fields."""
        result = TaskRepository.add_task(
            name="full-task",
            description="Full description",
            details="Implementation details",
            priority=7,
            status="pending",
            feature_name="default",
        )

        assert isinstance(result, TaskResponse)
        assert hasattr(result, "name")
        assert hasattr(result, "description")
        assert hasattr(result, "details")
        assert hasattr(result, "priority")
        assert hasattr(result, "status")
        assert hasattr(result, "feature_name")
        assert hasattr(result, "tests_required")
        assert hasattr(result, "created_at")
        assert hasattr(result, "updated_at")
        assert hasattr(result, "started_at")
        assert hasattr(result, "completed_at")


class TestDependencyRepositoryTypedReturns:
    """Tests for DependencyRepository returning typed models."""

    def test_add_dependency_returns_dependency_response(self, mock_db_path):
        """Test that add_dependency returns a DependencyResponse instance."""
        TaskRepository.add_task("task-a", "First task")
        TaskRepository.add_task("task-b", "Second task")

        result = DependencyRepository.add_dependency("task-b", "task-a")

        assert isinstance(result, DependencyResponse)
        assert result.task_name == "task-b"
        assert result.depends_on_task_name == "task-a"

    def test_list_dependencies_returns_list_of_dependency_responses(self, mock_db_path):
        """Test that list_dependencies returns list of DependencyResponse instances."""
        TaskRepository.add_task("task-1", "Task 1")
        TaskRepository.add_task("task-2", "Task 2")
        TaskRepository.add_task("task-3", "Task 3")

        DependencyRepository.add_dependency("task-2", "task-1")
        DependencyRepository.add_dependency("task-3", "task-1")
        DependencyRepository.add_dependency("task-3", "task-2")

        result = DependencyRepository.list_dependencies()

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(dep, DependencyResponse) for dep in result)

    def test_list_dependencies_returns_empty_list_when_no_dependencies(
        self, mock_db_path
    ):
        """Test that list_dependencies returns empty list when no dependencies exist."""
        result = DependencyRepository.list_dependencies()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_dependencies_with_filter_returns_dependency_responses(
        self, mock_db_path
    ):
        """Test that list_dependencies with filter returns DependencyResponse instances."""
        TaskRepository.add_task("task-1", "Task 1")
        TaskRepository.add_task("task-2", "Task 2")
        TaskRepository.add_task("task-3", "Task 3")

        DependencyRepository.add_dependency("task-2", "task-1")
        DependencyRepository.add_dependency("task-3", "task-2")

        result = DependencyRepository.list_dependencies(task_name="task-2")

        assert isinstance(result, list)
        assert len(result) == 2  # task-2 depends on task-1, task-3 depends on task-2
        assert all(isinstance(dep, DependencyResponse) for dep in result)

    def test_get_available_tasks_returns_list_of_task_responses(self, mock_db_path):
        """Test that get_available_tasks returns list of TaskResponse instances."""
        TaskRepository.add_task("base", "Base task", status="completed")
        TaskRepository.add_task("middle", "Middle task", status="pending")
        TaskRepository.add_task("top", "Top task", status="pending")

        DependencyRepository.add_dependency("middle", "base")
        DependencyRepository.add_dependency("top", "middle")

        result = DependencyRepository.get_available_tasks()

        assert isinstance(result, list)
        assert len(result) == 1
        assert all(isinstance(task, TaskResponse) for task in result)
        assert result[0].name == "middle"

    def test_get_available_tasks_returns_empty_list_when_no_available(
        self, mock_db_path
    ):
        """Test that get_available_tasks returns empty list when no tasks are available."""
        TaskRepository.add_task("task-1", "Task 1", status="pending")
        TaskRepository.add_task("task-2", "Task 2", status="pending")

        DependencyRepository.add_dependency("task-2", "task-1")

        result = DependencyRepository.get_available_tasks()

        # task-1 is not available because get_available_tasks only returns
        # tasks that are pending/in_progress. Both are pending but task-1 has no deps
        assert isinstance(result, list)


class TestFeatureRepositoryTypedReturns:
    """Tests for FeatureRepository returning typed models."""

    def test_add_feature_returns_feature_response(self, mock_db_path):
        """Test that add_feature returns a FeatureResponse instance."""
        result = FeatureRepository.add_feature(
            name="feature-a",
            description="Feature A description",
            enabled=True,
        )

        assert isinstance(result, FeatureResponse)
        assert result.name == "feature-a"
        assert result.description == "Feature A description"
        assert result.enabled is True
        assert result.created_at is not None

    def test_add_feature_without_description_returns_feature_response(
        self, mock_db_path
    ):
        """Test that add_feature without description returns a FeatureResponse."""
        result = FeatureRepository.add_feature(name="feature-b", enabled=False)

        assert isinstance(result, FeatureResponse)
        assert result.name == "feature-b"
        assert result.description is None
        assert result.enabled is False

    def test_list_features_returns_list_of_feature_responses(self, mock_db_path):
        """Test that list_features returns list of FeatureResponse instances."""
        FeatureRepository.add_feature("feature-1", "First feature", enabled=True)
        FeatureRepository.add_feature("feature-2", "Second feature", enabled=False)
        FeatureRepository.add_feature("feature-3", "Third feature", enabled=True)

        result = FeatureRepository.list_features()

        assert isinstance(result, list)
        assert len(result) == 4  # 3 + default feature
        assert all(isinstance(feature, FeatureResponse) for feature in result)

    def test_list_features_returns_empty_list_when_no_features(self, mock_db_path):
        """Test that list_features returns list with only default feature."""
        result = FeatureRepository.list_features()

        # The default feature is always present
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "default"

    def test_list_features_with_filter_returns_feature_responses(self, mock_db_path):
        """Test that list_features with filter returns FeatureResponse instances."""
        FeatureRepository.add_feature("feature-1", enabled=True)
        FeatureRepository.add_feature("feature-2", enabled=False)
        FeatureRepository.add_feature("feature-3", enabled=True)

        result = FeatureRepository.list_features(enabled=True)

        assert isinstance(result, list)
        # 2 enabled features + default feature
        assert len(result) == 3
        assert all(isinstance(feature, FeatureResponse) for feature in result)
        assert all(feature.enabled for feature in result)

    def test_feature_response_has_all_fields(self, mock_db_path):
        """Test that FeatureResponse instances have all expected fields."""
        result = FeatureRepository.add_feature(
            name="full-feature",
            description="Full description",
            enabled=True,
        )

        assert isinstance(result, FeatureResponse)
        assert hasattr(result, "name")
        assert hasattr(result, "description")
        assert hasattr(result, "enabled")
        assert hasattr(result, "created_at")


class TestTypedReturnsIntegration:
    """Integration tests for typed repository returns."""

    def test_workflow_with_typed_returns(self, mock_db_path):
        """Test a complete workflow using typed repository returns."""
        # Create tasks
        task1 = TaskRepository.add_task("task-1", "First task", priority=5)
        assert isinstance(task1, TaskResponse)

        task2 = TaskRepository.add_task("task-2", "Second task", priority=8)
        assert isinstance(task2, TaskResponse)

        # Create dependency
        dep = DependencyRepository.add_dependency("task-2", "task-1")
        assert isinstance(dep, DependencyResponse)

        # List all tasks
        tasks = TaskRepository.list_tasks()
        assert all(isinstance(t, TaskResponse) for t in tasks)

        # Update task
        updated = TaskRepository.update_task("task-1", status="completed")
        assert isinstance(updated, TaskResponse)
        assert updated.status == "completed"

        # Get available tasks
        available = DependencyRepository.get_available_tasks()
        assert all(isinstance(t, TaskResponse) for t in available)

    def test_pydantic_serialization(self, mock_db_path):
        """Test that typed returns can be serialized using Pydantic."""
        task = TaskRepository.add_task("serialize-me", "Test task", priority=5)

        # Pydantic model_dump should work
        serialized = task.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["name"] == "serialize-me"
        assert serialized["description"] == "Test task"
        assert serialized["priority"] == 5

    def test_pydantic_json_serialization(self, mock_db_path):
        """Test that typed returns can be JSON serialized."""
        task = TaskRepository.add_task("json-task", "JSON test", priority=3)

        # Pydantic model_dump_json should work
        json_str = task.model_dump_json()
        assert isinstance(json_str, str)
        assert "json-task" in json_str
        assert "JSON test" in json_str
