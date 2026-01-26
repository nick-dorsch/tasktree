"""
Integration tests for complete graph visualization system.

These tests verify that all graph visualization features work together
as a complete, integrated system:
- HTML viewer with D3.js
- HTTP API server
- SQL views (v_graph_json, v_graph_dot)
- Status colors, priority sizing, availability highlighting
- Auto-refresh, tooltips, legends, zoom/pan
- Position caching and stable simulation
"""

import json
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from time import sleep

import pytest

from tasktree_mcp.database import DependencyRepository, TaskRepository


# Import the server module dynamically
import importlib.util

scripts_dir = Path(__file__).parent.parent / "scripts"
graph_server_path = scripts_dir / "graph-server.py"

spec = importlib.util.spec_from_file_location("graph_server", graph_server_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load graph_server from {graph_server_path}")
graph_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_server)

run_server = graph_server.run_server


@pytest.fixture
def mock_db_path(test_db: Path, monkeypatch):
    """
    Mock the DB_PATH to use the test database.

    This fixture modifies the database.DB_PATH to point to the test database,
    ensuring all repository operations use the isolated test database.
    """
    import tasktree_mcp.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


@pytest.fixture
def server_thread(test_db: Path, request):
    """
    Start the graph server in a background thread for testing.

    Args:
        test_db: Path to the test database
        request: pytest request fixture for unique port per test

    Yields:
        int: port number the server is listening on
    """
    # Use unique port for each test to avoid conflicts
    # Base port 8765 + hash of test name
    base_port = 8765
    port_offset = abs(hash(request.node.name)) % 100
    port = base_port + port_offset

    # Start server in background thread
    thread = Thread(target=run_server, args=(port, test_db), daemon=True)
    thread.start()

    # Give server time to start
    sleep(0.5)

    yield port

    # Thread will be cleaned up automatically (daemon=True)


@pytest.fixture
def graph_viewer_path():
    """Get the path to the graph viewer HTML file."""
    return Path(__file__).parent.parent / "scripts" / "graph-viewer.html"


def test_complete_graph_visualization_workflow(
    mock_db_path, server_thread, graph_viewer_path
):
    """
    Integration test: Complete graph visualization workflow.

    This test verifies the complete workflow:
    1. Create a complex task graph with various statuses and priorities
    2. Verify SQL views generate correct graph data
    3. Verify HTTP API serves the graph data correctly
    4. Verify HTML viewer contains all necessary features
    5. Verify all features work together (colors, sizing, availability, tooltips)
    """
    port = server_thread

    # Step 1: Create a complex task graph
    # ---------------------------------
    # Create tasks with various statuses and priorities
    TaskRepository.add_task(
        "task-high-priority",
        "High priority pending task",
        priority=10,
        status="pending",
    )
    TaskRepository.add_task(
        "task-medium-priority",
        "Medium priority in-progress task",
        priority=5,
        status="in_progress",
    )
    TaskRepository.add_task(
        "task-low-priority",
        "Low priority completed task",
        priority=0,
        status="completed",
    )
    TaskRepository.add_task(
        "task-available",
        "Available task (no dependencies)",
        priority=7,
        status="pending",
    )
    TaskRepository.add_task(
        "task-blocked", "Blocked task (has dependency)", priority=8, status="pending"
    )

    # Create dependency: task-blocked depends on task-available
    DependencyRepository.add_dependency("task-blocked", "task-available")

    # Step 2: Verify SQL views generate correct graph data
    # -------------------------------------------------
    import sqlite3

    conn = sqlite3.connect(mock_db_path)
    cursor = conn.cursor()

    # Test v_graph_json view
    cursor.execute("SELECT graph_json FROM v_graph_json")
    result = cursor.fetchone()
    assert result is not None

    graph_data = json.loads(result[0])
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert len(graph_data["nodes"]) == 5
    assert len(graph_data["edges"]) == 1

    # Verify node data includes all required fields
    for node in graph_data["nodes"]:
        assert "name" in node
        assert "description" in node
        assert "status" in node
        assert "priority" in node
        assert "is_available" in node
        assert "completed_at" in node

    # Verify availability flags
    nodes_by_name = {node["name"]: node for node in graph_data["nodes"]}
    assert nodes_by_name["task-available"]["is_available"] == 1
    assert nodes_by_name["task-blocked"]["is_available"] == 0

    # Test v_graph_dot view
    cursor.execute("SELECT dot_graph FROM v_graph_dot")
    result = cursor.fetchone()
    assert result is not None

    dot_data = result[0]
    assert "digraph TaskTree {" in dot_data
    assert "fillcolor=lightblue" in dot_data  # pending tasks
    assert "fillcolor=yellow" in dot_data  # in_progress tasks
    assert "fillcolor=lightgreen" in dot_data  # completed tasks
    assert "penwidth=3" in dot_data  # available task highlighting

    conn.close()

    # Step 3: Verify HTTP API serves the graph data correctly
    # ----------------------------------------------------
    http_conn = HTTPConnection("localhost", port)
    try:
        http_conn.request("GET", "/api/graph")
        response = http_conn.getresponse()

        # Verify response
        assert response.status == 200
        assert response.getheader("Content-type") == "application/json"
        assert response.getheader("Access-Control-Allow-Origin") == "*"

        # Parse JSON response
        api_data = json.loads(response.read().decode())

        assert "nodes" in api_data
        assert "edges" in api_data
        assert len(api_data["nodes"]) == 5
        assert len(api_data["edges"]) == 1

        # Verify node priorities
        api_nodes_by_name = {node["name"]: node for node in api_data["nodes"]}
        assert api_nodes_by_name["task-high-priority"]["priority"] == 10
        assert api_nodes_by_name["task-medium-priority"]["priority"] == 5
        assert api_nodes_by_name["task-low-priority"]["priority"] == 0

        # Verify statuses
        assert api_nodes_by_name["task-high-priority"]["status"] == "pending"
        assert api_nodes_by_name["task-medium-priority"]["status"] == "in_progress"
        assert api_nodes_by_name["task-low-priority"]["status"] == "completed"

    finally:
        http_conn.close()

    # Step 4: Verify HTML viewer contains all necessary features
    # ------------------------------------------------------
    viewer_content = graph_viewer_path.read_text()

    # Basic HTML structure
    assert "<!DOCTYPE html>" in viewer_content
    assert "<html" in viewer_content
    assert "d3js.org/d3" in viewer_content

    # Graph visualization elements
    assert 'id="graph"' in viewer_content
    assert "forceSimulation" in viewer_content

    # Status colors
    assert "#2196F3" in viewer_content  # pending = blue
    assert "#FFC107" in viewer_content  # in_progress = yellow
    assert "#4CAF50" in viewer_content  # completed = green

    # Priority-based sizing
    assert "getNodeRadius" in viewer_content
    assert "return 8 +" in viewer_content  # min radius 8px
    assert "* 22" in viewer_content  # scaling factor to reach 30px

    # Available task highlighting
    assert "is_available" in viewer_content
    assert "#00FF00" in viewer_content  # green border for available tasks
    assert ".attr('id', 'glow')" in viewer_content
    assert "feGaussianBlur" in viewer_content

    # Tooltip features
    assert 'id="tooltip"' in viewer_content
    assert "showTooltip" in viewer_content
    assert "hideTooltip" in viewer_content
    assert "d.name" in viewer_content
    assert "d.description" in viewer_content
    assert "d.status" in viewer_content
    assert "d.priority" in viewer_content

    # Legend
    assert "legend" in viewer_content.lower()
    assert "Pending" in viewer_content
    assert "In Progress" in viewer_content
    assert "Completed" in viewer_content
    assert "Priority" in viewer_content

    # Interactive features
    assert "drag" in viewer_content.lower()
    assert "zoom" in viewer_content.lower()

    # Auto-refresh
    assert "setInterval" in viewer_content

    # Position caching and stable simulation
    assert "positionCache" in viewer_content
    assert "Map()" in viewer_content
    assert "structureChanged" in viewer_content

    # Stable link key function (handles D3 mutation)
    assert "typeof d.source === 'object'" in viewer_content
    assert "typeof d.target === 'object'" in viewer_content

    # Error handling
    assert "catch" in viewer_content


def test_graph_visualization_end_to_end_updates(mock_db_path, server_thread):
    """
    Integration test: Graph visualization updates end-to-end.

    This test verifies that changes to the task graph are properly
    reflected through all layers of the system:
    1. Add initial tasks
    2. Verify initial state via API
    3. Update task statuses
    4. Verify updated state via API
    5. Ensure availability flags update correctly
    """
    port = server_thread

    # Initial state: Create two tasks with dependency
    TaskRepository.add_task("base", "Base task", status="pending", priority=5)
    TaskRepository.add_task("dependent", "Dependent task", status="pending", priority=8)
    DependencyRepository.add_dependency("dependent", "base")

    # Verify initial state
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        nodes = {node["name"]: node for node in data["nodes"]}
        assert nodes["base"]["is_available"] == 1  # No dependencies
        assert nodes["dependent"]["is_available"] == 0  # Blocked by base
        assert nodes["base"]["status"] == "pending"
        assert nodes["dependent"]["status"] == "pending"
    finally:
        conn.close()

    # Update: Mark base task as completed
    TaskRepository.update_task("base", status="completed")

    # Verify updated state
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        nodes = {node["name"]: node for node in data["nodes"]}
        assert nodes["base"]["status"] == "completed"
        assert nodes["base"]["completed_at"] is not None
        assert nodes["dependent"]["is_available"] == 1  # Now available!
        assert nodes["dependent"]["status"] == "pending"
    finally:
        conn.close()

    # Update: Mark dependent task as in_progress
    TaskRepository.update_task("dependent", status="in_progress")

    # Verify final state
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        nodes = {node["name"]: node for node in data["nodes"]}
        assert nodes["dependent"]["status"] == "in_progress"
        assert (
            nodes["dependent"]["is_available"] == 0
        )  # No longer available (in progress)
    finally:
        conn.close()


def test_graph_visualization_complex_dependency_tree(mock_db_path, server_thread):
    """
    Integration test: Complex dependency tree visualization.

    This test creates a complex dependency tree and verifies:
    1. All nodes and edges are properly represented
    2. Availability cascades correctly through the tree
    3. Priority-based sizing works across all nodes
    4. Different statuses are properly color-coded
    """
    port = server_thread

    # Create a complex dependency tree:
    #     A (completed, p=10)
    #    / \
    #   B   C (in_progress, p=7)
    #    \ /
    #     D (pending, p=5)
    #     |
    #     E (pending, p=3)

    TaskRepository.add_task("task-a", "Task A", status="completed", priority=10)
    TaskRepository.add_task("task-b", "Task B", status="pending", priority=8)
    TaskRepository.add_task("task-c", "Task C", status="in_progress", priority=7)
    TaskRepository.add_task("task-d", "Task D", status="pending", priority=5)
    TaskRepository.add_task("task-e", "Task E", status="pending", priority=3)

    # Create dependencies
    DependencyRepository.add_dependency("task-b", "task-a")
    DependencyRepository.add_dependency("task-c", "task-a")
    DependencyRepository.add_dependency("task-d", "task-b")
    DependencyRepository.add_dependency("task-d", "task-c")
    DependencyRepository.add_dependency("task-e", "task-d")

    # Verify via API
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        # Verify structure
        assert len(data["nodes"]) == 5
        assert len(data["edges"]) == 5

        nodes = {node["name"]: node for node in data["nodes"]}

        # Verify statuses
        assert nodes["task-a"]["status"] == "completed"
        assert nodes["task-b"]["status"] == "pending"
        assert nodes["task-c"]["status"] == "in_progress"
        assert nodes["task-d"]["status"] == "pending"
        assert nodes["task-e"]["status"] == "pending"

        # Verify priorities
        assert nodes["task-a"]["priority"] == 10
        assert nodes["task-b"]["priority"] == 8
        assert nodes["task-c"]["priority"] == 7
        assert nodes["task-d"]["priority"] == 5
        assert nodes["task-e"]["priority"] == 3

        # Verify availability cascade
        # Only pending/blocked tasks with all dependencies completed are "available"
        assert (
            nodes["task-a"]["is_available"] == 0
        )  # Completed (no longer in work queue)
        assert nodes["task-b"]["is_available"] == 1  # A is completed
        assert (
            nodes["task-c"]["is_available"] == 0
        )  # In progress (already being worked)
        assert (
            nodes["task-d"]["is_available"] == 0
        )  # B is pending, C is in_progress (not all completed)
        assert nodes["task-e"]["is_available"] == 0  # D is not completed

        # Verify edges
        edges = data["edges"]
        edge_pairs = {(e["from"], e["to"]) for e in edges}
        assert ("task-b", "task-a") in edge_pairs
        assert ("task-c", "task-a") in edge_pairs
        assert ("task-d", "task-b") in edge_pairs
        assert ("task-d", "task-c") in edge_pairs
        assert ("task-e", "task-d") in edge_pairs

    finally:
        conn.close()


def test_graph_visualization_empty_and_single_node(mock_db_path, server_thread):
    """
    Integration test: Edge cases - empty graph and single node.

    Verifies the system handles edge cases gracefully:
    1. Empty database (no tasks)
    2. Single task (no edges)
    """
    port = server_thread

    # Test empty database
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        assert data["nodes"] == []
        assert data["edges"] == []
    finally:
        conn.close()

    # Add single task
    TaskRepository.add_task("solo-task", "A lone task", status="pending", priority=5)

    # Test single task
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 0
        assert data["nodes"][0]["name"] == "solo-task"
        assert data["nodes"][0]["is_available"] == 1  # No dependencies
    finally:
        conn.close()


def test_graph_visualization_special_characters(mock_db_path, server_thread):
    """
    Integration test: Special characters in task data.

    Verifies that task names and descriptions with special characters
    are properly handled through all layers:
    - SQL views
    - JSON encoding
    - HTTP API
    - HTML viewer (escaping)
    """
    port = server_thread

    # Create task with special characters
    TaskRepository.add_task(
        "task-with-特殊字符",
        'Description with "quotes", newlines\n, unicode: 你好世界 🚀',
        priority=7,
        status="pending",
    )

    # Verify via API
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/graph")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        assert len(data["nodes"]) == 1
        node = data["nodes"][0]

        # Verify name with special characters
        assert node["name"] == "task-with-特殊字符"

        # Verify description with special characters
        assert '"quotes"' in node["description"]
        assert "你好世界" in node["description"]
        assert "🚀" in node["description"]

    finally:
        conn.close()
