"""
Tests for the delete_feature MCP tool.
"""

from pathlib import Path
from typing import Any, cast

import pytest

from tasktree.core.database import FeatureRepository
from tasktree.mcp.tools import register_feature_tools


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
    """
    import tasktree.core.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


def get_feature_tools():
    """Register feature tools and return the tool mapping."""
    mcp = FakeMCP()
    register_feature_tools(cast(Any, mcp))
    return mcp.tools


def test_delete_feature_tool_registration():
    """Test that delete_feature is registered."""
    tools = get_feature_tools()
    assert "delete_feature" in tools


def test_delete_feature_tool_success(mock_db_path):
    """Test that delete_feature tool successfully deletes a feature."""
    tools = get_feature_tools()

    FeatureRepository.add_feature(
        name="test-feature",
        description="Test Description",
        specification="Test Spec",
    )

    result = tools["delete_feature"]("test-feature")
    assert result is True
    assert FeatureRepository.get_feature("test-feature") is None


def test_delete_feature_tool_not_found(mock_db_path):
    """Test that delete_feature tool returns False for non-existent feature."""
    tools = get_feature_tools()
    result = tools["delete_feature"]("non-existent")
    assert result is False


def test_delete_feature_tool_misc_protection(mock_db_path):
    """Test that delete_feature tool protects the 'misc' feature."""
    tools = get_feature_tools()
    with pytest.raises(ValueError, match="The 'misc' feature cannot be deleted"):
        tools["delete_feature"]("misc")
