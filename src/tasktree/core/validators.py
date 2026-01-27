"""
Validation utilities for TaskTree.
"""

from typing import Optional

from .models import TaskStatus


def validate_status(status: Optional[str]) -> Optional[str]:
    """Validate status if provided."""
    if status is not None:
        status = status.lower()
        if status not in [s.value for s in TaskStatus]:
            raise ValueError(
                f"Invalid status. Must be one of: {', '.join([s.value for s in TaskStatus])}"
            )
    return status


def validate_priority(priority: Optional[int]) -> None:
    """Validate priority if provided."""
    if priority is not None and (priority < 0 or priority > 10):
        raise ValueError("Priority must be between 0 and 10")


def validate_task_name(name: str) -> None:
    """Validate task name."""
    if not name or not name.strip():
        raise ValueError("Task name cannot be empty")


def validate_description(description: Optional[str]) -> None:
    """Validate description if provided."""
    if description is not None and not description.strip():
        raise ValueError("Description cannot be empty")


def validate_specification(specification: Optional[str]) -> None:
    """Validate specification if provided."""
    if specification is not None and not specification.strip():
        raise ValueError("Specification cannot be empty")


def validate_feature_name(feature_name: Optional[str]) -> None:
    """Validate feature name if provided."""
    if feature_name is None:
        return
    if not feature_name.strip():
        raise ValueError("Feature name cannot be empty")
    if len(feature_name) > 55:
        raise ValueError("Feature name must be 55 characters or fewer")
