"""
Data models for TaskTree.
"""

from enum import StrEnum
from typing import Any, Optional

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
