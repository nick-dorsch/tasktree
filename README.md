# README

# TaskTree - SQL-Heavy Task Execution System

A SQLite-based task execution system with **complex dependency tracking**, designed for
agentic coding workflows. The system uses a **SQL-first architecture** where the
database handles the majority of business logic through functions, views, and recursive
queries.

## Key Features

- **SQLite-Powered Dependency Resolution** - Complex DAG dependencies handled entirely in SQL
- **Recursive Query Optimization** - Hierarchical task trees using SQLite recursive CTEs
- **SQL-First Architecture** - Business logic implemented in SQL, minimal Python overhead
- **Custom SQL Functions** - Task availability, priority scoring, and cycle detection in the database
- **Agent-Centric Design** - Built for multiple concurrent agents working on task graphs
- **ACID Compliance** - SQLite ensures data consistency and concurrent access safety

## Architecture Overview

TaskTree uses a **SQL-heavy implementation** where:

- **SQLite handles** dependency resolution, state transitions, and complex queries
- **Python provides** thin wrappers around SQL operations
- **Recursive CTEs** manage hierarchical dependency trees
- **SQL views** provide optimized query patterns
- **Custom functions** implement business logic in the database

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   TaskAgent     │───▶│   TaskManager    │───▶│   SQL Functions  │
│   (Interface)   │    │   (Thin Wrapper) │    │   & Views       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   SQLite DB     │
                                              │   (Core Logic)  │
                                              └─────────────────┘
```

## Quick Start

### Installation

```bash
pip install tasktree
```

### Basic Usage

```python
from tasktree import TaskManager, TaskAgent

# Initialize the task system
manager = TaskManager("tasks.db")

# Create tasks with dependencies
task1 = manager.create_task("Load data", description="Load input data")
task2 = manager.create_task("Process data", description="Transform data", priority=5)
task3 = manager.create_task("Save results", description="Output results")

# Set up dependencies (task2 depends on task1, task3 depends on task2)
manager.add_dependency(task2, task1)
manager.add_dependency(task3, task2)

# Agent executes available tasks
agent = TaskAgent("worker-1", manager)
agent.register()

while True:
    task = agent.get_next_task()
    if task is None:
        break  # No more tasks available
    
    print(f"Executing: {task.name}")
    # ... perform work ...
    agent.submit_result(task.id, {"status": "success"}, success=True)
```

## SQL-Heavy Features

### Complex Dependency Resolution

```python
# Get available tasks - this uses the available_tasks SQL view
available = manager.get_available_tasks()
# The view uses SQL functions to:
# - Recursively check all dependencies
# - Calculate priority scores with age weighting
# - Filter tasks by completion status
```

### Dependency Tree Visualization

```python
# Query the dependency_tree view for hierarchical task relationships
tree = manager.execute_query("SELECT * FROM dependency_tree")
# Returns a flat representation of the entire task graph with:
# - Hierarchy levels
# - Path information
# - Status indicators
# - Dependency/dependent counts
```

### Agent Workload Monitoring

```python
# Query agent_workload view for current agent statistics
workload = manager.execute_query("SELECT * FROM agent_workload")
# Provides real-time statistics on:
# - Running tasks per agent
# - Priority distribution
# - Average and max run times
```

## Core SQL Components

### Custom SQL Functions

- `is_task_available(task_id)` - Checks if all dependencies are completed
- `task_priority_score(task_id, created_at)` - Calculates composite priority
- `would_create_cycle(task_id, depends_on)` - Prevents circular dependencies

### SQL Views

- `available_tasks` - Pre-filtered list of executable tasks
- `dependency_tree` - Hierarchical task relationship view
- `agent_workload` - Real-time agent performance metrics

### Stored Procedures

- `claim_task(task_id, agent_id)` - Atomic task claiming
- `complete_task(task_id, result_data)` - Task completion with dependency activation
- `fail_task(task_id, error_message)` - Failure handling with retry logic

## Performance Advantages

### Database-Centric Design

- **Zero Python-level dependency traversal** - All handled by SQL recursive CTEs
- **Optimized query planning** - SQLite handles join optimization and indexing
- **Minimal data transfer** - Only final results sent to Python
- **Built-in concurrency** - SQLite ACID properties handle parallel agents

### Query Examples

```sql
-- Get all available tasks with calculated priority scores
SELECT * FROM available_tasks 
WHERE priority_score > 50 
ORDER BY priority_score DESC, created_at ASC;

-- Find all tasks that depend on a specific task
SELECT * FROM dependency_tree 
WHERE path LIKE '%->42->%';

-- Monitor agent performance in real-time
SELECT * FROM agent_workload 
WHERE running_tasks > 5 OR avg_run_time_hours > 2.0;
```

## Project Structure

```
tasktree/
├── tasktree/                    # Main package
│   ├── sql/                     # SQL definitions (core logic)
│   │   ├── functions/           # Custom SQL functions
│   │   ├── views/               # SQL views for queries
│   │   ├── procedures/          # Stored procedures
│   │   └── schema.sql           # Database schema
│   ├── database.py              # Connection & SQL registration
│   ├── manager.py               # Thin SQL wrapper
│   ├── agent.py                 # Agent interface
│   └── models.py                # Data models
├── docs/                        # Documentation
├── tests/                       # Test suite
└── examples/                    # Usage examples
```

## Documentation

- [Database Schema](docs/database-schema.md) - Complete SQLite schema design
- [SQL-Heavy Architecture](docs/sql-heavy-architecture.md) - SQL-first design principles
- [Core Components](docs/core-components.md) - Component architecture
- [API Reference](docs/api-reference.md) - Complete method documentation
- [Project Structure](docs/project-structure.md) - File organization and development
- [JSONL Snapshot Format](docs/jsonl-snapshot-format.md) - Canonical snapshot schema

## Snapshot Workflow

TaskTree keeps the SQLite database (`.tasktree/tasktree.db`) out of git. Use JSONL snapshots
for collaboration, merges, and rehydrating local state.

### Export a Snapshot

```bash
task snapshot-export
```

By default this writes `.tasktree/tasktree.snapshot.jsonl` in the repo. You can override
the location with `TASKTREE_SNAPSHOT_PATH=/absolute/path/to/tasktree.snapshot.jsonl`.

### Merge Workflow

1. Run `task snapshot-export` and commit `.tasktree/tasktree.snapshot.jsonl`.
2. Merge or rebase as usual; resolve any JSONL conflicts line-by-line.
3. Rehydrate your local database from the merged snapshot.

### Rehydrate (Import)

```bash
task snapshot-import
```

`snapshot-import` overwrites the local database by default. To keep the existing database
and only import when it's missing, run `task snapshot-import OVERWRITE=false`.

## Use Cases

### Agentic Coding Workflows

```python
# Agent finds tasks it can execute based on completed dependencies
available_tasks = agent.get_next_tasks_for_capabilities(["data_processing", "ml_training"])

# System automatically tracks complex dependency chains
manager.add_dependency("train_model", "preprocess_data")
manager.add_dependency("preprocess_data", "load_dataset")
manager.add_dependency("deploy_model", "train_model")
```

### Complex Task Graphs

```python
# Build sophisticated dependency graphs
tasks = {
    "collect_data": [],
    "clean_data": ["collect_data"],
    "feature_engineer": ["clean_data"],
    "train_model": ["feature_engineer"],
    "validate_model": ["train_model"],
    "deploy_model": ["validate_model"],
    "monitor_model": ["deploy_model"]
}

# Set up dependencies programmatically
for task, deps in tasks.items():
    task_id = manager.create_task(task)
    for dep in deps:
        manager.add_dependency(task_id, task_ids[dep])
```

## Contributing

TaskTree is designed for SQL-first development. When contributing:

1. **Implement business logic in SQL** when possible
2. **Add Python wrappers only for interface purposes**
3. **Write SQL unit tests** for complex functions and views
4. **Document SQL patterns** in the architecture documentation

## License

MIT License - see LICENSE file for details.
