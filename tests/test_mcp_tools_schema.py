"""
Tests for MCP tool schemas.
"""

import asyncio

from fastmcp import FastMCP

from tasktree_mcp.tools import register_all_tools


def _load_tools():
    mcp = FastMCP("tasktree")
    register_all_tools(mcp)
    return asyncio.run(mcp.get_tools())


def test_add_task_schema_includes_tests_required():
    """Ensure add_task exposes tests_required in MCP schema."""
    tools = _load_tools()
    tool = tools["add_task"]
    properties = tool.parameters.get("properties", {})

    assert "tests_required" in properties


def test_update_task_schema_includes_tests_required():
    """Ensure update_task exposes tests_required in MCP schema."""
    tools = _load_tools()
    tool = tools["update_task"]
    properties = tool.parameters.get("properties", {})

    assert "tests_required" in properties
