# Core Components

## Overview

The TaskTree system is designed as a **SQL-heavy implementation** where the vast majority of business logic, dependency resolution, and data manipulation happens within SQLite using SQL functions, views, and recursive queries. Python components serve as thin wrappers around the SQL layer, providing clean interfaces while delegating complex operations to the database.

## Component Architecture

### 1. TaskManager (`manager.py`)

The central orchestrator of the system. **Acts as a thin wrapper around SQL functions and views**, delegating complex operations to the database layer.

#### Key Responsibilities:
- Interface to SQL functions and stored procedures
- Task creation, updates, and deletion via SQL calls
- Dependency validation and cycle detection (SQL-based)
- **Delegates dependency resolution to SQL views**
- Atomic task state transitions via SQL transactions

#### Core Methods:
- `create_task(name, description="", priority=0, max_retries=3)` - Calls SQL functions
- `add_dependency(task_id, depends_on_task_id)` - Uses SQL cycle detection
- `get_available_tasks(agent_id=None, limit=10)` - **Queries available_tasks view**
- `claim_task(task_id, agent_id)` - Calls SQL claim function
- `complete_task(task_id, result_data=None)` - SQL state transition
- `fail_task(task_id, error_message=None)` - SQL state transition

#### Usage Pattern:
```python
manager = TaskManager("path/to/database.db")
task_id = manager.create_task("Process data", description="Analyze input data")
manager.add_dependency(task_id, prerequisite_task_id)
available = manager.get_available_tasks()  # Returns data from SQL view
```

### 2. Database Layer (`database.py`)

Handles all SQLite-specific operations, connection pooling, and schema management. **Primary interface to the SQL-heavy data layer.**

#### Key Responsibilities:
- Database connection setup and teardown
- Schema initialization and migrations including custom SQL functions
- Connection pooling for concurrent access
- SQL query execution with prepared statements
- Transaction management
- Custom SQLite function registration

#### Core Methods:
- `initialize_database(db_path)`
- `get_connection()`
- `execute_query(sql, params=())`
- `execute_transaction(queries)`
- `register_custom_functions(conn)` - Registers Python functions for SQL use

#### Features:
- Thread-safe connection management
- Automatic schema versioning
- Backup and restore functionality
- **SQL-centric architecture** - Most logic implemented as SQL functions/views
- **Custom function registration** for complex business logic in SQL

### 3. Data Models (`models.py`)

Defines the data structures used throughout the system with proper typing and validation.

#### Key Classes:
- `Task`: Represents a single task with all its metadata
- `Dependency`: Represents a dependency relationship
- `TaskStatus`: Enum for task states
- `TaskQuery`: Builder pattern for complex queries

#### Example:
```python
@dataclass
class Task:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    max_retries: int = 3
    retry_count: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    result_data: Optional[str] = None
    error_message: Optional[str] = None
```

### 4. Agent Interface (`agent.py`)

Provides a simplified interface for agents to interact with the task system without needing to understand the underlying complexity.

#### Key Responsibilities:
- Abstract task operations from agent perspective
- Handle automatic retries and error recovery
- Provide context-aware task selection
- Manage agent registration and heartbeat

#### Core Methods:
- `register_agent(agent_id, capabilities=[])`
- `get_next_task(agent_id)`
- `submit_result(task_id, result, success=True, error=None)`
- `heartbeat(agent_id)`

#### Agent Workflow:
```python
agent = TaskAgent("agent-123", capabilities=["data_processing"])
agent.register()

while True:
    task = agent.get_next_task()
    if task is None:
        break  # No tasks available
    
    try:
        result = execute_task(task)
        agent.submit_result(task.id, result, success=True)
    except Exception as e:
        agent.submit_result(task.id, None, success=False, error=str(e))
```

### 5. Exception Handling (`exceptions.py`)

Custom exceptions for specific error conditions in the system.

#### Exception Classes:
- `TaskTreeException`: Base exception class
- `TaskNotFoundError`: Task ID doesn't exist
- `DependencyCycleError`: Attempt to create circular dependency
- `InvalidTaskStateError`: Invalid state transition
- `DatabaseError`: Database operation failures

## Component Interactions

### Task Execution Flow

1. **Task Creation**: TaskManager creates task and validates dependencies
2. **Dependency Resolution**: Database layer efficiently queries for available tasks
3. **Task Claiming**: Agent interface claims task atomically
4. **Execution**: Agent performs work (outside the system)
5. **Result Submission**: Agent interface updates task status
6. **Next Tasks Available**: Dependent tasks may become available

### Concurrency Handling

- **Thread Safety**: All database operations use proper locking
- **Atomic Operations**: Task claiming and status updates are atomic
- **Deadlock Prevention**: Transactions are kept short and consistent
- **Connection Pooling**: Multiple agents can work concurrently

### Performance Optimizations

- **Query Caching**: Frequently used queries are prepared statements
- **Batch Operations**: Multiple dependency additions use transactions
- **Index Utilization**: Database schema optimized for common query patterns
- **Lazy Loading**: Large result sets are loaded on demand

## Extension Points

The architecture is designed to be extensible:

### Custom Task Types
- Subclass `Task` model for domain-specific task types
- Add custom validation and business logic
- Extend serialization for complex result data

### Pluggable Dependency Resolvers
- Implement custom dependency validation logic
- Add support for conditional dependencies
- Implement priority-based dependency resolution

### Custom Agent Behaviors
- Extend `TaskAgent` for specialized agent types
- Add capability-based task matching
- Implement custom retry strategies

### Alternative Storage Backends
- Swap SQLite for PostgreSQL or MySQL
- Add distributed storage support
- Implement in-memory mode for testing

## Testing Strategy

Each component has comprehensive tests:

- **Unit Tests**: Test individual methods and edge cases
- **Integration Tests**: Test component interactions
- **Performance Tests**: Validate performance under load
- **Concurrency Tests**: Verify thread safety and atomicity

The component design ensures that each part can be tested in isolation while maintaining clear interfaces for integration testing.