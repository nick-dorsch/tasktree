#!/usr/bin/env python3
"""
TaskTree CLI - Command-line interface for TaskTree.

Provides commands for:
- init: Initialize TaskTree database
- start: Run graph web server
- reset: Reset database (preserve schema)
"""

import sqlite3
from pathlib import Path
from typing import Optional

import typer

from tasktree.core.paths import get_db_path, get_snapshot_path
from tasktree.db.init import initialize_database
from tasktree.io.snapshot import import_snapshot

# Create the main CLI app
cli = typer.Typer(
    name="tasktree",
    help="TaskTree CLI - Manage task dependencies and run graph server",
    no_args_is_help=True,
)


@cli.command()
def init(
    seed: bool = typer.Option(
        False,
        "--seed",
        "-s",
        help="Initialize with sample seed data",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing database",
    ),
) -> None:
    """
    Initialize TaskTree database.

    Creates a new TaskTree database with schemas and views applied.
    By default creates the database in .tasktree/tasktree.db relative to
    the repository root, or ~/.tasktree/tasktree.db if not in a repository.
    """
    db_path = get_db_path()

    if db_path.exists():
        if force:
            typer.echo(f"Overwriting existing database: {db_path}")
            db_path.unlink()
        else:
            typer.echo(f"Database already exists: {db_path}", err=True)
            typer.echo(
                "Use --force to overwrite or specify a different location.", err=True
            )
            raise typer.Exit(1)

    try:
        typer.echo(f"Initializing database at: {db_path}")
        initialize_database(db_path, apply_views_flag=True)
        typer.echo("✓ Database initialized successfully!")

        # Restore from snapshot if it exists
        snapshot_path = get_snapshot_path()
        if snapshot_path.exists():
            typer.echo(f"Restoring database from snapshot: {snapshot_path}")
            try:
                import_snapshot(db_path, snapshot_path, overwrite=False)
                typer.echo("✓ Database restored from snapshot.")
            except ValueError as e:
                typer.echo(f"Error importing snapshot: {e}", err=True)
                raise typer.Exit(1)

        if seed:
            typer.echo("Seed data functionality not yet implemented.")

    except sqlite3.Error as e:
        typer.echo(f"Error initializing database: {e}", err=True)
        raise typer.Exit(1)
    except PermissionError as e:
        typer.echo(f"Permission error: {e}", err=True)
        raise typer.Exit(1)


@cli.command()
def start(
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port for the web server",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="Run server in background (not yet implemented)",
    ),
    db_path: Optional[Path] = typer.Option(
        None,
        "--db",
        help="Path to database file (uses default if not specified)",
    ),
) -> None:
    """
    Start the TaskTree graph web server.

    Starts a web server that provides both a task list panel and interactive
    graph visualization of task dependencies.
    """
    from tasktree.graph.server import run_server

    target_db_path = db_path or get_db_path()

    if not target_db_path.exists():
        typer.echo(f"Database not found: {target_db_path}", err=True)
        typer.echo("Run 'tasktree init' to create the database first.", err=True)
        raise typer.Exit(1)

    if background:
        typer.echo("Background mode not yet implemented. Use foreground mode.")
        background = False

    try:
        run_server(port, target_db_path)
    except KeyboardInterrupt:
        typer.echo("\nServer stopped.")
    except Exception as e:
        typer.echo(f"Error starting server: {e}", err=True)
        raise typer.Exit(1)


@cli.command()
def refresh_views(
    db_path: Optional[Path] = typer.Option(
        None,
        "--db",
        help="Path to database file (uses default if not specified)",
    ),
) -> None:
    """
    Refresh all database views.

    Drops and recreates all views from the bundled SQL assets.
    Useful after modifying view definitions.
    """
    from tasktree.db.init import refresh_views as db_refresh_views

    target_db_path = db_path or get_db_path()

    if not target_db_path.exists():
        typer.echo(f"Database not found: {target_db_path}", err=True)
        typer.echo("Run 'tasktree init' to create the database first.", err=True)
        raise typer.Exit(1)

    try:
        typer.echo(f"Refreshing views in: {target_db_path}")
        db_refresh_views(target_db_path)
        typer.echo("✓ Views refreshed successfully!")
    except Exception as e:
        typer.echo(f"Error refreshing views: {e}", err=True)
        raise typer.Exit(1)


@cli.command()
def reset(
    confirm: bool = typer.Option(
        False,
        "--confirm",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Reset database (preserve schema, delete all data).

    Deletes all tasks, features, and dependencies while preserving the
    database schema and views. Useful for starting fresh without re-initializing.
    """
    db_path = get_db_path()

    # Check if database exists BEFORE prompting for confirmation
    if not db_path.exists():
        typer.echo(f"Database not found: {db_path}", err=True)
        typer.echo("Run 'tasktree init' to create the database first.", err=True)
        raise typer.Exit(1)

    if not confirm:
        if not typer.confirm(
            f"This will delete ALL data from {db_path}. Are you sure?"
        ):
            typer.echo("Operation cancelled.")
            raise typer.Exit()

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Delete all data while preserving schema
        conn.execute("DELETE FROM dependencies")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM features")

        conn.commit()
        conn.close()

        typer.echo("✓ Database reset successfully! All data has been cleared.")

    except sqlite3.Error as e:
        typer.echo(f"Error resetting database: {e}", err=True)
        raise typer.Exit(1)


@cli.command()
def mcp(
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="Port for SSE transport (runs in stdio mode if not specified)",
    ),
) -> None:
    """
    Start the Model Context Protocol (MCP) server.

    By default, runs using stdio transport. If --port is provided,
    runs using SSE transport on the specified port.
    """
    from tasktree.mcp.server import mcp as mcp_app

    if port:
        typer.echo(f"Starting MCP server with SSE transport on port {port}", err=True)
        mcp_app.run(transport="sse", port=port)
    else:
        typer.echo("Starting MCP server with stdio transport", err=True)
        mcp_app.run(transport="stdio")


if __name__ == "__main__":
    cli()
