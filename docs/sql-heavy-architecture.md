# SQL-Heavy Architecture

## Design Philosophy

TaskTree is built on a **SQL-first architecture** where the database is the primary source of business logic, not just a persistence layer. This approach leverages SQLite's advanced features to create a robust, performant, and maintainable task execution system.

## Core Principles

### 1. Database-Centric Logic
- **Complex dependency resolution** handled by SQL recursive CTEs
- **Task availability determination** via SQL functions and views
- **State transitions** managed through SQL stored procedures
- **Performance optimization** happening in the database engine

### 2. Python as Interface Layer
- **Thin wrappers** around SQL operations
- **Connection management** and transaction coordination
- **Type conversion** between Python and SQLite
- **Application-level orchestration** only

### 3. SQL-First Query Design
- **Prepared statements** for all operations
- **Custom SQL functions** for business logic
- **Materialized views** for common query patterns
- **Recursive queries** for hierarchical dependency resolution

## SQL Implementation Strategy

### Database Schema Enhancements

#### Custom SQL Functions
```sql
-- Task availability checking
CREATE FUNCTION is_task_available(task_name TEXT) RETURNS INTEGER AS $$
SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM dependencies d
    JOIN tasks t ON d.depends_on_task_name = t.name
    WHERE d.task_name = task_name AND t.status != 'completed'
) THEN 1 ELSE 0 END;
$$ LANGUAGE SQL;

-- Priority calculation with age weighting
CREATE FUNCTION task_priority_score(task_name TEXT, created_time TEXT) RETURNS REAL AS $$
SELECT (
    (SELECT priority FROM tasks WHERE name = task_name) * 10 +
    (julianday('now') - julianday(created_time)) * 2.4
);
$$ LANGUAGE SQL;

-- Note: Dependency cycle detection is handled by the prevent_circular_dependencies trigger
-- which uses a recursive CTE to check for cycles before allowing dependency inserts
```

#### Core SQL Views

##### Available Tasks View
```sql
CREATE VIEW v_available_tasks AS
SELECT t.*
FROM tasks t
WHERE t.status = 'pending'
  AND NOT EXISTS (
    SELECT 1
    FROM dependencies d
    JOIN tasks dep_task ON d.depends_on_task_name = dep_task.name
    WHERE d.task_name = t.name
      AND dep_task.status != 'completed'
  )
ORDER BY t.priority DESC, t.created_at ASC;
```

##### Dependency Tree View
```sql
CREATE VIEW v_dependency_tree AS
WITH RECURSIVE task_tree AS (
    -- Root tasks (no dependencies)
    SELECT 
        t.name,
        t.description,
        t.status,
        t.priority,
        t.completed_at,
        0 as level,
        CAST(t.name AS TEXT) as path,
        CAST(NULL AS TEXT) as parent_name
    FROM tasks t
    WHERE NOT EXISTS (
        SELECT 1 FROM dependencies d 
        WHERE d.task_name = t.name
    )
    
    UNION ALL
    
    -- Dependent tasks
    SELECT 
        t.name,
        t.description,
        t.status,
        t.priority,
        t.completed_at,
        tt.level + 1,
        tt.path || '->' || t.name,
        d.depends_on_task_name as parent_name
    FROM tasks t
    JOIN dependencies d ON t.name = d.task_name
    JOIN task_tree tt ON d.depends_on_task_name = tt.name
)
SELECT 
    name, description, status, priority, completed_at, level, path, parent_name
FROM task_tree
ORDER BY path;
```

##### Graph JSON View
```sql
CREATE VIEW v_graph_json AS
SELECT json_object(
    'nodes', (
        SELECT json_group_array(
            json_object(
                'name', t.name,
                'status', t.status,
                'priority', t.priority,
                'completed_at', t.completed_at,
                'is_available', CASE WHEN t.name IN (SELECT name FROM v_available_tasks) THEN 1 ELSE 0 END
            )
        )
        FROM tasks t
    ),
    'edges', (
        SELECT json_group_array(
            json_object(
                'from', d.task_name,
                'to', d.depends_on_task_name
            )
        )
        FROM dependencies d
    )
) as graph_json;
```

### SQL Stored Procedures Pattern

#### Task Status Updates

With name-based primary keys, task updates are ergonomic and human-readable:

```sql
-- Start a task
UPDATE tasks 
SET status = 'in_progress', 
    started_at = CURRENT_TIMESTAMP
WHERE name = 'Deploy Application' 
AND status = 'pending';
```

```sql
-- Complete a task
UPDATE tasks 
SET status = 'completed',
    completed_at = CURRENT_TIMESTAMP
WHERE name = 'Deploy Application' 
AND status = 'in_progress';
```

```sql
-- Reset a task
UPDATE tasks 
SET status = 'pending',
    started_at = NULL,
    completed_at = NULL
WHERE name = 'Deploy Application';
```

## Python Layer Responsibilities

### Minimal Python Logic

The Python layer is intentionally thin, focusing only on:

#### Connection Management
```python
class DatabaseManager:
    def get_connection(self):
        """Thread-safe connection with SQL optimizations"""
        conn = sqlite3.connect(self.db_path, **self.connection_config)
        self._register_sql_functions(conn)
        return conn
```

#### SQL Function Registration
```python
def _register_sql_functions(self, conn):
    """Register Python functions for SQL use when necessary"""
    
    def complex_dependency_check(task_id: int) -> int:
        """Complex logic that can't be expressed in pure SQL"""
        # Only for truly complex scenarios that SQL can't handle
        pass
    
    conn.create_function("complex_dependency_check", 1, complex_dependency_check)
```

#### Interface Methods
```python
class TaskManager:
    def get_available_tasks(self, limit: int = 10):
        """Thin wrapper around v_available_tasks view"""
        query = "SELECT * FROM v_available_tasks LIMIT ?"
        return [Task.from_row(row) for row in self.db.execute(query, (limit,))]
    
    def start_task(self, task_name: str) -> bool:
        """Start a task by name"""
        cursor = self.db.execute(
            "UPDATE tasks SET status = 'in_progress', started_at = CURRENT_TIMESTAMP "
            "WHERE name = ? AND status = 'pending'",
            (task_name,)
        )
        return cursor.rowcount > 0
    
    def complete_task(self, task_name: str) -> bool:
        """Complete a task by name"""
        cursor = self.db.execute(
            "UPDATE tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP "
            "WHERE name = ? AND status = 'in_progress'",
            (task_name,)
        )
        return cursor.rowcount > 0
```

## Performance Benefits of SQL-Heavy Design

### 1. Reduced Python Overhead
- **No Python-level dependency traversal**
- **No Python state management**
- **Minimal data transfer between Python and SQLite**

### 2. Database Engine Optimization
- **SQLite query planner** optimizes complex joins and recursive queries
- **Index utilization** is automatic and efficient
- **Memory management** handled by SQLite internals

### 3. Concurrency Advantages
- **Database-level locking** ensures data consistency
- **Connection pooling** enables parallel agent operations
- **Transaction management** handled by SQLite ACID properties

## File Organization

```
tasktree/
├── tasktree/
│   ├── sql/                    # SQL definition files
│   │   ├── functions/         # Custom SQL functions
│   │   │   ├── task_availability.sql
│   │   │   ├── priority_scoring.sql
│   │   │   └── cycle_detection.sql
│   │   ├── views/              # SQL views for common queries
│   │   │   ├── available_tasks.sql
│   │   │   ├── dependency_tree.sql
│   │   │   └── agent_workload.sql
│   │   ├── procedures/         # Stored procedures
│   │   │   ├── claim_task.sql
│   │   │   ├── complete_task.sql
│   │   │   └── fail_task.sql
│   │   └── schema.sql          # Core database schema
│   ├── database.py             # Connection and SQL registration
│   ├── manager.py              # Thin wrapper around SQL
│   └── ...
```

## Testing Strategy

### SQL Unit Testing
- **Direct SQL testing** using SQLite CLI
- **Function and view validation** with test data
- **Performance benchmarking** of complex queries
- **Recursive query verification** with known dependency graphs

### Python Layer Testing
- **Interface validation** only
- **Connection management testing**
- **Error handling and transaction testing**
- **Type conversion testing**

This SQL-heavy architecture ensures maximum performance, reliability, and maintainability by leveraging SQLite's strengths while keeping Python code minimal and focused on interface concerns.