# AGENTS.md - Coding Agent Guidelines for TaskTree

This document provides essential information for AI coding agents (like Claude, Cursor, GitHub Copilot) working in the TaskTree repository.

## Project Overview

TaskTree is a **SQL-first** task execution system with complex dependency tracking, designed for agentic coding workflows. The architecture puts SQLite at the core, handling business logic through views, recursive CTEs, and SQL constraints. Python provides thin wrappers via FastMCP.

**Core Architecture:**
- SQLite handles dependency resolution, DAG validation, and complex queries
- Python provides minimal wrappers using FastMCP (Model Context Protocol)
- Pydantic models ensure type safety and validation at API boundaries
- Repository pattern abstracts database operations

## Package Management

**CRITICAL:** This project uses `uv` as the package manager. Always use `uv` commands:

```bash
# Install/sync dependencies
uv sync

# Add a new package (updates pyproject.toml and uv.lock)
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Run Python scripts/commands
uv run python script.py
uv run server.py
```

**Never use:** `pip install`, `pip freeze`, `python -m`, or bare `python`/`pytest` commands. Always prefix with `uv run`.

## Build/Lint/Test Commands

### Running Tests

```bash
# Run all tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_database.py

# Run a specific test function
uv run pytest tests/test_database.py::test_list_tasks

# Run with verbose output
uv run pytest -v

# Run with coverage (if configured)
uv run pytest --cov=src/tasktree_mcp
```

### Linting and Formatting

```bash
# Format code (auto-fix)
uv run ruff format .

# Lint code (check only)
uv run ruff check .

# Lint and auto-fix issues
uv run ruff check --fix .
```

### Database Operations

```bash
# Initialize database (clean slate)
# WARNING: This WIPES ALL DATABASE DATA! Always ask the user before running.
task init-db

# Initialize with seed data
# WARNING: This WIPES ALL DATABASE DATA! Always ask the user before running.
SEED=true task init-db

# Refresh SQL views after modifying sql/views/*.sql
task refresh-views

# Start the MCP server
task mcp
```

### Visualization and Debugging

```bash
# View dependency graph as JSON
task graph-json

# Draw dependency graph in terminal
task draw
```

## Code Style Guidelines

### General Principles

- **SQL-first design**: Implement complex logic in SQL (views, CTEs, constraints), not Python
- **Type safety**: Use type hints everywhere; leverage Pydantic for validation
- **Repository pattern**: Database access through `TaskRepository` and `DependencyRepository`
- **Immutability**: Prefer immutable data structures where possible

### Imports

Organize imports in three groups (separated by blank lines):

1. Standard library imports
2. Third-party imports (fastmcp, pydantic, etc.)
3. Local application imports (relative imports from same package)

**Example:**
```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .database import TaskRepository
from .models import Task, TaskStatus
```

### Formatting

- **Line length**: Default (~88-100 characters, Ruff default)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings (Ruff default)
- **Trailing commas**: Use in multi-line collections

### Types and Type Hints

**Always use type hints** on all functions, methods, and class attributes:

```python
def get_task(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific task by name."""
    ...

class TaskRepository:
    @staticmethod
    def list_tasks(
        status: Optional[str] = None, 
        priority_min: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        ...
```

**Use Pydantic for data validation:**
```python
from pydantic import BaseModel, Field, field_validator

class Task(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    priority: int = Field(default=0, ge=0, le=10)
    
    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if not 0 <= v <= 10:
            raise ValueError("Priority must be between 0 and 10")
        return v
```

### Naming Conventions

- **Functions/variables**: `snake_case` (e.g., `get_available_tasks`, `task_name`)
- **Classes**: `PascalCase` (e.g., `TaskRepository`, `TaskStatus`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DB_PATH`, `MAX_PRIORITY`)
- **Private methods**: Prefix with `_` (e.g., `_validate_dependencies`)
- **SQL identifiers**: `snake_case` for tables/columns (e.g., `depends_on_task_name`)

### Error Handling

**Raise specific exceptions with clear messages:**

```python
# Good
if not task:
    raise ValueError(f"Task '{task_name}' does not exist")

# Bad
if not task:
    raise Exception("Error")
```

**Handle SQLite integrity errors:**

```python
try:
    cursor.execute("INSERT INTO tasks ...", ...)
except sqlite3.IntegrityError as e:
    raise ValueError(f"Task with name '{name}' already exists") from e
```

**Use context managers for database connections:**

```python
with get_db_connection() as conn:
    cursor = conn.cursor()
    # ... database operations
    conn.commit()
```

### Docstrings

Use **Google-style docstrings** for all public functions/classes:

```python
def add_task(name: str, description: str, priority: int = 0) -> Dict[str, Any]:
    """
    Add a new task to the database.

    Args:
        name: Unique name for the task
        description: Description of what the task involves
        priority: Priority level (0-10, higher is more important)

    Returns:
        The created task dictionary

    Raises:
        ValueError: If task with name already exists
    """
    ...
```

## Testing Guidelines

- **Fixtures**: Use `test_db` and `test_db_connection` fixtures from `conftest.py`
- **Isolation**: Each test gets a fresh database (function-scoped fixtures)
- **Test structure**: Arrange-Act-Assert pattern
- **Database setup**: Schema automatically applied from `sql/schemas/*.sql`

**Example test:**

```python
def test_add_task(test_db: Path):
    """Test adding a task to the database."""
    # Arrange
    import tasktree_mcp.database as db
    import monkeypatch
    monkeypatch.setattr(db, "DB_PATH", test_db)
    
    # Act
    task = TaskRepository.add_task(
        name="test-task",
        description="Test description",
        priority=5
    )
    
    # Assert
    assert task["name"] == "test-task"
    assert task["priority"] == 5
```

## SQL Development

When modifying SQL:

1. **Schema changes**: Edit files in `sql/schemas/` (numbered: `001_tasks.sql`, `002_dependencies.sql`)
2. **View changes**: Edit files in `sql/views/` (numbered: `001_available_tasks.sql`, etc.)
3. **After changes**: Run `task refresh-views` to update the database
4. **Constraints**: Use SQLite constraints for data integrity (UNIQUE, FOREIGN KEY, CHECK)

**SQL Style:**
- Use recursive CTEs for hierarchical queries
- Prefer SQL views for complex, reusable queries
- Use parameterized queries in Python (never string interpolation)

## Project Structure

```
tasktree/
├── src/tasktree_mcp/      # Main Python package
│   ├── database.py        # Repository classes, DB connection
│   ├── models.py          # Pydantic models
│   ├── tools.py           # FastMCP tool registration
│   └── validators.py      # Input validation helpers
├── sql/                   # SQL-first architecture
│   ├── schemas/           # Database schema definitions
│   └── views/             # SQL views for complex queries
├── tests/                 # Pytest test suite
│   └── conftest.py        # Test fixtures
├── data/                  # Runtime database (gitignored)
├── server.py              # MCP server entry point
└── pyproject.toml         # Project configuration
```

## Common Patterns

### Adding a New MCP Tool

1. Define request/response models in `models.py`
2. Add validation logic in `validators.py` (if needed)
3. Implement repository method in `database.py`
4. Register tool in `tools.py` using `@mcp.tool()` decorator
5. Add tests in `tests/`

### Working with Dependencies

Dependencies form a **Directed Acyclic Graph (DAG)**:
- Circular dependencies are prevented by SQL constraints
- Use `get_available_tasks()` to find tasks ready to execute
- Available = all dependencies are completed

---

**Remember:** This is a SQL-heavy codebase. When in doubt, implement logic in SQL rather than Python. The database is the source of truth for business logic.
