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
CREATE FUNCTION is_task_available(task_id INTEGER) RETURNS INTEGER AS $$
SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM task_dependencies td
    JOIN tasks t ON td.depends_on_task_id = t.id
    WHERE td.task_id = task_id AND t.status != 'completed'
) THEN 1 ELSE 0 END;
$$ LANGUAGE SQL;

-- Priority calculation with age weighting
CREATE FUNCTION task_priority_score(task_id INTEGER, created_time TEXT) RETURNS REAL AS $$
SELECT (
    (SELECT priority FROM tasks WHERE id = task_id) * 10 +
    (julianday('now') - julianday(created_time)) * 2.4
);
$$ LANGUAGE SQL;

-- Dependency cycle detection
CREATE FUNCTION would_create_cycle(task_id INTEGER, depends_on INTEGER) RETURNS INTEGER AS $$
WITH RECURSIVE check_cycle(path) AS (
    SELECT depends_on
    UNION ALL
    SELECT td.depends_on_task_id
    FROM task_dependencies td
    JOIN check_cycle cc ON td.task_id = cc.path
    WHERE td.depends_on_task_id != task_id
)
SELECT CASE WHEN EXISTS (
    SELECT 1 FROM check_cycle WHERE path = task_id
) THEN 1 ELSE 0 END;
$$ LANGUAGE SQL;
```

#### Core SQL Views

##### Available Tasks View
```sql
CREATE VIEW available_tasks AS
SELECT 
    t.*,
    task_priority_score(t.id, t.created_at) as priority_score,
    is_task_available(t.id) as is_available,
    (
        SELECT json_group_array(td.depends_on_task_id)
        FROM task_dependencies td
        WHERE td.task_id = t.id
    ) as dependency_list
FROM tasks t
WHERE t.status = 'pending'
AND is_task_available(t.id) = 1
ORDER BY priority_score DESC, t.created_at ASC;
```

##### Dependency Tree View
```sql
CREATE VIEW dependency_tree AS
WITH RECURSIVE task_tree AS (
    -- Root tasks (no dependencies)
    SELECT 
        t.id,
        t.name,
        t.status,
        t.priority,
        0 as level,
        CAST(t.id AS TEXT) as path,
        CAST(NULL AS INTEGER) as parent_id
    FROM tasks t
    WHERE NOT EXISTS (
        SELECT 1 FROM task_dependencies td 
        WHERE td.depends_on_task_id = t.id
    )
    
    UNION ALL
    
    -- Dependent tasks
    SELECT 
        t.id,
        t.name,
        t.status,
        t.priority,
        tt.level + 1,
        tt.path || '->' || t.id,
        td.depends_on_task_id
    FROM tasks t
    JOIN task_dependencies td ON t.id = td.task_id
    JOIN task_tree tt ON td.depends_on_task_id = tt.id
)
SELECT 
    id, name, status, priority, level, path, parent_id,
    CASE 
        WHEN status = 'completed' THEN '✓'
        WHEN status = 'running' THEN '⟳'
        WHEN status = 'failed' THEN '✗'
        ELSE '○'
    END as status_icon,
    (
        SELECT COUNT(*) FROM task_dependencies td 
        WHERE td.task_id = task_tree.id
    ) as dependency_count,
    (
        SELECT COUNT(*) FROM task_dependencies td 
        WHERE td.depends_on_task_id = task_tree.id
    ) as dependent_count
FROM task_tree
ORDER BY path;
```

##### Agent Workload View
```sql
CREATE VIEW agent_workload AS
SELECT 
    agent_id,
    COUNT(*) as running_tasks,
    COUNT(CASE WHEN priority >= 8 THEN 1 END) as high_priority_tasks,
    SUM(priority) as total_priority,
    AVG(julianday('now') - julianday(started_at)) * 24 as avg_run_time_hours,
    MAX(julianday('now') - julianday(started_at)) * 24 as max_run_time_hours
FROM tasks 
WHERE status = 'running'
GROUP BY agent_id;
```

### SQL Stored Procedures Pattern

#### Task Claiming Procedure
```sql
-- Atomic task claiming with validation
CREATE PROCEDURE claim_task(IN task_id INTEGER, IN agent_id TEXT, OUT success INTEGER)
BEGIN
    UPDATE tasks 
    SET status = 'running', 
        started_at = CURRENT_TIMESTAMP, 
        agent_id = agent_id
    WHERE id = task_id 
    AND status = 'pending'
    AND is_task_available(task_id) = 1;
    
    SET success = changes();
END;
```

#### Task Completion Procedure
```sql
-- Task completion with dependent task activation
CREATE PROCEDURE complete_task(IN task_id INTEGER, IN result_data TEXT)
BEGIN
    UPDATE tasks 
    SET status = 'completed',
        completed_at = CURRENT_TIMESTAMP,
        result_data = result_data
    WHERE id = task_id AND status = 'running';
    
    -- Dependent tasks automatically become available via the available_tasks view
END;
```

#### Failure Handling Procedure
```sql
-- Task failure with retry logic
CREATE PROCEDURE fail_task(IN task_id INTEGER, IN error_message TEXT)
BEGIN
    UPDATE tasks 
    SET status = CASE 
            WHEN retry_count + 1 >= max_retries THEN 'failed'
            ELSE 'pending'
        END,
        retry_count = retry_count + 1,
        completed_at = CURRENT_TIMESTAMP,
        error_message = error_message
    WHERE id = task_id AND status = 'running';
END;
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
    def get_available_tasks(self, agent_id: Optional[str] = None, limit: int = 10):
        """Thin wrapper around available_tasks view"""
        query = "SELECT * FROM available_tasks LIMIT ?"
        if agent_id:
            # Additional filtering if needed
            query = "SELECT * FROM available_tasks WHERE agent_id = ? OR agent_id IS NULL LIMIT ?"
            return [Task.from_row(row) for row in self.db.execute(query, (agent_id, limit))]
        else:
            return [Task.from_row(row) for row in self.db.execute(query, (limit,))]
    
    def claim_task(self, task_id: int, agent_id: str) -> bool:
        """Calls SQL stored procedure"""
        cursor = self.db.execute("CALL claim_task(?, ?)", (task_id, agent_id))
        return cursor.fetchone()[0] == 1
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