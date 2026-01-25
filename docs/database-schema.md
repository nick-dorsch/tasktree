# Database Schema

## Overview

The TaskTree system uses SQLite as its backend for storing tasks and their dependencies. The schema is designed to support complex Directed Acyclic Graphs (DAGs) of tasks with full execution context tracking.

## Tables

### tasks

Stores individual tasks with their metadata and execution state.

```sql
CREATE TABLE tasks (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### Columns

- **name**: Unique name identifier for the task (primary key)
- **description**: Detailed description of what the task does
- **status**: Current state of the task
  - `pending`: Task is ready to be executed (dependencies satisfied)
  - `in_progress`: Task is currently being executed
  - `completed`: Task has finished successfully
- **priority**: Higher numbers indicate higher priority (default: 0)
- **created_at**: Timestamp when task was created
- **started_at**: Timestamp when task execution began
- **completed_at**: Timestamp when task finished

### dependencies

Stores dependency relationships between tasks, forming a DAG.

```sql
CREATE TABLE dependencies (
    task_name TEXT NOT NULL REFERENCES tasks(name),
    depends_on_task_name TEXT NOT NULL REFERENCES tasks(name),
    PRIMARY KEY (task_name, depends_on_task_name),
    CHECK (task_name != depends_on_task_name)
);
```

#### Columns

- **task_name**: Name of the task that has the dependency
- **depends_on_task_name**: Name of the task that must be completed first
- **PRIMARY KEY**: Composite key prevents duplicate dependency relationships
- **CHECK constraint**: Prevents self-dependencies

## Triggers

### Circular Dependency Prevention

```sql
CREATE TRIGGER prevent_circular_dependencies
BEFORE INSERT ON dependencies
BEGIN
  SELECT CASE
    WHEN EXISTS (
      WITH RECURSIVE dependency_chain AS (
        SELECT depends_on_task_name as task_name, 1 as depth
        FROM dependencies
        WHERE task_name = NEW.depends_on_task_name
        
        UNION ALL
        
        SELECT d.depends_on_task_name, dc.depth + 1
        FROM dependencies d
        JOIN dependency_chain dc ON d.task_name = dc.task_name
        WHERE dc.depth < 10
      )
      SELECT 1 FROM dependency_chain WHERE task_name = NEW.task_name
    ) THEN
      RAISE(ABORT, 'Circular dependencies are not allowed!')
    END;
END;
```

## Constraints and Guarantees

### ACID Properties

- **Atomicity**: Task status updates are atomic
- **Consistency**: Foreign key constraints ensure referential integrity
- **Isolation**: Concurrent agent operations don't interfere
- **Durability**: All changes are persisted to disk

### Cycle Prevention

The trigger `prevent_circular_dependencies` validates that no circular dependencies are created when adding new dependencies. This ensures the task graph remains a Directed Acyclic Graph (DAG).

### Referential Integrity

Foreign key constraints ensure that all task names referenced in dependencies table exist in the tasks table.

## Query Patterns

### Finding Available Tasks

```sql
SELECT t.* FROM tasks t
WHERE t.status = 'pending'
AND NOT EXISTS (
    SELECT 1 FROM dependencies d
    JOIN tasks dt ON d.depends_on_task_name = dt.name
    WHERE d.task_name = t.name
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
SET status = 'in_progress', started_at = CURRENT_TIMESTAMP
WHERE name = ? AND status = 'pending';
```

### Adding Tasks and Dependencies

With name-based primary keys, inserts are maximally ergonomic:

```sql
-- Insert a task
INSERT INTO tasks (name, description, priority) 
VALUES ('Deploy Application', 'Deploy to production environment', 3);

-- Add dependencies by name
INSERT INTO dependencies (task_name, depends_on_task_name) 
VALUES 
  ('Deploy Application', 'Build User Interface'),
  ('Deploy Application', 'Run Tests');
```

### Dependency Checking

The trigger automatically performs cycle detection using recursive CTEs when inserting dependencies.