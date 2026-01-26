"""
Tests for the graph viewer HTML (scripts/graph-viewer.html).

Tests that the HTML file exists and contains required D3.js visualization components.
"""

from pathlib import Path

import pytest


@pytest.fixture
def graph_viewer_path():
    """Get the path to the graph viewer HTML file."""
    return Path(__file__).parent.parent / "scripts" / "graph-viewer.html"


def test_graph_viewer_file_exists(graph_viewer_path):
    """Test that the graph viewer HTML file exists."""
    assert graph_viewer_path.exists()
    assert graph_viewer_path.is_file()


def test_graph_viewer_has_html_structure(graph_viewer_path):
    """Test that the HTML file has basic HTML structure."""
    content = graph_viewer_path.read_text()

    # Check for basic HTML structure
    assert "<!DOCTYPE html>" in content
    assert "<html" in content
    assert "<head>" in content
    assert "<body>" in content
    assert "</html>" in content


def test_graph_viewer_includes_d3_library(graph_viewer_path):
    """Test that the HTML includes the D3.js library."""
    content = graph_viewer_path.read_text()

    # Check for D3.js CDN link
    assert "d3js.org/d3" in content or "d3.min.js" in content


def test_graph_viewer_has_graph_container(graph_viewer_path):
    """Test that the HTML has a container for the graph."""
    content = graph_viewer_path.read_text()

    # Check for graph container element
    assert 'id="graph"' in content


def test_graph_viewer_has_api_endpoint_config(graph_viewer_path):
    """Test that the HTML defines the API endpoint."""
    content = graph_viewer_path.read_text()

    # Check for API endpoint configuration
    assert "localhost:8000" in content or "API_ENDPOINT" in content
    assert "/api/graph" in content


def test_graph_viewer_has_status_colors(graph_viewer_path):
    """Test that status-based color coding is defined."""
    content = graph_viewer_path.read_text()

    # Check for status colors (case-insensitive)
    content_lower = content.lower()

    # Should define colors for different statuses
    assert "pending" in content_lower
    assert "in_progress" in content_lower or "in progress" in content_lower
    assert "completed" in content_lower


def test_graph_viewer_has_force_simulation(graph_viewer_path):
    """Test that D3 force simulation is configured."""
    content = graph_viewer_path.read_text()

    # Check for D3 force simulation elements
    assert "forceSimulation" in content or "force simulation" in content.lower()


def test_graph_viewer_has_tooltip(graph_viewer_path):
    """Test that tooltip functionality is included."""
    content = graph_viewer_path.read_text()

    # Check for tooltip elements
    assert "tooltip" in content.lower()


def test_graph_viewer_has_node_rendering(graph_viewer_path):
    """Test that node rendering is implemented."""
    content = graph_viewer_path.read_text()

    # Check for node-related code
    assert "node" in content.lower()
    # Check for circle or similar node shape
    assert "circle" in content.lower() or "rect" in content.lower()


def test_graph_viewer_has_link_rendering(graph_viewer_path):
    """Test that link/edge rendering is implemented."""
    content = graph_viewer_path.read_text()

    # Check for link/edge-related code
    assert "link" in content.lower() or "edge" in content.lower()


def test_graph_viewer_has_drag_behavior(graph_viewer_path):
    """Test that drag-and-drop behavior is implemented."""
    content = graph_viewer_path.read_text()

    # Check for drag behavior
    assert "drag" in content.lower()


def test_graph_viewer_has_zoom_behavior(graph_viewer_path):
    """Test that zoom/pan behavior is implemented."""
    content = graph_viewer_path.read_text()

    # Check for zoom functionality
    assert "zoom" in content.lower()


def test_graph_viewer_has_auto_refresh(graph_viewer_path):
    """Test that auto-refresh functionality is included."""
    content = graph_viewer_path.read_text()

    # Check for interval/polling mechanism
    assert "setInterval" in content or "setTimeout" in content


def test_graph_viewer_has_error_handling(graph_viewer_path):
    """Test that error handling is implemented."""
    content = graph_viewer_path.read_text()

    # Check for error handling
    assert "catch" in content or "error" in content.lower()


def test_graph_viewer_has_fetch_api_call(graph_viewer_path):
    """Test that the HTML fetches data from the API."""
    content = graph_viewer_path.read_text()

    # Check for fetch API call
    assert "fetch" in content.lower()


def test_graph_viewer_has_arrowhead_marker(graph_viewer_path):
    """Test that directed graph arrows are defined."""
    content = graph_viewer_path.read_text()

    # Check for SVG marker definition for arrows
    assert "marker" in content.lower()
    assert "arrowhead" in content.lower() or "arrow" in content.lower()


def test_graph_viewer_styling_included(graph_viewer_path):
    """Test that CSS styling is included."""
    content = graph_viewer_path.read_text()

    # Check for style tag or CSS
    assert "<style>" in content or "css" in content.lower()


def test_graph_viewer_has_title(graph_viewer_path):
    """Test that the HTML has a descriptive title."""
    content = graph_viewer_path.read_text()

    # Check for title
    assert "<title>" in content
    assert "TaskTree" in content or "Graph" in content


def test_graph_viewer_responsive_design(graph_viewer_path):
    """Test that viewport meta tag is included for responsive design."""
    content = graph_viewer_path.read_text()

    # Check for viewport meta tag
    assert "viewport" in content


def test_graph_viewer_uses_svg(graph_viewer_path):
    """Test that visualization uses SVG."""
    content = graph_viewer_path.read_text()

    # Check for SVG usage
    assert "svg" in content.lower()


def test_graph_viewer_has_priority_based_sizing(graph_viewer_path):
    """Test that priority-based node sizing is implemented."""
    content = graph_viewer_path.read_text()

    # Check for priority-based sizing logic
    assert "priority" in content.lower()


def test_graph_viewer_has_available_task_highlighting(graph_viewer_path):
    """Test that available tasks are visually highlighted."""
    content = graph_viewer_path.read_text()

    # Check for is_available flag usage
    assert "is_available" in content or "available" in content.lower()
