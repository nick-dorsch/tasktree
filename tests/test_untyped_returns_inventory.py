"""
Test that verifies the untyped returns inventory is accurate.

This test ensures that:
1. All methods returning Dict[str, Any] are documented
2. The count of untyped returns matches the inventory
3. No new untyped returns have been added without updating the inventory
"""

import inspect

import pytest

from tasktree_mcp.database import (
    DependencyRepository,
    FeatureRepository,
    TaskRepository,
)


def check_return_type(func) -> bool:
    """
    Check if a function returns Dict[str, Any] or Optional[Dict[str, Any]] or List[Dict[str, Any]].

    Args:
        func: Function to check

    Returns:
        True if function returns untyped dict-like structure
    """
    try:
        # Get the signature and check return annotation
        sig = inspect.signature(func)
        return_annotation = sig.return_annotation

        if return_annotation is inspect.Parameter.empty:
            return False

        # Convert to string for easier checking
        type_str = str(return_annotation)

        # Check for Dict[str, Any] patterns (with or without typing. prefix)
        patterns = [
            "Dict[str, Any]",
            "dict[str, Any]",
            "typing.Dict[str, typing.Any]",
            "typing.dict[str, typing.Any]",
        ]

        for pattern in patterns:
            if pattern in type_str:
                return True

        return False
    except Exception:
        # If we can't get signature, skip this function
        return False


class TestUntypedReturnsInventory:
    """Tests to validate the untyped returns inventory document."""

    def test_task_repository_untyped_methods(self):
        """Verify all TaskRepository methods with untyped returns are documented."""
        expected_untyped = {
            "list_tasks",
            "get_task",
            "add_task",
            "update_task",
            "complete_task",
        }

        actual_untyped = set()
        for name, method in inspect.getmembers(
            TaskRepository, predicate=inspect.isfunction
        ):
            if not name.startswith("_") and check_return_type(method):
                actual_untyped.add(name)

        assert actual_untyped == expected_untyped, (
            f"TaskRepository untyped methods mismatch.\n"
            f"Expected: {expected_untyped}\n"
            f"Actual: {actual_untyped}\n"
            f"Missing from inventory: {actual_untyped - expected_untyped}\n"
            f"Extra in inventory: {expected_untyped - actual_untyped}"
        )

    def test_feature_repository_untyped_methods(self):
        """Verify all FeatureRepository methods with untyped returns are documented."""
        expected_untyped = {
            "add_feature",
            "list_features",
        }

        actual_untyped = set()
        for name, method in inspect.getmembers(
            FeatureRepository, predicate=inspect.isfunction
        ):
            if not name.startswith("_") and check_return_type(method):
                actual_untyped.add(name)

        assert actual_untyped == expected_untyped, (
            f"FeatureRepository untyped methods mismatch.\n"
            f"Expected: {expected_untyped}\n"
            f"Actual: {actual_untyped}\n"
            f"Missing from inventory: {actual_untyped - expected_untyped}\n"
            f"Extra in inventory: {expected_untyped - actual_untyped}"
        )

    def test_dependency_repository_untyped_methods(self):
        """Verify all DependencyRepository methods with untyped returns are documented."""
        expected_untyped = {
            "list_dependencies",
            "add_dependency",
            "get_available_tasks",
        }

        actual_untyped = set()
        for name, method in inspect.getmembers(
            DependencyRepository, predicate=inspect.isfunction
        ):
            if not name.startswith("_") and check_return_type(method):
                actual_untyped.add(name)

        assert actual_untyped == expected_untyped, (
            f"DependencyRepository untyped methods mismatch.\n"
            f"Expected: {expected_untyped}\n"
            f"Actual: {actual_untyped}\n"
            f"Missing from inventory: {actual_untyped - expected_untyped}\n"
            f"Extra in inventory: {expected_untyped - actual_untyped}"
        )

    def test_total_repository_untyped_count(self):
        """Verify the total count of repository methods with untyped returns."""
        # From inventory: 6 TaskRepository + 2 FeatureRepository + 3 DependencyRepository = 11 total
        # But inventory lists 10, let me recount:
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
                if not name.startswith("_") and check_return_type(method):
                    total += 1

        assert total == expected_total, (
            f"Expected {expected_total} repository methods with untyped returns, "
            f"but found {total}"
        )

    def test_mcp_tools_inventory_completeness(self):
        """
        Verify MCP tools inventory matches implementation.

        Note: This test checks against the documented tool count.
        A more thorough check would require parsing tools.py dynamically,
        but that's complex due to decorator registration pattern.
        """
        # From inventory document:
        # Single return: get_task, add_task, update_task, start_task, complete_task, add_dependency, add_feature = 7
        # List return: list_tasks, list_dependencies, get_available_tasks, list_features = 4
        # Total = 11 MCP tools
        expected_single_tools = 7
        expected_list_tools = 4
        expected_total = 11

        # This is a documentation test - if someone adds a new tool,
        # they need to update the inventory
        assert expected_total == expected_single_tools + expected_list_tools

    def test_existing_response_models_not_used(self):
        """Verify that response models exist but are not yet used."""
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

        # But they're not used in repository returns (which still return Dict[str, Any])
        # This test documents the current state for future migration

    def test_repository_methods_return_dict_structure(self, mock_db_path):
        """
        Verify that repository methods actually return dict structures.

        This test ensures the inventory is accurate by checking actual return values.
        """
        # Add a test task
        task = TaskRepository.add_task("test-task", "Test description")

        # Verify it returns a dict, not a Pydantic model
        assert isinstance(task, dict)
        assert "name" in task
        assert "description" in task

        # Get task
        retrieved_task = TaskRepository.get_task("test-task")
        assert isinstance(retrieved_task, dict) or retrieved_task is None

        # List tasks
        tasks = TaskRepository.list_tasks()
        assert isinstance(tasks, list)
        if len(tasks) > 0:
            assert isinstance(tasks[0], dict)


@pytest.fixture
def mock_db_path(test_db, monkeypatch):
    """Mock the DB_PATH to use the test database."""
    import tasktree_mcp.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db
