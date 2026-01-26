"""
Tests for Pydantic response models.

This test suite validates that response models can be created from
database dictionaries and handle all expected fields correctly.
"""

import pytest

from tasktree_mcp.models import (
    DependencyListResponse,
    DependencyResponse,
    FeatureListResponse,
    FeatureResponse,
    TaskListResponse,
    TaskResponse,
    TaskUpdateResponse,
)


class TestTaskResponse:
    """Tests for TaskResponse model."""

    def test_task_response_from_dict_basic(self):
        """Test creating TaskResponse from a basic database dictionary."""
        data = {
            "name": "test-task",
            "description": "Test description",
            "details": None,
            "feature_name": "default",
            "tests_required": True,
            "priority": 5,
            "status": "pending",
            "created_at": "2026-01-26 08:00:00",
            "updated_at": "2026-01-26 08:00:00",
            "started_at": None,
            "completed_at": None,
        }

        response = TaskResponse.from_dict(data)

        assert response.name == "test-task"
        assert response.description == "Test description"
        assert response.details is None
        assert response.feature_name == "default"
        assert response.tests_required is True
        assert response.priority == 5
        assert response.status == "pending"
        assert response.created_at == "2026-01-26 08:00:00"
        assert response.updated_at == "2026-01-26 08:00:00"
        assert response.started_at is None
        assert response.completed_at is None

    def test_task_response_from_dict_with_all_fields(self):
        """Test TaskResponse with all optional fields populated."""
        data = {
            "name": "completed-task",
            "description": "A completed task",
            "details": "Implementation details",
            "feature_name": "feature-a",
            "tests_required": False,
            "priority": 8,
            "status": "completed",
            "created_at": "2026-01-26 07:00:00",
            "updated_at": "2026-01-26 08:30:00",
            "started_at": "2026-01-26 07:30:00",
            "completed_at": "2026-01-26 08:00:00",
        }

        response = TaskResponse.from_dict(data)

        assert response.name == "completed-task"
        assert response.description == "A completed task"
        assert response.details == "Implementation details"
        assert response.feature_name == "feature-a"
        assert response.tests_required is False
        assert response.priority == 8
        assert response.status == "completed"
        assert response.created_at == "2026-01-26 07:00:00"
        assert response.updated_at == "2026-01-26 08:30:00"
        assert response.started_at == "2026-01-26 07:30:00"
        assert response.completed_at == "2026-01-26 08:00:00"

    def test_task_response_dict_serialization(self):
        """Test that TaskResponse can be serialized back to dict."""
        data = {
            "name": "test-task",
            "description": "Test description",
            "details": None,
            "feature_name": "default",
            "tests_required": True,
            "priority": 5,
            "status": "pending",
            "created_at": "2026-01-26 08:00:00",
            "updated_at": "2026-01-26 08:00:00",
            "started_at": None,
            "completed_at": None,
        }

        response = TaskResponse.from_dict(data)
        serialized = response.model_dump()

        assert serialized["name"] == "test-task"
        assert serialized["description"] == "Test description"
        assert serialized["priority"] == 5
        assert serialized["tests_required"] is True

    def test_task_response_validation_priority_bounds(self):
        """Test that TaskResponse validates priority bounds."""
        # Valid priorities
        valid_data = {
            "name": "task",
            "description": "Test",
            "feature_name": "default",
            "tests_required": True,
            "priority": 10,
            "status": "pending",
            "created_at": None,
            "updated_at": None,
            "started_at": None,
            "completed_at": None,
        }
        response = TaskResponse(**valid_data)
        assert response.priority == 10

        # Invalid priority (too high)
        invalid_data = valid_data.copy()
        invalid_data["priority"] = 11
        with pytest.raises(ValueError):
            TaskResponse(**invalid_data)

        # Invalid priority (negative)
        invalid_data = valid_data.copy()
        invalid_data["priority"] = -1
        with pytest.raises(ValueError):
            TaskResponse(**invalid_data)


class TestTaskListResponse:
    """Tests for TaskListResponse model."""

    def test_task_list_response_from_list_empty(self):
        """Test creating TaskListResponse from an empty list."""
        data = []
        response = TaskListResponse.from_list(data)

        assert response.tasks == []
        assert len(response.tasks) == 0

    def test_task_list_response_from_list_single(self):
        """Test creating TaskListResponse from a single-item list."""
        data = [
            {
                "name": "task-1",
                "description": "First task",
                "details": None,
                "feature_name": "default",
                "tests_required": True,
                "priority": 5,
                "status": "pending",
                "created_at": "2026-01-26 08:00:00",
                "updated_at": "2026-01-26 08:00:00",
                "started_at": None,
                "completed_at": None,
            }
        ]

        response = TaskListResponse.from_list(data)

        assert len(response.tasks) == 1
        assert response.tasks[0].name == "task-1"
        assert response.tasks[0].description == "First task"

    def test_task_list_response_from_list_multiple(self):
        """Test creating TaskListResponse from multiple items."""
        data = [
            {
                "name": "task-1",
                "description": "First task",
                "details": None,
                "feature_name": "default",
                "tests_required": True,
                "priority": 5,
                "status": "pending",
                "created_at": "2026-01-26 08:00:00",
                "updated_at": "2026-01-26 08:00:00",
                "started_at": None,
                "completed_at": None,
            },
            {
                "name": "task-2",
                "description": "Second task",
                "details": "Details",
                "feature_name": "feature-a",
                "tests_required": False,
                "priority": 8,
                "status": "in_progress",
                "created_at": "2026-01-26 08:00:00",
                "updated_at": "2026-01-26 08:00:00",
                "started_at": "2026-01-26 08:10:00",
                "completed_at": None,
            },
        ]

        response = TaskListResponse.from_list(data)

        assert len(response.tasks) == 2
        assert response.tasks[0].name == "task-1"
        assert response.tasks[1].name == "task-2"
        assert response.tasks[1].status == "in_progress"


class TestTaskUpdateResponse:
    """Tests for TaskUpdateResponse model."""

    def test_task_update_response_with_task(self):
        """Test creating TaskUpdateResponse with a task."""
        data = {
            "name": "updated-task",
            "description": "Updated description",
            "details": None,
            "feature_name": "default",
            "tests_required": True,
            "priority": 7,
            "status": "in_progress",
            "created_at": "2026-01-26 08:00:00",
            "updated_at": "2026-01-26 08:30:00",
            "started_at": "2026-01-26 08:30:00",
            "completed_at": None,
        }

        response = TaskUpdateResponse.from_dict(data)

        assert response.task is not None
        assert response.task.name == "updated-task"
        assert response.task.status == "in_progress"

    def test_task_update_response_with_none(self):
        """Test creating TaskUpdateResponse when task is not found."""
        response = TaskUpdateResponse.from_dict(None)

        assert response.task is None


class TestDependencyResponse:
    """Tests for DependencyResponse model."""

    def test_dependency_response_from_dict(self):
        """Test creating DependencyResponse from a database dictionary."""
        data = {
            "task_name": "task-a",
            "depends_on_task_name": "task-b",
        }

        response = DependencyResponse.from_dict(data)

        assert response.task_name == "task-a"
        assert response.depends_on_task_name == "task-b"

    def test_dependency_response_serialization(self):
        """Test that DependencyResponse can be serialized."""
        data = {
            "task_name": "task-a",
            "depends_on_task_name": "task-b",
        }

        response = DependencyResponse.from_dict(data)
        serialized = response.model_dump()

        assert serialized["task_name"] == "task-a"
        assert serialized["depends_on_task_name"] == "task-b"


class TestDependencyListResponse:
    """Tests for DependencyListResponse model."""

    def test_dependency_list_response_from_list_empty(self):
        """Test creating DependencyListResponse from empty list."""
        data = []
        response = DependencyListResponse.from_list(data)

        assert response.dependencies == []
        assert len(response.dependencies) == 0

    def test_dependency_list_response_from_list_multiple(self):
        """Test creating DependencyListResponse from multiple items."""
        data = [
            {"task_name": "task-a", "depends_on_task_name": "task-b"},
            {"task_name": "task-a", "depends_on_task_name": "task-c"},
            {"task_name": "task-c", "depends_on_task_name": "task-b"},
        ]

        response = DependencyListResponse.from_list(data)

        assert len(response.dependencies) == 3
        assert response.dependencies[0].task_name == "task-a"
        assert response.dependencies[0].depends_on_task_name == "task-b"
        assert response.dependencies[2].task_name == "task-c"


class TestFeatureResponse:
    """Tests for FeatureResponse model."""

    def test_feature_response_from_dict_basic(self):
        """Test creating FeatureResponse from a database dictionary."""
        data = {
            "name": "feature-a",
            "description": "Feature A description",
            "enabled": True,
            "created_at": "2026-01-26 08:00:00",
        }

        response = FeatureResponse.from_dict(data)

        assert response.name == "feature-a"
        assert response.description == "Feature A description"
        assert response.enabled is True
        assert response.created_at == "2026-01-26 08:00:00"

    def test_feature_response_from_dict_no_description(self):
        """Test FeatureResponse with no description."""
        data = {
            "name": "feature-b",
            "description": None,
            "enabled": False,
            "created_at": "2026-01-26 08:00:00",
        }

        response = FeatureResponse.from_dict(data)

        assert response.name == "feature-b"
        assert response.description is None
        assert response.enabled is False


class TestFeatureListResponse:
    """Tests for FeatureListResponse model."""

    def test_feature_list_response_from_list_empty(self):
        """Test creating FeatureListResponse from empty list."""
        data = []
        response = FeatureListResponse.from_list(data)

        assert response.features == []
        assert len(response.features) == 0

    def test_feature_list_response_from_list_multiple(self):
        """Test creating FeatureListResponse from multiple items."""
        data = [
            {
                "name": "feature-a",
                "description": "Feature A",
                "enabled": True,
                "created_at": "2026-01-26 08:00:00",
            },
            {
                "name": "feature-b",
                "description": None,
                "enabled": False,
                "created_at": "2026-01-26 08:05:00",
            },
        ]

        response = FeatureListResponse.from_list(data)

        assert len(response.features) == 2
        assert response.features[0].name == "feature-a"
        assert response.features[0].enabled is True
        assert response.features[1].name == "feature-b"
        assert response.features[1].enabled is False
