#!/usr/bin/env python3
"""
TaskTree MCP Server
A Model Context Protocol server that provides tools for querying and managing tasks
in the TaskTree SQLite database.
"""

from fastmcp import FastMCP

from .database import get_db_connection
from .tools import register_all_tools

# Initialize MCP server
mcp = FastMCP("tasktree")

# Register all tools
register_all_tools(mcp)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Simple test mode - test database connection and queries
        print("Testing TaskTree MCP Server...")

        from .database import get_db_connection

        # Test basic database connection and queries
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Test all tasks query
            cursor.execute("SELECT * FROM tasks ORDER BY priority DESC, created_at ASC")
            all_tasks = [
                {key: row[key] for key in row.keys()} for row in cursor.fetchall()
            ]
            print(f"All tasks: {all_tasks}")

            # Test available tasks query
            cursor.execute(
                """
                SELECT t.* FROM tasks t
                WHERE t.status != 'completed'
                AND NOT EXISTS (
                    SELECT 1 FROM dependencies d
                    WHERE d.task_name = t.name
                    AND EXISTS (
                        SELECT 1 FROM tasks t2
                        WHERE t2.name = d.depends_on_task_name
                        AND t2.status != 'completed'
                    )
                )
                ORDER BY t.priority DESC, t.created_at ASC
                """
            )
            available_tasks = [
                {key: row[key] for key in row.keys()} for row in cursor.fetchall()
            ]
            print(f"Available tasks: {available_tasks}")

        print("Test completed successfully!")
    else:
        # Run the MCP server
        mcp.run()
