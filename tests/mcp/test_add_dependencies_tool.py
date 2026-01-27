"""
Tests for the add_dependencies MCP tool.
"""

from pathlib import Path
from typing import Any, cast

import pytest

from tasktree.core.database import DependencyRepository, TaskRepository
from tasktree.mcp.tools import register_dependency_tools


class FakeMCP:
    """Minimal MCP implementation for registering tools."""

    def __init__(self) -> None:
        self.tools = {}

    def tool(self):
        """Capture tool registrations in a dict."""

        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


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


def get_dependency_tools():
    """Register dependency tools and return the tool mapping."""
    mcp = FakeMCP()
    register_dependency_tools(cast(Any, mcp))
    return mcp.tools


def test_add_dependencies_tool_registration():
    """Test that add_dependencies replaces add_dependency."""
    tools = get_dependency_tools()

    assert "add_dependencies" in tools
    assert "add_dependency" not in tools


def test_add_dependencies_tool_creates_multiple(mock_db_path):
    """Test that add_dependencies creates multiple dependencies."""
    tools = get_dependency_tools()

    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")

    result = tools["add_dependencies"]("task-c", ["task-a", "task-b"])

    assert result is True

    deps = DependencyRepository.list_dependencies("task-c")
    assert len(deps) == 2
    assert {dep.depends_on_task_name for dep in deps} == {"task-a", "task-b"}


def test_add_dependencies_tool_reports_failures(mock_db_path):
    """Test that add_dependencies reports failures but still inserts successes."""
    tools = get_dependency_tools()

    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")

    with pytest.raises(ValueError, match="missing-task"):
        tools["add_dependencies"]("task-b", ["task-a", "missing-task"])

    deps = DependencyRepository.list_dependencies("task-b")
    assert len(deps) == 1
    assert deps[0].task_name == "task-b"
    assert deps[0].depends_on_task_name == "task-a"
