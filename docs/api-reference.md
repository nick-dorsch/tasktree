# API Reference

## TaskManager Class

The TaskManager class provides a **thin Python interface** to the **SQL-heavy task execution system**. Most business logic is implemented in SQL functions and views, with Python serving as a wrapper for clean API access.

### Constructor

```python
TaskManager(db_path: str, timeout: float = 30.0)
```

**Parameters:**
- `db_path` (str): Path to SQLite database file
- `timeout` (float): Database connection timeout in seconds

**Example:**
```python
manager = TaskManager("tasks.db")
```

### Task Management Methods

#### create_task

```python
create_task(name: str, description: str = "", priority: int = 0, max_retries: int = 3) -> int
```

Creates a new task and returns its ID.

**Parameters:**
- `name` (str): Human-readable task name
- `description` (str): Optional detailed description
- `priority` (int): Task priority (higher = more important)
- `max_retries` (int): Maximum retry attempts on failure

**Returns:**
- `int`: ID of the created task

**Example:**
```python
task_id = manager.create_task(
    "Process user data",
    description="Analyze and transform user input data",
    priority=5,
    max_retries=2
)
```

#### get_task

```python
get_task(task_id: int) -> Task
```

Retrieves a task by ID.

**Parameters:**
- `task_id` (int): ID of the task to retrieve

**Returns:**
- `Task`: Task object with all metadata

**Raises:**
- `TaskNotFoundError`: If task ID doesn't exist

#### update_task

```python
update_task(task_id: int, **kwargs) -> None
```

Updates task metadata. Valid keyword arguments: `name`, `description`, `priority`.

**Parameters:**
- `task_id` (int): ID of task to update
- `**kwargs`: Fields to update

**Example:**
```python
manager.update_task(task_id, priority=10, description="Updated description")
```

#### delete_task

```python
delete_task(task_id: int) -> None
```

Deletes a task and all its dependencies.

**Parameters:**
- `task_id` (int): ID of task to delete

### Dependency Management Methods

#### add_dependency

```python
add_dependency(task_id: int, depends_on_task_id: int) -> None
```

Adds a dependency relationship between two tasks.

**Parameters:**
- `task_id` (int): ID of the task that depends on the other
- `depends_on_task_id` (int): ID of the task that must complete first

**Raises:**
- `DependencyCycleError`: If this would create a circular dependency
- `TaskNotFoundError`: If either task doesn't exist

**Example:**
```python
# Task 2 depends on task 1
manager.add_dependency(task_id_2, task_id_1)
```

#### remove_dependency

```python
remove_dependency(task_id: int, depends_on_task_id: int) -> None
```

Removes a dependency relationship.

**Parameters:**
- `task_id` (int): ID of the dependent task
- `depends_on_task_id` (int): ID of the prerequisite task

#### get_dependencies

```python
get_dependencies(task_id: int) -> List[int]
```

Returns list of task IDs that the given task depends on.

**Parameters:**
- `task_id` (int): ID of the task

**Returns:**
- `List[int]`: List of dependency task IDs

#### get_dependents

```python
get_dependents(task_id: int) -> List[int]
```

Returns list of task IDs that depend on the given task.

**Parameters:**
- `task_id` (int): ID of the task

**Returns:**
- `List[int]`: List of dependent task IDs

### Task Execution Methods

#### get_available_tasks

```python
get_available_tasks(agent_id: Optional[str] = None, limit: int = 10) -> List[Task]
```

Returns tasks that are ready to be executed (all dependencies completed). **Queries the `available_tasks` SQL view**.

**Parameters:**
- `agent_id` (Optional[str]): Filter tasks for specific agent
- `limit` (int): Maximum number of tasks to return

**Returns:**
- `List[Task]`: Available tasks ordered by priority and creation time

**Implementation Note:** This method queries the `available_tasks` SQL view, which uses custom SQL functions for dependency resolution and priority scoring.

#### claim_task

```python
claim_task(task_id: int, agent_id: str) -> bool
```

Atomically claims a task for execution by an agent.

**Parameters:**
- `task_id` (int): ID of task to claim
- `agent_id` (str): ID of the agent claiming the task

**Returns:**
- `bool`: True if task was successfully claimed, False if already claimed

#### complete_task

```python
complete_task(task_id: int, result_data: Optional[str] = None) -> None
```

Marks a task as completed and stores its results.

**Parameters:**
- `task_id` (int): ID of task to complete
- `result_data` (Optional[str]): JSON string containing task results

#### fail_task

```python
fail_task(task_id: int, error_message: Optional[str] = None) -> None
```

Marks a task as failed and increments retry count.

**Parameters:**
- `task_id` (int): ID of task to mark as failed
- `error_message` (Optional[str]): Description of the error

**Behavior:**
- If `retry_count < max_retries`: task status becomes `pending`
- If `retry_count >= max_retries`: task status becomes `failed`

### Query Methods

#### list_tasks

```python
list_tasks(status: Optional[TaskStatus] = None, agent_id: Optional[str] = None, limit: int = 100) -> List[Task]
```

Lists tasks with optional filtering.

**Parameters:**
- `status` (Optional[TaskStatus]): Filter by task status
- `agent_id` (Optional[str]): Filter by agent ID
- `limit` (int): Maximum number of tasks to return

**Returns:**
- `List[Task]`: List of matching tasks

#### get_task_statistics

```python
get_task_statistics() -> Dict[str, int]
```

Returns summary statistics of tasks in the system.

**Returns:**
- `Dict[str, int]`: Counts by status (pending, running, completed, failed)

## TaskAgent Class

### Constructor

```python
TaskAgent(agent_id: str, manager: TaskManager, capabilities: List[str] = [])
```

**Parameters:**
- `agent_id` (str): Unique identifier for this agent
- `manager` (TaskManager): TaskManager instance
- `capabilities` (List[str]): List of agent capabilities (for future filtering)

### Agent Methods

#### register

```python
register() -> None
```

Registers the agent with the task system.

#### get_next_task

```python
get_next_task() -> Optional[Task]
```

Gets the next available task for this agent to work on.

**Returns:**
- `Optional[Task]`: Available task or None if no tasks available

#### submit_result

```python
submit_result(task_id: int, result: Optional[str], success: bool = True, error: Optional[str] = None) -> None
```

Submits the result of task execution.

**Parameters:**
- `task_id` (int): ID of the completed task
- `result` (Optional[str]): Task result data (JSON string)
- `success` (bool): Whether the task completed successfully
- `error` (Optional[str]): Error message if task failed

#### heartbeat

```python
heartbeat() -> None
```

Updates the agent's last activity timestamp.

## Data Models

### Task

```python
@dataclass
class Task:
    id: Optional[int]
    name: str
    description: str
    status: TaskStatus
    priority: int
    max_retries: int
    retry_count: int
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    agent_id: Optional[str]
    result_data: Optional[str]
    error_message: Optional[str]
```

### TaskStatus (Enum)

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

## Exceptions

### TaskTreeException

Base exception for all TaskTree errors.

### TaskNotFoundError

Raised when attempting to access a non-existent task.

### DependencyCycleError

Raised when attempting to create a circular dependency.

### InvalidTaskStateError

Raised when attempting an invalid state transition.

### DatabaseError

Raised for database operation failures.

## Usage Examples

### Basic Task Creation and Execution

```python
from tasktree import TaskManager, TaskAgent

# Initialize the task manager
manager = TaskManager("my_tasks.db")

# Create some tasks
task1 = manager.create_task("Load data", "Load input data from file")
task2 = manager.create_task("Process data", "Transform and analyze data")
task3 = manager.create_task("Save results", "Save processed results")

# Set up dependencies
manager.add_dependency(task2, task1)  # Process depends on Load
manager.add_dependency(task3, task2)  # Save depends on Process

# Agent executes tasks
agent = TaskAgent("worker-1", manager)
agent.register()

# Work through available tasks
while True:
    task = agent.get_next_task()
    if task is None:
        break
    
    print(f"Executing task: {task.name}")
    # ... do work here ...
    result = {"status": "success", "output": "data processed"}
    agent.submit_result(task.id, json.dumps(result))
```

### Batch Operations

```python
# Create multiple tasks efficiently
tasks = [
    ("task1", "Description 1", 5),
    ("task2", "Description 2", 3),
    ("task3", "Description 3", 8)
]

task_ids = []
for name, desc, priority in tasks:
    task_id = manager.create_task(name, desc, priority)
    task_ids.append(task_id)

# Create dependencies
manager.add_dependency(task_ids[1], task_ids[0])  # task2 depends on task1
manager.add_dependency(task_ids[2], task_ids[1])  # task3 depends on task2
```