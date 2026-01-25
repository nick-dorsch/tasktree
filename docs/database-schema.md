# Database Schema

## Overview

The TaskTree system uses SQLite as its backend for storing tasks and their dependencies. The schema is designed to support complex Directed Acyclic Graphs (DAGs) of tasks with full execution context tracking.

## Tables

### tasks

Stores individual tasks with their metadata and execution state.

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    agent_id TEXT,
    result_data TEXT,
    error_message TEXT
);
```

#### Columns

- **id**: Unique identifier for the task
- **name**: Human-readable name of the task
- **description**: Optional detailed description of what the task does
- **status**: Current state of the task
  - `pending`: Task is ready to be executed (dependencies satisfied)
  - `running`: Task is currently being executed by an agent
  - `completed`: Task has finished successfully
  - `failed`: Task has failed after all retry attempts
- **priority**: Higher numbers indicate higher priority (default: 0)
- **max_retries**: Maximum number of retry attempts (default: 3)
- **retry_count**: Current number of retry attempts
- **created_at**: Timestamp when task was created
- **started_at**: Timestamp when task execution began
- **completed_at**: Timestamp when task finished (successfully or failed)
- **agent_id**: Identifier of the agent executing the task
- **result_data**: JSON blob containing task execution results
- **error_message**: Error message if task failed

### task_dependencies

Stores dependency relationships between tasks, forming a DAG.

```sql
CREATE TABLE task_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    depends_on_task_id INTEGER NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    UNIQUE(task_id, depends_on_task_id)
);
```

#### Columns

- **id**: Unique identifier for the dependency relationship
- **task_id**: ID of the task that has the dependency
- **depends_on_task_id**: ID of the task that must be completed first
- **UNIQUE constraint**: Prevents duplicate dependency relationships

## Indexes

Performance indexes for efficient querying:

```sql
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX idx_dependencies_task ON task_dependencies(task_id);
CREATE INDEX idx_dependencies_depends_on ON task_dependencies(depends_on_task_id);
```

## Constraints and Guarantees

### ACID Properties

- **Atomicity**: Task status updates are atomic
- **Consistency**: Foreign key constraints ensure referential integrity
- **Isolation**: Concurrent agent operations don't interfere
- **Durability**: All changes are persisted to disk

### Cycle Prevention

The system validates that no circular dependencies are created when adding new dependencies. This ensures the task graph remains a Directed Acyclic Graph (DAG).

### Cascade Deletes

When a task is deleted, all its dependency relationships are automatically cleaned up through ON DELETE CASCADE.

## Query Patterns

### Finding Available Tasks

```sql
SELECT t.* FROM tasks t
WHERE t.status = 'pending'
AND NOT EXISTS (
    SELECT 1 FROM task_dependencies td
    JOIN tasks dt ON td.depends_on_task_id = dt.id
    WHERE td.task_id = t.id
    AND dt.status != 'completed'
)
ORDER BY t.priority DESC, t.created_at ASC
LIMIT 10;
```

This query returns tasks that:
1. Are in 'pending' status
2. Have no incomplete dependencies
3. Are ordered by priority (highest first) and creation time

### Task Status Updates

All status updates are performed atomically to ensure consistency:

```sql
UPDATE tasks 
SET status = 'running', started_at = CURRENT_TIMESTAMP, agent_id = ?
WHERE id = ? AND status = 'pending';
```

### Dependency Checking

Before adding dependencies, the system performs cycle detection using recursive SQL or application-level graph traversal.