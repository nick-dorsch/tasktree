"""
Data models for TaskTree.
"""

from enum import StrEnum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class TaskStatus(StrEnum):
    """Valid task status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class Task(BaseModel):
    """Task model with validation."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    specification: str = Field(
        ...,
        min_length=1,
        description="Detailed task specification",
    )
    feature_name: str = Field(default="misc", min_length=1, max_length=55)
    tests_required: bool = Field(default=True)
    priority: int = Field(default=0, ge=0, le=10)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> TaskStatus:
        """Validate status is one of the allowed values."""
        if isinstance(v, TaskStatus):
            return v
        if isinstance(v, str):
            v = v.lower()
            for status in TaskStatus:
                if status.value == v:
                    return status
            raise ValueError(
                f"Status must be one of: {', '.join([s.value for s in TaskStatus])}"
            )
        raise ValueError(f"Invalid status type: {type(v)}")


class Dependency(BaseModel):
    """Dependency relationship model."""

    task_name: str = Field(..., min_length=1, max_length=255)
    depends_on_task_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("depends_on_task_name")
    @classmethod
    def validate_no_self_dependency(cls, v: str, info) -> str:
        """Ensure a task doesn't depend on itself."""
        if "task_name" in info.data and v == info.data["task_name"]:
            raise ValueError("A task cannot depend on itself")
        return v


class Feature(BaseModel):
    """Feature model with validation."""

    name: str = Field(..., min_length=1, max_length=55)
    description: str = Field(..., min_length=1, description="Feature description")
    specification: str = Field(..., min_length=1, description="Feature specification")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# Request models for function arguments
class ListTasksRequest(BaseModel):
    """Request model for list_tasks function."""

    status: Optional[str] = Field(None, description="Filter by status")
    priority_min: Optional[int] = Field(
        None, ge=0, le=10, description="Minimum priority filter"
    )
    feature_name: Optional[str] = Field(
        None, min_length=1, max_length=55, description="Filter by feature name"
    )


class GetTaskRequest(BaseModel):
    """Request model for get_task function."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Task name to retrieve"
    )


class AddTaskRequest(BaseModel):
    """Request model for add_task function."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Unique name for the task"
    )
    description: str = Field(
        ..., min_length=1, description="Description of what the task involves"
    )
    specification: str = Field(
        ...,
        min_length=1,
        description="Detailed task specification, including implementation notes",
    )
    feature_name: str = Field(
        default="misc",
        min_length=1,
        max_length=55,
        description="Feature this task belongs to",
    )
    tests_required: bool = Field(
        default=True,
        description="Whether tests are required for this task",
    )
    priority: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Priority level (0-10, higher is more important)",
    )
    status: str = Field(default="pending", description="Initial status")
    dependencies: Optional[List[str]] = Field(
        default=None, description="List of task names this task depends on"
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> str:
        """Validate status is one of the allowed values."""
        if isinstance(v, str):
            v = v.lower()
            valid_statuses = [status.value for status in TaskStatus]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
            return v
        raise ValueError(f"Invalid status type: {type(v)}")


class UpdateTaskRequest(BaseModel):
    """Request model for update_task function."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the task to update"
    )
    description: Optional[str] = Field(
        None, min_length=1, description="New description"
    )
    specification: Optional[str] = Field(None, description="New specification")
    status: Optional[str] = Field(None, description="New status")
    priority: Optional[int] = Field(None, ge=0, le=10, description="New priority")
    tests_required: Optional[bool] = Field(
        None, description="Whether tests are required for this task"
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> Optional[str]:
        """Validate status is one of the allowed values."""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.lower()
            valid_statuses = [status.value for status in TaskStatus]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
            return v
        raise ValueError(f"Invalid status type: {type(v)}")


class DeleteTaskRequest(BaseModel):
    """Request model for delete_task function."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the task to delete"
    )


class CompleteTaskRequest(BaseModel):
    """Request model for complete_task function."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the task to complete"
    )


class ListDependenciesRequest(BaseModel):
    """Request model for list_dependencies function."""

    task_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Filter dependencies for a specific task",
    )


class AddDependenciesRequest(BaseModel):
    """Request model for add_dependencies function."""

    task_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the task that depends on other tasks",
    )
    depends_on_task_names: List[str] = Field(
        ...,
        description="List of task names that must be completed first",
    )

    @field_validator("depends_on_task_names")
    @classmethod
    def validate_depends_on_task_names(cls, v: List[str], info) -> List[str]:
        """Ensure dependencies are not empty or self-referential."""
        if any(not name or not name.strip() for name in v):
            raise ValueError("Dependency task name cannot be empty")
        task_name = info.data.get("task_name")
        if task_name and any(dep_name == task_name for dep_name in v):
            raise ValueError("A task cannot depend on itself")
        return v


class AddDependencyRequest(BaseModel):
    """Request model for add_dependency function."""

    task_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the task that depends on another task",
    )
    depends_on_task_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the task that must be completed first",
    )

    @field_validator("depends_on_task_name")
    @classmethod
    def validate_no_self_dependency(cls, v: str, info) -> str:
        """Ensure a task doesn't depend on itself."""
        if "task_name" in info.data and v == info.data["task_name"]:
            raise ValueError("A task cannot depend on itself")
        return v


class RemoveDependencyRequest(BaseModel):
    """Request model for remove_dependency function."""

    task_name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the task"
    )
    depends_on_task_name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the task it depends on"
    )

    @field_validator("depends_on_task_name")
    @classmethod
    def validate_no_self_dependency(cls, v: str, info) -> str:
        """Ensure a task doesn't depend on itself."""
        if "task_name" in info.data and v == info.data["task_name"]:
            raise ValueError("A task cannot depend on itself")
        return v


class AddFeatureRequest(BaseModel):
    """Request model for add_feature function."""

    name: str = Field(
        ..., min_length=1, max_length=55, description="Unique name for the feature"
    )
    description: str = Field(
        ..., min_length=1, description="Description of the feature"
    )
    specification: str = Field(
        ..., min_length=1, description="Specification for the feature"
    )


class DeleteFeatureRequest(BaseModel):
    """Request model for delete_feature function."""

    name: str = Field(
        ..., min_length=1, max_length=55, description="Name of the feature to delete"
    )


# Response models for function returns
class TaskResponse(BaseModel):
    """Response model for task data."""

    name: str = Field(..., description="Task name")
    description: str = Field(..., description="Task description")
    specification: str = Field(..., description="Task specification")
    feature_name: str = Field(..., description="Feature this task belongs to")
    tests_required: bool = Field(..., description="Whether tests are required")
    priority: int = Field(..., ge=0, le=10, description="Task priority")
    status: str = Field(..., description="Task status")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    updated_at: Optional[str] = Field(None, description="Update timestamp")

    model_config = {"from_attributes": True}

    @classmethod
    def from_dict(cls, data: dict) -> "TaskResponse":
        """Create a TaskResponse from a database dictionary."""
        return cls(**data)


class TaskListResponse(BaseModel):
    """Response model for list of tasks."""

    tasks: List[TaskResponse] = Field(..., description="List of tasks")

    @classmethod
    def from_list(cls, data: List[dict]) -> "TaskListResponse":
        """Create a TaskListResponse from a list of database dictionaries."""
        return cls(tasks=[TaskResponse.from_dict(item) for item in data])


class DependencyResponse(BaseModel):
    """Response model for dependency data."""

    task_name: str = Field(..., description="Name of the task")
    depends_on_task_name: str = Field(..., description="Name of the dependency task")

    model_config = {"from_attributes": True}

    @classmethod
    def from_dict(cls, data: dict) -> "DependencyResponse":
        """Create a DependencyResponse from a database dictionary."""
        return cls(**data)


class DependencyListResponse(BaseModel):
    """Response model for list of dependencies."""

    dependencies: List[DependencyResponse] = Field(
        ..., description="List of dependencies"
    )

    @classmethod
    def from_list(cls, data: List[dict]) -> "DependencyListResponse":
        """Create a DependencyListResponse from a list of database dictionaries."""
        return cls(dependencies=[DependencyResponse.from_dict(item) for item in data])


class TaskCreateResponse(BaseModel):
    """Response model for task creation."""

    task: TaskResponse = Field(..., description="Created task")


class TaskUpdateResponse(BaseModel):
    """Response model for task update."""

    task: Optional[TaskResponse] = Field(
        ..., description="Updated task or None if not found"
    )

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "TaskUpdateResponse":
        """Create a TaskUpdateResponse from an optional database dictionary."""
        return cls(task=TaskResponse.from_dict(data) if data else None)


class TaskDeleteResponse(BaseModel):
    """Response model for task deletion."""

    deleted: bool = Field(
        ..., description="True if task was deleted, False if not found"
    )


class DependencyCreateResponse(BaseModel):
    """Response model for dependency creation."""

    dependency: DependencyResponse = Field(..., description="Created dependency")


class DependencyRemoveResponse(BaseModel):
    """Response model for dependency removal."""

    removed: bool = Field(
        ..., description="True if dependency was removed, False if not found"
    )


class FeatureResponse(BaseModel):
    """Response model for feature data."""

    name: str = Field(..., description="Feature name")
    description: str = Field(..., description="Feature description")
    specification: str = Field(..., description="Feature specification")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Update timestamp")

    model_config = {"from_attributes": True}

    @classmethod
    def from_dict(cls, data: dict) -> "FeatureResponse":
        """Create a FeatureResponse from a database dictionary."""
        return cls(**data)


class TaskStartResponse(BaseModel):
    """Response model for starting a task with feature context."""

    task: TaskResponse = Field(..., description="Started task")
    feature: FeatureResponse = Field(..., description="Feature for the task")


class FeatureListResponse(BaseModel):
    """Response model for list of features."""

    features: List[FeatureResponse] = Field(..., description="List of features")

    @classmethod
    def from_list(cls, data: List[dict]) -> "FeatureListResponse":
        """Create a FeatureListResponse from a list of database dictionaries."""
        return cls(features=[FeatureResponse.from_dict(item) for item in data])


class FeatureCreateResponse(BaseModel):
    """Response model for feature creation."""

    feature: FeatureResponse = Field(..., description="Created feature")


class FeatureDeleteResponse(BaseModel):
    """Response model for feature deletion."""

    deleted: bool = Field(
        ..., description="True if feature was deleted, False if not found"
    )
