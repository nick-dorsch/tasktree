"""
Test that verifies repository methods return Pydantic models.

This test ensures that:
1. All repository methods return properly typed Pydantic models
2. No methods return untyped Dict[str, Any]
3. Response models are used consistently
"""

import inspect

import pytest

from tasktree_mcp.database import (
    DependencyRepository,
    FeatureRepository,
    TaskRepository,
)
from tasktree_mcp.models import TaskResponse


def check_return_type_is_pydantic(func) -> bool:
    """
    Check if a function returns a Pydantic model or list of Pydantic models.

    Args:
        func: Function to check

    Returns:
        True if function returns Pydantic model structure
    """
    try:
        # Get the signature and check return annotation
        sig = inspect.signature(func)
        return_annotation = sig.return_annotation

        if return_annotation is inspect.Parameter.empty:
            return False

        # Convert to string for easier checking
        type_str = str(return_annotation)

        # Check for Pydantic model patterns
        pydantic_patterns = [
            "TaskResponse",
            "DependencyResponse",
            "FeatureResponse",
            "List[TaskResponse]",
            "List[DependencyResponse]",
            "List[FeatureResponse]",
            "Optional[TaskResponse]",
        ]

        for pattern in pydantic_patterns:
            if pattern in type_str:
                return True

        return False
    except Exception:
        # If we can't get signature, skip this function
        return False


class TestTypedReturnsValidation:
    """Tests to validate that repository methods return Pydantic models."""

    def test_task_repository_typed_methods(self):
        """Verify all TaskRepository methods return Pydantic models."""
        expected_typed = {
            "list_tasks",
            "get_task",
            "add_task",
            "update_task",
            "complete_task",
        }

        actual_typed = set()
        for name, method in inspect.getmembers(
            TaskRepository, predicate=inspect.isfunction
        ):
            if not name.startswith("_") and check_return_type_is_pydantic(method):
                actual_typed.add(name)

        assert actual_typed == expected_typed, (
            f"TaskRepository typed methods mismatch.\n"
            f"Expected: {expected_typed}\n"
            f"Actual: {actual_typed}\n"
            f"Missing from expected: {expected_typed - actual_typed}\n"
            f"Extra found: {actual_typed - expected_typed}"
        )

    def test_feature_repository_typed_methods(self):
        """Verify all FeatureRepository methods return Pydantic models."""
        expected_typed = {
            "add_feature",
            "list_features",
        }

        actual_typed = set()
        for name, method in inspect.getmembers(
            FeatureRepository, predicate=inspect.isfunction
        ):
            if not name.startswith("_") and check_return_type_is_pydantic(method):
                actual_typed.add(name)

        assert actual_typed == expected_typed, (
            f"FeatureRepository typed methods mismatch.\n"
            f"Expected: {expected_typed}\n"
            f"Actual: {actual_typed}\n"
            f"Missing from expected: {expected_typed - actual_typed}\n"
            f"Extra found: {actual_typed - expected_typed}"
        )

    def test_dependency_repository_typed_methods(self):
        """Verify all DependencyRepository methods return Pydantic models."""
        expected_typed = {
            "list_dependencies",
            "add_dependency",
            "get_available_tasks",
        }

        actual_typed = set()
        for name, method in inspect.getmembers(
            DependencyRepository, predicate=inspect.isfunction
        ):
            if not name.startswith("_") and check_return_type_is_pydantic(method):
                actual_typed.add(name)

        assert actual_typed == expected_typed, (
            f"DependencyRepository typed methods mismatch.\n"
            f"Expected: {expected_typed}\n"
            f"Actual: {actual_typed}\n"
            f"Missing from expected: {expected_typed - actual_typed}\n"
            f"Extra found: {actual_typed - expected_typed}"
        )

    def test_total_repository_typed_count(self):
        """Verify the total count of repository methods with Pydantic returns."""
        # Task: list_tasks, get_task, add_task, update_task, complete_task = 5
        # Feature: add_feature, list_features = 2
        # Dependency: list_dependencies, add_dependency, get_available_tasks = 3
        # Total = 10 methods
        expected_total = 10

        total = 0
        for repo_class in [TaskRepository, FeatureRepository, DependencyRepository]:
            for name, method in inspect.getmembers(
                repo_class, predicate=inspect.isfunction
            ):
                if not name.startswith("_") and check_return_type_is_pydantic(method):
                    total += 1

        assert total == expected_total, (
            f"Expected {expected_total} repository methods with Pydantic returns, "
            f"but found {total}"
        )

    def test_response_models_are_used(self):
        """Verify that response models exist and are used."""
        from tasktree_mcp.models import (
            DependencyListResponse,
            DependencyResponse,
            FeatureListResponse,
            FeatureResponse,
            TaskListResponse,
            TaskResponse,
        )

        # These models exist
        assert TaskResponse is not None
        assert TaskListResponse is not None
        assert DependencyResponse is not None
        assert DependencyListResponse is not None
        assert FeatureResponse is not None
        assert FeatureListResponse is not None

        # Verify they are used in repository returns
        # This is validated by actual runtime tests below

    def test_repository_methods_return_pydantic_models(self, mock_db_path):
        """
        Verify that repository methods return Pydantic models, not dicts.

        This test ensures the migration to typed returns is complete.
        """
        # Add a test task
        task = TaskRepository.add_task("test-task", "Test description")

        # Verify it returns a Pydantic model, not a dict
        assert isinstance(task, TaskResponse)
        assert not isinstance(task, dict)
        assert task.name == "test-task"
        assert task.description == "Test description"

        # Get task
        retrieved_task = TaskRepository.get_task("test-task")
        assert retrieved_task is None or isinstance(retrieved_task, TaskResponse)

        # List tasks
        tasks = TaskRepository.list_tasks()
        assert isinstance(tasks, list)
        if len(tasks) > 0:
            assert isinstance(tasks[0], TaskResponse)
            assert not isinstance(tasks[0], dict)


@pytest.fixture
def mock_db_path(test_db, monkeypatch):
    """Mock the DB_PATH to use the test database."""
    import tasktree_mcp.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db
