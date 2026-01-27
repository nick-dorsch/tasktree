"""
Tests for deleting features from the repository.
"""

from pathlib import Path
import pytest

from tasktree.core.database import (
    FeatureRepository,
    TaskRepository,
    DependencyRepository,
)


@pytest.fixture
def mock_db_path(test_db: Path, monkeypatch):
    """
    Mock the DB_PATH to use the test database.
    """
    import tasktree.core.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


def test_delete_feature_success(mock_db_path):
    """Test successfully deleting a feature."""
    # Arrange
    FeatureRepository.add_feature(
        name="test-feature", description="A feature to delete", specification="Spec"
    )

    # Act
    deleted = FeatureRepository.delete_feature("test-feature")

    # Assert
    assert deleted is True
    assert FeatureRepository.get_feature("test-feature") is None


def test_delete_nonexistent_feature(mock_db_path):
    """Test deleting a feature that does not exist."""
    # Act
    deleted = FeatureRepository.delete_feature("nonexistent")

    # Assert
    assert deleted is False


def test_delete_misc_feature_fails(mock_db_path):
    """Test that deleting the 'misc' feature raises a ValueError."""
    # Act & Assert
    with pytest.raises(ValueError, match="The 'misc' feature cannot be deleted"):
        FeatureRepository.delete_feature("misc")


def test_delete_feature_cascades_to_tasks(mock_db_path):
    """Test that deleting a feature cascades to its tasks."""
    # Arrange
    FeatureRepository.add_feature(
        name="cascade-feature", description="Feature with tasks", specification="Spec"
    )
    TaskRepository.add_task(
        name="task-1",
        description="Task in feature",
        specification="Spec",
        feature_name="cascade-feature",
    )
    TaskRepository.add_task(
        name="task-2",
        description="Another task in feature",
        specification="Spec",
        feature_name="cascade-feature",
    )

    # Verify tasks exist
    assert TaskRepository.get_task("task-1") is not None
    assert TaskRepository.get_task("task-2") is not None

    # Act
    FeatureRepository.delete_feature("cascade-feature")

    # Assert
    assert TaskRepository.get_task("task-1") is None
    assert TaskRepository.get_task("task-2") is None


def test_delete_feature_cascades_to_dependencies(mock_db_path):
    """Test that deleting a feature cascades to dependencies between its tasks."""
    # Arrange
    FeatureRepository.add_feature(
        name="dep-feature",
        description="Feature with dependencies",
        specification="Spec",
    )
    TaskRepository.add_task(
        name="task-a",
        description="Task A",
        specification="Spec",
        feature_name="dep-feature",
    )
    TaskRepository.add_task(
        name="task-b",
        description="Task B",
        specification="Spec",
        feature_name="dep-feature",
    )
    DependencyRepository.add_dependency("task-b", "task-a")

    # Verify dependency exists
    deps = DependencyRepository.list_dependencies()
    assert any(
        d.task_name == "task-b" and d.depends_on_task_name == "task-a" for d in deps
    )

    # Act
    FeatureRepository.delete_feature("dep-feature")

    # Assert
    deps = DependencyRepository.list_dependencies()
    assert not any(
        d.task_name == "task-b" and d.depends_on_task_name == "task-a" for d in deps
    )
    assert TaskRepository.get_task("task-a") is None
    assert TaskRepository.get_task("task-b") is None
