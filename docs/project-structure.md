# Project Structure

## Directory Layout

```
tasktree/
├── tasktree/                    # Main package directory
│   ├── __init__.py             # Package initialization, exports main classes
│   ├── database.py             # SQLite connection and SQL function registration
│   ├── models.py               # Data models and enums
│   ├── manager.py              # TaskManager - thin wrapper around SQL
│   ├── agent.py                # TaskAgent class for agent interface
│   ├── sql/                    # SQL definition files (core logic)
│   │   ├── functions/          # Custom SQL functions
│   │   ├── views/              # SQL views for common queries
│   │   ├── procedures/         # Stored procedures
│   │   └── schema.sql          # Core database schema
│   └── exceptions.py           # Custom exception classes
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_manager.py         # Tests for TaskManager class
│   ├── test_dependencies.py    # Tests for dependency validation
│   ├── test_agent.py          # Tests for TaskAgent class
│   ├── test_database.py       # Tests for database operations
│   └── conftest.py            # Pytest configuration and fixtures
├── examples/                   # Usage examples and demos
│   ├── basic_usage.py         # Simple task creation and execution
│   ├── complex_workflow.py    # Multi-step workflow with dependencies
│   ├── agent_simulation.py    # Simulate multiple agents working
│   └── batch_operations.py    # Bulk task operations
├── docs/                       # Documentation
│   ├── database-schema.md     # Database design and schema
│   ├── core-components.md     # Architecture overview
│   ├── api-reference.md       # Detailed API documentation
│   └── project-structure.md   # This file
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── setup.py                    # Package setup and installation
├── pyproject.toml             # Modern Python packaging configuration
├── README.md                  # Project overview and quick start
├── LICENSE                    # License information
└── CHANGELOG.md               # Version history and changes
```

## Package Organization

### Core Package (`tasktree/`)

The main package contains all the core functionality:

#### `__init__.py`
- Package initialization
- Exports main public API: `TaskManager`, `TaskAgent`, `Task`, `TaskStatus`
- Version information
- Package-level configuration

#### `database.py`
- `DatabaseManager` class for connection management
- Schema initialization and migration functions
- **SQL function and view registration**
- Custom SQLite function registration
- Connection pooling for thread safety
- **Primary interface to SQL-heavy architecture**

#### `models.py`
- `Task` dataclass with all task metadata
- `TaskStatus` enum for task states
- Type definitions and validators
- Serialization/deserialization helpers

#### `manager.py`
- `TaskManager` class - main orchestrator
- **Thin wrapper around SQL functions and views**
- Interface to SQL stored procedures
- **Delegates complex operations to SQL layer**
- Connection and transaction coordination

#### `agent.py`
- `TaskAgent` class for agent interface
- Agent registration and heartbeat functionality
- Simplified API for task execution
- Automatic retry and error handling

#### `exceptions.py`
- Custom exception hierarchy
- Error codes and messages
- Exception handling utilities

### Testing (`tests/`)

Comprehensive test suite organized by component:

#### `test_manager.py`
- Task creation, updates, deletion
- Dependency management
- Task execution workflows
- Performance and stress tests

#### `test_dependencies.py`
- Dependency validation
- Cycle detection
- Complex DAG scenarios
- Edge cases and error conditions

#### `test_agent.py`
- Agent registration and authentication
- Task claiming and execution
- Multi-agent scenarios
- Concurrency and race conditions

#### `test_database.py`
- Schema initialization
- Connection management
- Transaction handling
- Data integrity tests

#### `conftest.py`
- Pytest fixtures for database setup
- Mock data generation
- Test configuration
- Common helper functions

### Examples (`examples/`)

Real-world usage examples and demonstrations:

#### `basic_usage.py`
- Simple task creation
- Basic dependency setup
- Single agent execution
- Common patterns and best practices

#### `complex_workflow.py`
- Multi-step workflows
- Complex dependency graphs
- Error handling and recovery
- Monitoring and logging

#### `agent_simulation.py`
- Multiple concurrent agents
- Load balancing scenarios
- Performance under stress
- Resource management

#### `batch_operations.py`
- Bulk task creation
- Batch dependency setup
- Import/export functionality
- Data migration examples

## File Details

### Configuration Files

#### `requirements.txt`
```
sqlite3  # Built-in, listed for clarity
typing-extensions>=4.0.0  # For type hints compatibility
```

#### `requirements-dev.txt`
```
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-asyncio>=0.21.0
black>=22.0.0
flake8>=5.0.0
mypy>=1.0.0
pre-commit>=2.20.0
```

#### `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tasktree"
version = "0.1.0"
description = "SQLite-based task execution system with dependency tracking"
authors = [{name = "Your Name", email = "your.email@example.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.8"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=22.0.0",
    "flake8>=5.0.0",
    "mypy>=1.0.0",
]

[tool.black]
line-length = 88
target-version = ['py38']

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

#### `setup.py`
```python
from setuptools import setup, find_packages

setup(
    name="tasktree",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'tasktree=tasktree.cli:main',
        ],
    },
)
```

### Documentation Structure

All documentation is in Markdown format in the `docs/` directory:

- **Database Schema**: Detailed table structures and relationships
- **Core Components**: Architecture and component interactions
- **API Reference**: Complete method signatures and usage examples
- **Project Structure**: This file, explaining the codebase organization

## Development Workflow

### Adding New Features

1. **Core Logic**: Add to appropriate module in `tasktree/`
2. **Tests**: Add comprehensive tests in `tests/`
3. **Documentation**: Update relevant files in `docs/`
4. **Examples**: Add usage example if applicable in `examples/`

### Code Style

- Use `black` for code formatting
- Follow PEP 8 style guidelines
- Type hints required for all public APIs
- Comprehensive docstrings for all public methods

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tasktree

# Run specific test file
pytest tests/test_manager.py

# Run tests with specific marker
pytest -m "not slow"
```

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd tasktree

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest
```

## Packaging and Distribution

### Building

```bash
python -m build
```

### Local Testing

```bash
pip install dist/tasktree-*.whl
```

### Publishing (when ready)

```bash
python -m twine upload dist/*
```

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes to API
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, documentation updates

Version is managed automatically using `setuptools_scm` based on git tags.