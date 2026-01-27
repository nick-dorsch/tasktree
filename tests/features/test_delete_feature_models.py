"""
Tests for DeleteFeatureRequest and FeatureDeleteResponse models.
"""

from tasktree.core.models import DeleteFeatureRequest, FeatureDeleteResponse
import pytest
from pydantic import ValidationError


def test_delete_feature_request_valid():
    """Test valid DeleteFeatureRequest instantiation."""
    request = DeleteFeatureRequest(name="test-feature")
    assert request.name == "test-feature"


def test_delete_feature_request_invalid_empty():
    """Test DeleteFeatureRequest with empty name."""
    with pytest.raises(ValidationError):
        DeleteFeatureRequest(name="")


def test_delete_feature_request_invalid_too_long():
    """Test DeleteFeatureRequest with too long name."""
    with pytest.raises(ValidationError):
        DeleteFeatureRequest(name="a" * 56)


def test_feature_delete_response_valid():
    """Test valid FeatureDeleteResponse instantiation."""
    response = FeatureDeleteResponse(deleted=True)
    assert response.deleted is True

    response = FeatureDeleteResponse(deleted=False)
    assert response.deleted is False
