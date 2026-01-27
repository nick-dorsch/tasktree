# TaskTree MCP Server

A Model Context Protocol (MCP) server that provides tools for querying and managing tasks in the TaskTree SQLite database.

## Installation

1. Ensure `uv` is installed on your system
2. Install dependencies:
```bash
uv sync
```

3. Ensure the TaskTree database exists at `data/tasktree.db`

## Available Tools

### Task Management
- `list_tasks(status=None, priority_min=None, feature_name=None)` - List tasks with optional filtering
- `get_task(name)` - Get a specific task by name
- `add_task(name, description, priority=0, status="pending", dependencies=None, specification=None, feature_name="misc", tests_required=True)` - Add a new task
- `update_task(name, description=None, status=None, priority=None, specification=None, tests_required=None)` - Update an existing task
- `delete_task(name)` - Delete a task

### Dependency Management
- `list_dependencies(task_name=None)` - List task dependencies
- `add_dependency(task_name, depends_on_task_name)` - Add a dependency relationship
- `remove_dependency(task_name, depends_on_task_name)` - Remove a dependency

### Utility Tools
- `get_available_tasks()` - Get tasks that can be started (no uncompleted dependencies)

### tests_required Flag

Use `tests_required=False` when a task does not involve testable code (for example: documentation-only updates or content changes). Leave it as `True` for normal code changes so downstream automation can expect tests to run.

## Usage

### Running the Server
```bash
uv run python src/tasktree/server.py
```

### Testing the Server
```bash
uv run python src/tasktree/server.py --test
```

## Snapshot Workflow

TaskTree keeps the SQLite database (`.tasktree/tasktree.db`) out of git. Use JSONL
snapshots for collaboration and rehydrating local state.

```bash
task snapshot-export
task snapshot-import
```

Snapshots are written to `.tasktree/tasktree.snapshot.jsonl` by default. Override the
location with `TASKTREE_SNAPSHOT_PATH=/absolute/path/to/tasktree.snapshot.jsonl`. Import
overwrites the local database by default; set `OVERWRITE=false` to skip overwriting.

## Integration with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "tasktree": {
      "command": "uv",
       "args": ["run", "python", "/path/to/tasktree/src/tasktree/server.py"],
       "cwd": "/path/to/tasktree"
    }
  }
}
```

## Database Schema

### Tasks Table
- `name` (TEXT PRIMARY KEY) - Unique task identifier
- `description` (TEXT) - Task description
- `status` (TEXT) - 'pending', 'in_progress', or 'completed'
- `priority` (INTEGER) - 0-10, higher is more important
- `tests_required` (INTEGER) - 0 or 1, whether tests are required
- `created_at` (TIMESTAMP) - When task was created
- `started_at` (TIMESTAMP) - When work began
- `completed_at` (TIMESTAMP) - When task was completed

### Dependencies Table
- `task_name` (TEXT) - The dependent task
- `depends_on_task_name` (TEXT) - The prerequisite task
- Prevents circular dependencies via database triggers
