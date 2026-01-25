"""
MCP tools for TaskTree server.
"""

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .database import DependencyRepository, TaskRepository
from .models import (
    AddDependencyRequest,
    AddTaskRequest,
    DeleteTaskRequest,
    Dependency,
    DependencyCreateResponse,
    DependencyListResponse,
    DependencyRemoveResponse,
    GetTaskRequest,
    ListDependenciesRequest,
    ListTasksRequest,
    RemoveDependencyRequest,
    Task,
    TaskCreateResponse,
    TaskDeleteResponse,
    TaskListResponse,
    TaskStatus,
    TaskUpdateResponse,
    UpdateTaskRequest,
)
from .validators import (
    validate_description,
    validate_priority,
    validate_status,
    validate_task_name,
)


def register_task_tools(mcp: FastMCP) -> None:
    """Register all task-related tools with the MCP server."""

    @mcp.tool()
    def list_tasks(
        status: Optional[str] = None, priority_min: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List tasks from the database with optional filtering.

        Args:
            status: Filter by status ('pending', 'in_progress', 'completed')
            priority_min: Minimum priority filter (0-10, higher is more important)

        Returns:
            List of task dictionaries with name, description, status, priority, and timestamps
        """
        request = ListTasksRequest(status=status, priority_min=priority_min)
        validate_status(request.status)
        validate_priority(request.priority_min)
        return TaskRepository.list_tasks(
            status=request.status, priority_min=request.priority_min
        )

    @mcp.tool()
    def get_task(name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific task by name.

        Args:
            name: The name of the task to retrieve

        Returns:
            Task dictionary if found, None otherwise
        """
        request = GetTaskRequest(name=name)
        validate_task_name(request.name)
        return TaskRepository.get_task(request.name)

    @mcp.tool()
    def add_task(
        name: str, description: str, priority: int = 0, status: str = "pending"
    ) -> Dict[str, Any]:
        """
        Add a new task to the database.

        Args:
            name: Unique name for the task
            description: Description of what the task involves
            priority: Priority level (0-10, higher is more important)
            status: Initial status ('pending', 'in_progress', 'completed')

        Returns:
            The created task dictionary
        """
        request = AddTaskRequest(
            name=name, description=description, priority=priority, status=status
        )
        # Convert string status to TaskStatus enum
        task_status = TaskStatus(request.status)
        task = Task(
            name=request.name,
            description=request.description,
            priority=request.priority,
            status=task_status,
        )
        return TaskRepository.add_task(
            name=task.name,
            description=task.description,
            priority=task.priority,
            status=task.status.value,
        )

    @mcp.tool()
    def update_task(
        name: str,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing task.

        Args:
            name: Name of the task to update
            description: New description (optional)
            status: New status (optional)
            priority: New priority (optional)
            started_at: ISO timestamp when task was started (optional)
            completed_at: ISO timestamp when task was completed (optional)

        Returns:
            Updated task dictionary if found, None otherwise
        """
        request = UpdateTaskRequest(
            name=name,
            description=description,
            status=status,
            priority=priority,
            started_at=started_at,
            completed_at=completed_at,
        )
        validate_task_name(request.name)
        validate_status(request.status)
        validate_priority(request.priority)
        validate_description(request.description)

        return TaskRepository.update_task(
            name=request.name,
            description=request.description,
            status=request.status,
            priority=request.priority,
            started_at=request.started_at,
            completed_at=request.completed_at,
        )

    @mcp.tool()
    def delete_task(name: str) -> bool:
        """
        Delete a task from the database.

        Args:
            name: Name of the task to delete

        Returns:
            True if task was deleted, False if task was not found
        """
        request = DeleteTaskRequest(name=name)
        validate_task_name(request.name)
        return TaskRepository.delete_task(request.name)


def register_dependency_tools(mcp: FastMCP) -> None:
    """Register all dependency-related tools with the MCP server."""

    @mcp.tool()
    def list_dependencies(task_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List task dependencies.

        Args:
            task_name: Filter dependencies for a specific task (optional)

        Returns:
            List of dependency relationships
        """
        request = ListDependenciesRequest(task_name=task_name)
        return DependencyRepository.list_dependencies(task_name=request.task_name)

    @mcp.tool()
    def add_dependency(task_name: str, depends_on_task_name: str) -> Dict[str, Any]:
        """
        Add a dependency relationship between tasks.

        Args:
            task_name: Name of the task that depends on another task
            depends_on_task_name: Name of the task that must be completed first

        Returns:
            The created dependency relationship
        """
        request = AddDependencyRequest(
            task_name=task_name, depends_on_task_name=depends_on_task_name
        )
        dependency = Dependency(
            task_name=request.task_name,
            depends_on_task_name=request.depends_on_task_name,
        )
        return DependencyRepository.add_dependency(
            task_name=dependency.task_name,
            depends_on_task_name=dependency.depends_on_task_name,
        )

    @mcp.tool()
    def remove_dependency(task_name: str, depends_on_task_name: str) -> bool:
        """
        Remove a dependency relationship.

        Args:
            task_name: Name of the task
            depends_on_task_name: Name of the task it depends on

        Returns:
            True if dependency was removed, False if not found
        """
        request = RemoveDependencyRequest(
            task_name=task_name, depends_on_task_name=depends_on_task_name
        )
        dependency = Dependency(
            task_name=request.task_name,
            depends_on_task_name=request.depends_on_task_name,
        )
        return DependencyRepository.remove_dependency(
            task_name=dependency.task_name,
            depends_on_task_name=dependency.depends_on_task_name,
        )

    @mcp.tool()
    def get_available_tasks() -> List[Dict[str, Any]]:
        """
        Get tasks that can be started (no uncompleted dependencies).

        Returns:
            List of available tasks with their dependencies resolved
        """
        return DependencyRepository.get_available_tasks()


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tools with the MCP server."""
    register_task_tools(mcp)
    register_dependency_tools(mcp)
