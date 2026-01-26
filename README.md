# TaskTree

TaskTree is a SQL-first task and dependency tracker backed by SQLite, exposed as a
Model Context Protocol (MCP) server for agentic workflows. The database is the
source of truth: views and constraints encode dependency logic while Python provides
thin, typed wrappers.

## Key Ideas

- SQL-first dependency resolution with recursive CTEs and views.
- MCP tools for tasks, dependencies, and features.
- JSONL snapshot export/import for collaboration and rehydration.
- Optional graph visualization for the dependency DAG.

## Quick Start

1. Install dependencies with uv:

```bash
uv sync
```

2. Initialize the database (this overwrites the local database):

```bash
task init-db
```

Optional seed data:

```bash
task init-db SEED=true
```

3. Start the MCP server:

```bash
task mcp
```

## MCP Tools

Task management:
- `list_tasks(status=None, priority_min=None, feature_name=None)`
- `get_task(name)`
- `add_task(name, description, priority=0, status="pending", dependencies=None, details=None, feature_name="default", tests_required=True)`
- `update_task(name, description=None, status=None, priority=None, details=None, tests_required=None)`
- `delete_task(name)`
- `start_task(name)`
- `complete_task(name)`

Dependency management:
- `list_dependencies(task_name=None)`
- `add_dependency(task_name, depends_on_task_name)`
- `remove_dependency(task_name, depends_on_task_name)`
- `get_available_tasks()`

Feature management:
- `add_feature(name, description=None, enabled=True)`
- `list_features(enabled=None)`

## Database and Snapshot Paths

Database location resolution:
- `TASKTREE_DB_PATH` (absolute override)
- `.tasktree/tasktree.db` in the repo root
- `~/.tasktree/tasktree.db` fallback

Snapshot location resolution:
- `TASKTREE_SNAPSHOT_PATH` (absolute override)
- `.tasktree/tasktree.snapshot.jsonl` in the repo root
- `~/.tasktree/tasktree.snapshot.jsonl` fallback

## Snapshot Workflow

```bash
task snapshot-export
task snapshot-import
```

Import overwrites the local database by default. Use `OVERWRITE=false` to skip
overwriting when the database already exists.

## Graph Visualization

```bash
task graph-json
task web-graph
```

`task web-graph` launches a small server and opens a browser view. The static HTML
viewer is available at `scripts/graph-viewer.html`.

## Development

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Project Layout

```
tasktree/
├── src/tasktree_mcp/          # MCP server implementation
│   ├── database.py            # Repositories and DB access
│   ├── models.py              # Pydantic models
│   ├── tools.py               # MCP tool registration
│   ├── sql/                   # Schemas and views
│   └── snapshot.py            # JSONL snapshot IO
├── tests/                     # Pytest suite
├── Taskfile.yml               # Task runner commands
└── docs/                      # Supporting documentation
```
