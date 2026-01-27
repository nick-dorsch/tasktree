"""
MCP tools for TaskTree server.
"""

from typing import List, Optional

from fastmcp import FastMCP

from ..core.database import DependencyRepository, FeatureRepository, TaskRepository
from ..core.models import (
    AddDependenciesRequest,
    AddFeatureRequest,
    AddTaskRequest,
    CompleteTaskRequest,
    DeleteTaskRequest,
    Dependency,
    DependencyResponse,
    Feature,
    FeatureResponse,
    GetTaskRequest,
    ListDependenciesRequest,
    ListTasksRequest,
    RemoveDependencyRequest,
    Task,
    TaskResponse,
    TaskStartResponse,
    TaskStatus,
    UpdateTaskRequest,
)
from ..core.validators import (
    validate_description,
    validate_feature_name,
    validate_priority,
    validate_specification,
    validate_status,
    validate_task_name,
)


def register_task_tools(mcp: FastMCP) -> None:
    """Register all task-related tools with the MCP server."""

    @mcp.tool()
    def list_tasks(
        status: Optional[str] = None,
        priority_min: Optional[int] = None,
        feature_name: Optional[str] = None,
    ) -> List[TaskResponse]:
        """
        List tasks from the database with optional filtering.

        Args:
            status: Filter by status ('pending', 'in_progress', 'completed')
            priority_min: Minimum priority filter (0-10, higher is more important)
            feature_name: Filter by feature name

        Returns:
            List of TaskResponse models with task data
        """
        request = ListTasksRequest(
            status=status, priority_min=priority_min, feature_name=feature_name
        )
        validate_status(request.status)
        validate_priority(request.priority_min)
        validate_feature_name(request.feature_name)
        return TaskRepository.list_tasks(
            status=request.status,
            priority_min=request.priority_min,
            feature_name=request.feature_name,
        )

    @mcp.tool()
    def get_task(name: str) -> Optional[TaskResponse]:
        """
        Get a specific task by name.

        Args:
            name: The name of the task to retrieve

        Returns:
            TaskResponse model if found, None otherwise
        """
        request = GetTaskRequest(name=name)
        validate_task_name(request.name)
        return TaskRepository.get_task(request.name)

    @mcp.tool()
    def add_task(
        name: str,
        description: str,
        specification: str,
        priority: int = 0,
        status: str = "pending",
        dependencies: Optional[List[str]] = None,
        feature_name: str = "misc",
        tests_required: bool = True,
    ) -> bool:
        """
        Add a new task to the database.

        Note that if tests_required is true, tests are part of the task! Do not create
        separate tasks to implement tests, each task requires its own tests.

        Args:
            name: Unique name for the task
            description: Description of what the task involves
            specification: Detailed task specification, including implementation notes
            priority: Priority level (0-10, higher is more important)
            status: Initial status ('pending', 'in_progress', 'completed')
            dependencies: List of task names this task depends on (optional)
            feature_name: Feature this task belongs to (defaults to 'misc')
            tests_required: Whether tests are required for this task

        Returns:
            True if the task was created successfully
        """
        request = AddTaskRequest(
            name=name,
            description=description,
            specification=specification,
            priority=priority,
            status=status,
            dependencies=dependencies,
            feature_name=feature_name,
            tests_required=tests_required,
        )
        validate_feature_name(request.feature_name)
        validate_specification(request.specification)

        # Validate dependencies exist before creating task
        if request.dependencies:
            for dep_name in request.dependencies:
                if not TaskRepository.get_task(dep_name):
                    raise ValueError(f"Dependency task '{dep_name}' does not exist")

        # Convert string status to TaskStatus enum
        task_status = TaskStatus(request.status)
        task = Task(
            name=request.name,
            description=request.description,
            specification=request.specification,
            priority=request.priority,
            status=task_status,
            feature_name=request.feature_name,
            tests_required=request.tests_required,
        )

        # Create the task
        TaskRepository.add_task(
            name=task.name,
            description=task.description,
            specification=task.specification,
            priority=task.priority,
            status=task.status.value,
            feature_name=task.feature_name,
            tests_required=task.tests_required,
        )

        # Add dependencies if provided
        if request.dependencies:
            for dep_name in request.dependencies:
                DependencyRepository.add_dependency(
                    task_name=task.name,
                    depends_on_task_name=dep_name,
                )

        return True

    @mcp.tool()
    def update_task(
        name: str,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        specification: Optional[str] = None,
        tests_required: Optional[bool] = None,
    ) -> Optional[TaskResponse]:
        """
        Update an existing task.

        Args:
            name: Name of the task to update
            description: New description (optional)
            status: New status (optional)
            priority: New priority (optional)
            specification: New specification (optional)
            tests_required: Whether tests are required for this task (optional)

        Returns:
            TaskResponse model with updated task data if found, None otherwise
        """
        request = UpdateTaskRequest(
            name=name,
            description=description,
            status=status,
            priority=priority,
            specification=specification,
            tests_required=tests_required,
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
            specification=request.specification,
            tests_required=request.tests_required,
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

    @mcp.tool()
    def start_task(name: str) -> Optional[TaskStartResponse]:
        """
        Start a task by setting its status to 'in_progress'.

        Args:
            name: Name of the task to start

        Returns:
            TaskStartResponse model with task and feature data if found, None otherwise
        """
        validate_task_name(name)
        task = TaskRepository.update_task(name=name, status="in_progress")
        if task is None:
            return None
        feature = FeatureRepository.get_feature(task.feature_name)
        if feature is None:
            raise ValueError(f"Feature '{task.feature_name}' does not exist")
        return TaskStartResponse(task=task, feature=feature)

    @mcp.tool()
    def complete_task(name: str) -> Optional[TaskResponse]:
        """
        Complete a task by setting its status to 'completed'.

        Args:
            name: Name of the task to complete

        Returns:
            TaskResponse model with updated task data if found, None otherwise
        """
        request = CompleteTaskRequest(name=name)
        validate_task_name(request.name)
        return TaskRepository.complete_task(request.name)


def register_dependency_tools(mcp: FastMCP) -> None:
    """Register all dependency-related tools with the MCP server."""

    @mcp.tool()
    def list_dependencies(task_name: Optional[str] = None) -> List[DependencyResponse]:
        """
        List task dependencies.

        Args:
            task_name: Filter dependencies for a specific task (optional)

        Returns:
            List of DependencyResponse models with dependency relationship data
        """
        request = ListDependenciesRequest(task_name=task_name)
        return DependencyRepository.list_dependencies(task_name=request.task_name)

    @mcp.tool()
    def add_dependencies(task_name: str, depends_on_task_names: List[str]) -> bool:
        """
        Add dependency relationships between tasks.

        Args:
            task_name: Name of the task that depends on other tasks
            depends_on_task_names: List of task names that must be completed first

        Returns:
            True if all dependencies were created successfully
        """
        request = AddDependenciesRequest(
            task_name=task_name, depends_on_task_names=depends_on_task_names
        )
        failures = []
        for depends_on_task_name in request.depends_on_task_names:
            dependency = Dependency(
                task_name=request.task_name,
                depends_on_task_name=depends_on_task_name,
            )
            try:
                DependencyRepository.add_dependency(
                    task_name=dependency.task_name,
                    depends_on_task_name=dependency.depends_on_task_name,
                )
            except ValueError as exc:
                failures.append(f"{depends_on_task_name} ({exc})")

        if failures:
            failure_list = ", ".join(failures)
            raise ValueError(
                "Failed to add dependencies for task "
                f"'{request.task_name}': {failure_list}"
            )

        return True

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
    def get_available_tasks() -> List[TaskResponse]:
        """
        Get tasks that can be started NOW.

        They are available because all their dependencies are fulfilled.

        They are ordered by priority, favour high priority tasks.

        Returns:
            List of TaskResponse models for available tasks with dependencies resolved
        """
        return DependencyRepository.get_available_tasks()


def register_feature_tools(mcp: FastMCP) -> None:
    """Register all feature-related tools with the MCP server."""

    @mcp.tool()
    def add_feature(
        name: str,
        description: str,
        specification: str,
    ) -> bool:
        """
        Add a new feature to the database.

        Args:
            name: Unique name for the feature
            description: Description of the feature
            specification: Detailed feature specification

        Returns:
            True if the feature was created successfully
        """
        request = AddFeatureRequest(
            name=name,
            description=description,
            specification=specification,
        )
        validate_feature_name(request.name)
        validate_description(request.description)
        validate_specification(request.specification)

        feature = Feature(
            name=request.name,
            description=request.description,
            specification=request.specification,
        )

        FeatureRepository.add_feature(
            name=feature.name,
            description=feature.description,
            specification=feature.specification,
        )
        return True

    @mcp.tool()
    def list_features() -> List[FeatureResponse]:
        """
        List features from the database.

        Returns:
            List of FeatureResponse models with feature data
        """
        return FeatureRepository.list_features()


def register_all_tools(mcp: FastMCP) -> None:
    """Register all tools with the MCP server."""
    register_task_tools(mcp)
    register_dependency_tools(mcp)
    register_feature_tools(mcp)
