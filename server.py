#!/usr/bin/env python3
"""
TaskTree MCP Server
A Model Context Protocol server that provides tools for querying and managing tasks
in the TaskTree SQLite database.
"""

from fastmcp import FastMCP

from tasktree_mcp.tools import register_all_tools

# Initialize MCP server
mcp = FastMCP("tasktree")

# Register all tools
register_all_tools(mcp)


if __name__ == "__main__":
    mcp.run()
