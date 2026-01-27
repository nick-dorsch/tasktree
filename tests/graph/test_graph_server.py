"""
Tests for the graph server (tasktree/graph_server.py).

Tests the HTTP API endpoints for retrieving task dependency graphs.
"""

# Import the server module
import json
import socket
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from time import sleep

import pytest

import tasktree.graph.server as graph_server
from tasktree.core.database import DependencyRepository, TaskRepository

GraphAPIHandler = graph_server.GraphAPIHandler
run_server = graph_server.run_server


@pytest.fixture
def mock_db_path(test_db: Path, monkeypatch):
    """
    Mock the DB_PATH to use the test database.

    This fixture modifies the database.DB_PATH to point to the test database,
    ensuring all repository operations use the isolated test database.
    """
    import tasktree.core.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


@pytest.fixture
def server_thread(test_db: Path):
    """
    Start the graph server in a background thread for testing.

    Args:
        test_db: Path to the test database

    Yields:
        int: port number the server is listening on
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        port = sock.getsockname()[1]

    # Start server in background thread
    thread = Thread(target=run_server, args=(port, test_db), daemon=True)
    thread.start()

    # Give server time to start
    sleep(0.1)

    yield port

    # Thread will be cleaned up automatically (daemon=True)


def fetch_graph_js(port: int) -> str:
    """Fetch the graph.js asset content from the running server."""
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/graph.js")
        response = conn.getresponse()
        assert response.status == 200
        return response.read().decode()
    finally:
        conn.close()


def fetch_task_ids(db_path: Path, *names: str) -> dict:
    """Fetch task IDs by name from the database."""
    if not names:
        return {}
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in names)
    cursor.execute(f"SELECT name, id FROM tasks WHERE name IN ({placeholders})", names)
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def test_graph_api_handler_class_exists():
    """Test that GraphAPIHandler class is properly defined."""
    assert hasattr(GraphAPIHandler, "do_GET")
    assert hasattr(GraphAPIHandler, "_handle_graph_request")
    assert hasattr(GraphAPIHandler, "_get_graph_json")


def test_get_graph_json_empty_database(test_db: Path):
    """Test get_graph_json helper function with an empty database."""
    # Test via direct SQL query (same as handler does)
    import sqlite3

    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT graph_json FROM v_graph_json")
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        graph = json.loads(result[0])
    else:
        graph = {"nodes": [], "edges": []}

    assert "nodes" in graph
    assert "edges" in graph
    assert graph["nodes"] == []
    assert graph["edges"] == []


def test_get_graph_json_with_tasks(mock_db_path):
    """Test graph JSON with tasks in the database."""
    # Add some tasks
    TaskRepository.add_task("task-1", "Description 1", priority=5)
    TaskRepository.add_task("task-2", "Description 2", priority=3)

    # Query graph JSON
    import sqlite3

    conn = sqlite3.connect(mock_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT graph_json FROM v_graph_json")
    result = cursor.fetchone()
    conn.close()

    graph = json.loads(result[0])

    # Verify structure
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 0

    # Verify node content
    node_names = {node["name"] for node in graph["nodes"]}
    node_ids = {node["id"] for node in graph["nodes"]}
    assert "task-1" in node_names
    assert "task-2" in node_names
    assert len(node_ids) == 2


def test_get_graph_json_with_dependencies(mock_db_path):
    """Test graph JSON with tasks and dependencies."""
    # Create tasks with dependencies
    TaskRepository.add_task("base-task", "Base task")
    TaskRepository.add_task("dependent-task", "Dependent task")
    DependencyRepository.add_dependency("dependent-task", "base-task")

    # Query graph JSON
    import sqlite3

    conn = sqlite3.connect(mock_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT graph_json FROM v_graph_json")
    result = cursor.fetchone()
    conn.close()

    graph = json.loads(result[0])

    # Verify edges
    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    task_ids = fetch_task_ids(mock_db_path, "dependent-task", "base-task")
    assert edge["from"] == task_ids["dependent-task"]
    assert edge["to"] == task_ids["base-task"]


def test_get_graph_json_includes_all_fields(mock_db_path):
    """Test that graph JSON includes all expected fields."""
    TaskRepository.add_task(
        "test-task", "Test description", priority=7, status="pending"
    )

    # Query graph JSON
    import sqlite3

    conn = sqlite3.connect(mock_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT graph_json FROM v_graph_json")
    result = cursor.fetchone()
    conn.close()

    graph = json.loads(result[0])
    node = graph["nodes"][0]

    # Verify all expected fields are present
    assert "id" in node
    assert "name" in node
    assert "description" in node
    assert "status" in node
    assert "priority" in node
    assert "completed_at" in node
    assert "started_at" in node
    assert "completion_minutes" in node
    assert "is_available" in node

    # Verify values
    assert node["name"] == "test-task"
    assert node["description"] == "Test description"
    assert node["status"] == "pending"
    assert node["priority"] == 7
    assert node["is_available"] == 1  # No dependencies, so available


def test_get_graph_json_is_available_flag(mock_db_path):
    """Test that is_available flag is correctly set based on dependencies."""
    # Create dependency chain
    TaskRepository.add_task("available-task", "Available", status="pending")
    TaskRepository.add_task("blocked-task", "Blocked", status="pending")
    DependencyRepository.add_dependency("blocked-task", "available-task")

    # Query graph JSON
    import sqlite3

    conn = sqlite3.connect(mock_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT graph_json FROM v_graph_json")
    result = cursor.fetchone()
    conn.close()

    graph = json.loads(result[0])

    # Check is_available flags
    nodes_by_name = {node["name"]: node for node in graph["nodes"]}

    assert nodes_by_name["available-task"]["is_available"] == 1
    assert nodes_by_name["blocked-task"]["is_available"] == 0


def test_api_graph_endpoint(mock_db_path, server_thread):
    """Test the /api/graph HTTP endpoint."""
    port = server_thread

    # Add test data
    TaskRepository.add_task("api-task", "API test task", priority=5)

    # Make HTTP request
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()

        # Verify response
        assert response.status == 200
        assert response.getheader("Content-type") == "application/json"

        # Parse JSON response
        data = json.loads(response.read().decode())

        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "api-task"
    finally:
        conn.close()


def test_api_graph_endpoint_cors_header(mock_db_path, server_thread):
    """Test that the /api/graph endpoint includes CORS headers."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()

        # Verify CORS header is present
        assert response.getheader("Access-Control-Allow-Origin") == "*"
    finally:
        conn.close()


def test_root_endpoint_returns_html(server_thread):
    """Test that the root endpoint returns HTML with visualization."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        assert response.status == 200
        assert response.getheader("Content-type") == "text/html"

        html = response.read().decode()
        assert "<html" in html
        assert "/static/graph.js" in html
    finally:
        conn.close()


def test_not_found_endpoint(server_thread):
    """Test that unknown endpoints return 404."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/unknown")
        response = conn.getresponse()

        assert response.status == 404

        # Should return JSON error
        data = json.loads(response.read().decode())
        assert "error" in data
        assert data["status"] == 404
    finally:
        conn.close()


def test_graph_endpoint_with_complex_dependencies(mock_db_path, server_thread):
    """Test /api/graph with a complex dependency graph."""
    port = server_thread

    # Create a complex dependency graph
    TaskRepository.add_task("task-a", "Task A")
    TaskRepository.add_task("task-b", "Task B")
    TaskRepository.add_task("task-c", "Task C")
    TaskRepository.add_task("task-d", "Task D")

    # Create dependencies: D -> C -> B -> A
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()

        data = json.loads(response.read().decode())

        # Verify all tasks are present
        assert len(data["nodes"]) == 4

        # Verify all dependencies are present
        assert len(data["edges"]) == 3

        # Verify availability: only task-a should be available
        nodes_by_name = {node["name"]: node for node in data["nodes"]}
        assert nodes_by_name["task-a"]["is_available"] == 1
        assert nodes_by_name["task-b"]["is_available"] == 0
        assert nodes_by_name["task-c"]["is_available"] == 0
        assert nodes_by_name["task-d"]["is_available"] == 0
    finally:
        conn.close()


def test_graph_endpoint_with_completed_tasks(mock_db_path, server_thread):
    """Test that completed tasks appear correctly in the graph."""
    port = server_thread

    # Add task and mark as completed
    TaskRepository.add_task("completed-task", "Completed", status="pending")
    TaskRepository.update_task("completed-task", status="completed")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()

        data = json.loads(response.read().decode())

        node = data["nodes"][0]
        assert node["status"] == "completed"
        assert node["completed_at"] is not None
    finally:
        conn.close()


def test_graph_endpoint_json_formatting(mock_db_path, server_thread):
    """Test that the JSON response is properly formatted."""
    port = server_thread

    TaskRepository.add_task("test", "Test task")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()

        raw_json = response.read().decode()

        # Should be pretty-printed (contains newlines and indentation)
        assert "\n" in raw_json
        assert "  " in raw_json  # Indentation

        # Should be valid JSON
        data = json.loads(raw_json)
        assert isinstance(data, dict)
    finally:
        conn.close()


def test_root_endpoint_includes_task_panel(mock_db_path, server_thread):
    """Test that the root endpoint includes the task list panel."""
    port = server_thread

    # Add some tasks with different statuses and priorities
    TaskRepository.add_task("high-priority-task", "High priority", priority=10)
    TaskRepository.add_task("low-priority-task", "Low priority", priority=2)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for task panel structure
        assert "task-panel" in html
        assert "panel-header" in html
        assert "task-list" in html

        # Check for glassmorphism styling
        assert "backdrop-filter: blur" in html
        assert "rgba(0, 0, 0, 0.6)" in html

        # Check for task items
        assert "high-priority-task" in html
        assert "low-priority-task" in html
    finally:
        conn.close()


def test_root_endpoint_task_panel_priority_sorting(mock_db_path, server_thread):
    """Test that tasks in the panel are sorted by priority (descending)."""
    port = server_thread

    # Add tasks with different priorities
    TaskRepository.add_task("priority-3", "Task 3", priority=3)
    TaskRepository.add_task("priority-8", "Task 8", priority=8)
    TaskRepository.add_task("priority-5", "Task 5", priority=5)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Find positions of task names in HTML
        pos_3 = html.find("priority-3")
        pos_5 = html.find("priority-5")
        pos_8 = html.find("priority-8")

        # Higher priority should appear earlier in the HTML
        assert pos_8 < pos_5 < pos_3
    finally:
        conn.close()


def test_root_endpoint_task_panel_status_ordering(mock_db_path, server_thread):
    """Test that tasks in the panel are sorted by status (blocked, in_progress, pending, completed), then priority."""
    port = server_thread

    # Add tasks with different statuses and priorities
    TaskRepository.add_task(
        "completed-high", "Completed high priority", priority=10, status="completed"
    )
    TaskRepository.add_task(
        "pending-high", "Pending high priority", priority=9, status="pending"
    )
    TaskRepository.add_task(
        "in-progress-low", "In progress low priority", priority=5, status="in_progress"
    )
    TaskRepository.add_task(
        "blocked-medium", "Blocked medium priority", priority=7, status="blocked"
    )

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Find positions of task names in HTML
        pos_blocked = html.find("blocked-medium")
        pos_in_progress = html.find("in-progress-low")
        pos_pending = html.find("pending-high")
        pos_completed = html.find("completed-high")

        # Status order should be: blocked, in_progress, pending, completed
        assert pos_blocked < pos_in_progress < pos_pending < pos_completed
    finally:
        conn.close()


def test_root_endpoint_task_panel_status_colors(mock_db_path, server_thread):
    """Test that task panel shows correct status color coding."""
    port = server_thread

    # Add tasks with different statuses
    TaskRepository.add_task("pending-task", "Pending", status="pending")
    TaskRepository.add_task("in-progress-task", "In Progress", status="in_progress")
    TaskRepository.add_task("completed-task", "Completed", status="completed")
    TaskRepository.add_task("blocked-task", "Blocked", status="blocked")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for status colors (these match the STATUS_COLORS in the viewer)
        assert "#2196F3" in html  # Pending - Blue
        assert "#FFC107" in html  # In Progress - Yellow/Amber
        assert "#4CAF50" in html  # Completed - Green
        assert "#F44336" in html  # Blocked - Red
    finally:
        conn.close()


def test_root_endpoint_task_panel_overall_times(mock_db_path, server_thread):
    """Test that task panel header does not show overall started_at and completed_at."""
    port = server_thread

    # Add tasks with started_at and completed_at times
    TaskRepository.add_task("task-1", "Task 1", status="pending")
    TaskRepository.update_task("task-1", status="in_progress")

    TaskRepository.add_task("task-2", "Task 2", status="pending")
    TaskRepository.update_task("task-2", status="in_progress")
    TaskRepository.complete_task("task-2")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Verify panel header does NOT contain overall started/completed metadata
        # The panel-meta div should not exist in the header
        assert 'class="panel-meta"' not in html
        # Panel header should still exist
        assert 'class="panel-header"' in html
    finally:
        conn.close()


def test_root_endpoint_task_panel_empty_state(server_thread):
    """Test that task panel shows appropriate message when no tasks exist."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for empty state message
        assert "No tasks available" in html
    finally:
        conn.close()


def test_root_endpoint_task_panel_full_description_in_details(
    mock_db_path, server_thread
):
    """Test that full description appears in expandable details section."""
    port = server_thread

    # Add task with a very long description
    long_desc = "A" * 150  # 150 characters
    TaskRepository.add_task("long-desc-task", long_desc)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Full description should appear in the details section
        assert long_desc in html
        # Description should be in the details section
        assert "Description:" in html
    finally:
        conn.close()


def test_root_endpoint_includes_graph_visualization(server_thread):
    """Test that root endpoint includes the D3.js graph visualization."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for D3.js script
        assert "d3js.org/d3.v7.min.js" in html

        # Check for graph container
        assert 'id="graph"' in html

        # Check that the external script is referenced
        assert "/static/graph.js" in html
    finally:
        conn.close()

    graph_js = fetch_graph_js(port)

    # Check for force simulation code
    assert "forceSimulation" in graph_js
    assert "forceLink" in graph_js

    # Check for API endpoint reference
    assert "/api/graph" in graph_js


def test_root_endpoint_legend_includes_blocked_status(server_thread):
    """Test that the legend includes the blocked status."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check that legend includes all status types
        assert "Blocked" in html
        assert "In Progress" in html
        assert "Pending" in html
        assert "Completed" in html

        # Check that blocked status appears in legend with correct color
        # The legend should contain the blocked color (#F44336)
        assert "#F44336" in html
    finally:
        conn.close()


def test_root_endpoint_task_items_collapsed_by_default(mock_db_path, server_thread):
    """Test that task items are collapsed by default with expandable details."""
    port = server_thread

    # Add task with various details
    TaskRepository.add_task(
        "test-task",
        "Test description",
        priority=5,
        status="pending",
        specification="Additional details about the task",
    )

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for task header with expand icon
        assert "task-header" in html
        assert "task-expand-icon" in html
        assert "▶" in html

        # Check that details section exists but is hidden by default
        assert "task-details" in html
        assert 'style="display: none;"' in html

        # Check that onclick handler is present
        assert "toggleTaskDetails" in html
    finally:
        conn.close()


def test_root_endpoint_task_details_section_content(mock_db_path, server_thread):
    """Test that task details section includes all expected fields."""
    port = server_thread

    # Add task and progress it through states
    TaskRepository.add_task(
        "detailed-task",
        "Full description",
        priority=7,
        status="pending",
        specification="Implementation details here",
    )
    TaskRepository.update_task("detailed-task", status="in_progress")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for details section fields
        assert "task-details-row" in html
        assert "task-details-label" in html

        # Check for all expected labels
        assert "Status:" in html
        assert "Priority:" in html
        assert "Description:" in html
        assert "Details:" in html
        assert "Created:" in html
        assert "Started:" in html

        # Check for values
        assert "in_progress" in html
        assert "Full description" in html
        assert "Implementation details here" in html
    finally:
        conn.close()


def test_root_endpoint_task_details_handles_null_fields(mock_db_path, server_thread):
    """Test that task details properly handle null/empty fields."""
    port = server_thread

    # Add minimal task (no details, not started, not completed)
    TaskRepository.add_task("minimal-task", "Basic description", priority=3)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check that empty description renders as None
        # (though description is required, this tests the pattern)
        # Details field should not appear if null
        task_item_start = html.find('data-status="pending"')
        task_item_end = html.find("</div>", task_item_start + 200)
        task_item_section = html[task_item_start:task_item_end]

        # Started and Completed should not appear for pending tasks with no times
        # Check that started_at and completed_at are conditionally shown
        assert "Started:" not in task_item_section or "None" not in task_item_section
    finally:
        conn.close()


def test_root_endpoint_task_details_shows_completed_at(mock_db_path, server_thread):
    """Test that completed tasks show completed_at timestamp."""
    port = server_thread

    # Add and complete a task
    TaskRepository.add_task("completed-task", "Done task", priority=5)
    TaskRepository.update_task("completed-task", status="in_progress")
    TaskRepository.complete_task("completed-task")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for completed timestamp
        assert "Completed:" in html
        # Should have a timestamp (year prefix)
        assert "2026-" in html or "202" in html
    finally:
        conn.close()


def test_root_endpoint_toggle_function_exists(server_thread):
    """Test that toggleTaskDetails JavaScript function is defined."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Check for toggle function definition
    assert "function toggleTaskDetails" in graph_js
    assert "querySelector('.task-details')" in graph_js
    assert "querySelector('.task-expand-icon')" in graph_js
    assert "classList.add('expanded')" in graph_js
    assert "classList.remove('expanded')" in graph_js


def test_root_endpoint_task_details_css_styling(server_thread):
    """Test that task details CSS styles are present."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for CSS class definitions
        assert ".task-details {" in html or ".task-details{{" in html
        assert ".task-details-row" in html
        assert ".task-details-label" in html
        assert ".task-expand-icon" in html
        assert ".task-expand-icon.expanded" in html

        # Check for specific styling (expand icon rotation)
        assert "transform: rotate(90deg)" in html
    finally:
        conn.close()


def test_root_endpoint_task_header_clickable(mock_db_path, server_thread):
    """Test that task headers are clickable for expanding."""
    port = server_thread

    TaskRepository.add_task("clickable-task", "Test", priority=5)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check that task-header has cursor pointer and is clickable
        assert "cursor: pointer" in html
        assert "onclick=" in html or 'onclick="toggleTaskDetails' in html
    finally:
        conn.close()


def test_root_endpoint_tooltip_shows_started_at_conditionally(server_thread):
    """Test that tooltip shows started_at only when non-null."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Check that tooltip function conditionally shows started_at
    assert "d.started_at" in graph_js
    assert "Started:" in graph_js

    # Should use conditional rendering (ternary or template literal)
    # Pattern: ${d.started_at ? `<div>...Started:...</div>` : ''}
    assert "d.started_at ?" in graph_js or "started_at?" in graph_js


def test_root_endpoint_tooltip_shows_completion_minutes(server_thread):
    """Test that tooltip shows completion_minutes when available."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Check that tooltip function shows completion_minutes
    assert "d.completion_minutes" in graph_js
    assert "Duration:" in graph_js or "completion_minutes" in graph_js

    # Should use conditional rendering for completion_minutes
    # Pattern: ${d.completion_minutes !== null ? `<div>...Duration:...</div>` : ''}
    assert (
        "completion_minutes !== null" in graph_js
        or "completion_minutes !==" in graph_js
    )


def test_root_endpoint_accordion_behavior(mock_db_path, server_thread):
    """Test that toggleTaskDetails function implements accordion behavior (only one expanded at a time)."""
    port = server_thread

    # Add multiple tasks
    TaskRepository.add_task("task-1", "First task", priority=5)
    TaskRepository.add_task("task-2", "Second task", priority=4)
    TaskRepository.add_task("task-3", "Third task", priority=3)

    graph_js = fetch_graph_js(port)

    # Check that toggleTaskDetails closes all other tasks before opening
    assert "querySelectorAll('.task-details')" in graph_js
    assert "querySelectorAll('.task-expand-icon')" in graph_js

    # Should iterate through all task details and close them
    assert "forEach" in graph_js

    # Should set display to none for all details
    assert (
        "details.style.display = 'none'" in graph_js
        or "style.display='none'" in graph_js
    )

    # Should remove expanded class from all icons
    assert "classList.remove('expanded')" in graph_js

    # Should expand only the clicked task
    assert (
        "detailsDiv.style.display = 'block'" in graph_js
        or "style.display='block'" in graph_js
    )
    assert "expandIcon.classList.add('expanded')" in graph_js


def test_root_endpoint_description_scrollable_container(mock_db_path, server_thread):
    """Test that description and details fields use scrollable containers."""
    port = server_thread

    # Add task with long description and details
    long_description = "This is a very long description. " * 20  # ~600 characters
    long_details = "These are extensive details. " * 30  # ~900 characters

    TaskRepository.add_task(
        "long-content-task",
        long_description,
        priority=5,
        specification=long_details,
    )

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for task-details-value CSS class
        assert ".task-details-value" in html or ".task-details-value{" in html

        # Check that description and details use the scrollable container class
        assert 'class="task-details-value"' in html

        # Check for scrollable container styles
        assert "max-height:" in html  # Should have max-height constraint
        assert "overflow-y: auto" in html  # Should be scrollable

        # Check for word wrapping
        assert "word-wrap: break-word" in html or "word-break:" in html

        # Check for scrollbar styling
        assert "::-webkit-scrollbar" in html

        # Verify that description is on a new line (display: block)
        assert "display: block" in html
    finally:
        conn.close()


def test_root_endpoint_description_details_new_lines(mock_db_path, server_thread):
    """Test that description and details start on new lines, not inline."""
    port = server_thread

    TaskRepository.add_task(
        "test-task",
        "Task description text",
        priority=5,
        specification="Task details text",
    )

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check that description has its own div container (not just inline span)
        # Pattern should be:
        # <div class="task-details-row">
        #   <span class="task-details-label">Description:</span>
        #   <div class="task-details-value">Task description text</div>
        # </div>

        # Find description section
        desc_index = html.find('task-details-label">Description:</span>')
        assert desc_index != -1, "Description label not found"

        # Check that description value is in a div, not inline
        after_desc_label = html[desc_index : desc_index + 200]
        assert '<div class="task-details-value">' in after_desc_label

        # Find details section
        details_index = html.find('task-details-label">Details:</span>')
        if details_index != -1:  # Only check if details exist
            after_details_label = html[details_index : details_index + 200]
            assert '<div class="task-details-value">' in after_details_label
    finally:
        conn.close()


def test_root_endpoint_scrollable_container_max_height(server_thread):
    """Test that scrollable containers have appropriate max-height."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for max-height in task-details-value CSS
        # Should be reasonable (e.g., 100px) to trigger scrolling
        assert ".task-details-value" in html

        # Extract the CSS section for task-details-value
        value_css_start = html.find(".task-details-value")
        value_css_end = html.find("}", value_css_start)
        value_css = html[value_css_start:value_css_end]

        # Check for max-height property
        assert "max-height:" in value_css
        # Should have overflow-y: auto for scrolling
        assert "overflow-y: auto" in value_css or "overflow-y:auto" in value_css
    finally:
        conn.close()


def test_api_tasks_endpoint_exists(server_thread):
    """Test that the /api/tasks endpoint exists and returns JSON."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/tasks")
        response = conn.getresponse()

        assert response.status == 200
        assert response.getheader("Content-type") == "application/json"
    finally:
        conn.close()


def test_api_tasks_endpoint_empty_database(server_thread):
    """Test /api/tasks with no tasks in the database."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/tasks")
        response = conn.getresponse()

        data = json.loads(response.read().decode())

        assert "tasks" in data
        assert isinstance(data["tasks"], list)
        assert len(data["tasks"]) == 0
    finally:
        conn.close()


def test_api_tasks_endpoint_with_tasks(mock_db_path, server_thread):
    """Test /api/tasks returns all tasks with proper formatting."""
    port = server_thread

    # Add some tasks
    TaskRepository.add_task("task-1", "First task", priority=5)
    TaskRepository.add_task("task-2", "Second task", priority=3)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/tasks")
        response = conn.getresponse()

        data = json.loads(response.read().decode())

        assert len(data["tasks"]) == 2

        # Check first task structure
        task = data["tasks"][0]
        assert "name" in task
        assert "description" in task
        assert "status" in task
        assert "priority" in task
        assert "created_at" in task
        assert "started_at" in task
        assert "completed_at" in task
        assert "specification" in task
        assert "feature_name" in task
        assert "feature_description" in task
        assert "feature_created_at" in task
        assert "tests_required" in task
        assert "updated_at" in task
    finally:
        conn.close()


def test_api_tasks_endpoint_sorting(mock_db_path, server_thread):
    """Test that /api/tasks returns tasks sorted by status, priority, created_at."""
    port = server_thread

    # Add tasks with different statuses, priorities, and created_at times
    TaskRepository.add_task("completed-high", "Done", priority=10, status="completed")
    TaskRepository.add_task("pending-high", "Pending", priority=9, status="pending")
    TaskRepository.add_task(
        "in-progress-low", "Working", priority=5, status="in_progress"
    )
    TaskRepository.add_task("blocked-medium", "Blocked", priority=7, status="blocked")

    # Add two tasks with same status and priority but different created_at to test created_at ordering
    TaskRepository.add_task("pending-old", "Old pending", priority=9, status="pending")
    # This one should come after pending-old due to later created_at
    TaskRepository.add_task("pending-new", "New pending", priority=9, status="pending")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/tasks")
        response = conn.getresponse()

        data = json.loads(response.read().decode())

        task_names = [task["name"] for task in data["tasks"]]

        # Debug: print the actual task names
        print(f"Actual task names: {task_names}")

        # Order should be: blocked, in_progress, pending, completed
        assert task_names.index("blocked-medium") < task_names.index("in-progress-low")
        assert task_names.index("in-progress-low") < task_names.index("pending-high")
        assert task_names.index("pending-high") < task_names.index("completed-high")

        # For same status and priority, should be ordered by created_at ASC
        # pending-old should come before pending-new
        assert task_names.index("pending-old") < task_names.index("pending-new")
    finally:
        conn.close()


def test_root_endpoint_includes_tasks_endpoint(server_thread):
    """Test that the root endpoint includes reference to /api/tasks."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Should include TASKS_ENDPOINT constant
    assert "TASKS_ENDPOINT" in graph_js
    assert "/api/tasks" in graph_js


def test_root_endpoint_renders_template_placeholders(mock_db_path, server_thread):
    """Test that template placeholders are replaced in the root response."""
    port = server_thread

    TaskRepository.add_task("templated-task", "Template task")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        assert "{{TASK_ITEMS}}" not in html
        assert "templated-task" in html
        assert "misc" in html
        assert "feature-group" in html
    finally:
        conn.close()


def test_root_endpoint_feature_header_includes_description_and_created_at(
    mock_db_path, server_thread
):
    """Test that feature headers include description and created_at."""
    port = server_thread

    # Add a task to get the default 'misc' feature
    TaskRepository.add_task("test-task", "Test task", priority=5)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        html = response.read().decode()

        # Check for feature description and created_at in the HTML
        assert "feature-description" in html or 'class="feature-description"' in html
        assert "feature-created-at" in html or 'class="feature-created-at"' in html

        # Check that the default misc feature description is present
        assert "Default feature for uncategorized tasks" in html

        # Check that feature meta info CSS classes exist
        assert "feature-main-info" in html
        assert "feature-meta-info" in html

        # Check that created_at timestamp format is present (year prefix)
        assert "202" in html  # Should contain a year like 2026-XX-XX
    finally:
        conn.close()


def test_root_endpoint_includes_fetch_tasks_function(server_thread):
    """Test that fetchTasks function is defined in the HTML."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Check for fetchTasks function
    assert (
        "function fetchTasks()" in graph_js or "async function fetchTasks()" in graph_js
    )
    assert "fetch(TASKS_ENDPOINT)" in graph_js
    assert "updateTaskList" in graph_js


def test_root_endpoint_includes_update_task_list_function(server_thread):
    """Test that updateTaskList function is defined."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Check for updateTaskList function
    assert "function updateTaskList(tasks)" in graph_js
    assert "querySelector('.task-list')" in graph_js


def test_root_endpoint_auto_refresh_includes_tasks(server_thread):
    """Test that auto-refresh interval calls both fetchGraph and fetchTasks."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Check that setInterval calls both functions
    assert "setInterval" in graph_js
    assert "fetchGraph()" in graph_js
    assert "fetchTasks()" in graph_js

    # Should be in the same interval block
    interval_start = graph_js.find("setInterval")
    interval_end = graph_js.find("}", interval_start)
    interval_block = graph_js[interval_start:interval_end]

    assert "fetchGraph" in interval_block
    assert "fetchTasks" in interval_block


def test_api_tasks_endpoint_includes_feature_info(mock_db_path, server_thread):
    """Test /api/tasks includes feature description and created_at."""
    port = server_thread

    # Add a task to get default 'misc' feature
    TaskRepository.add_task("test-task", "Test task", priority=5)

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/tasks")
        response = conn.getresponse()

        data = json.loads(response.read().decode())

        assert len(data["tasks"]) == 1
        task = data["tasks"][0]

        # Check feature info is present
        assert "feature_description" in task
        assert "feature_created_at" in task

        # Check values are reasonable (misc feature from seed data)
        assert task["feature_name"] == "misc"
        assert task["feature_description"] == "Default feature for uncategorized tasks"
        assert task["feature_created_at"] is not None
    finally:
        conn.close()


def test_update_task_list_preserves_expanded_state(server_thread):
    """Test that updateTaskList preserves which tasks are expanded."""
    port = server_thread

    graph_js = fetch_graph_js(port)

    # Check that updateTaskList stores expanded task names
    assert "expandedTasks" in graph_js
    assert "new Set()" in graph_js

    # Check that updateTaskList stores expanded feature names
    assert "expandedFeatures" in graph_js
    assert "feature-group" in graph_js

    # Should check which tasks are currently expanded
    assert "style.display === 'block'" in graph_js or "display==='block'" in graph_js

    # Should restore expanded state after rebuild
    assert "shouldExpand" in graph_js or "expandedTasks.has" in graph_js
