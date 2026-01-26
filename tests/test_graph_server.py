"""
Tests for the graph server (scripts/graph-server.py).

Tests the HTTP API endpoints for retrieving task dependency graphs.
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
graph_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_server)

GraphAPIHandler = graph_server.GraphAPIHandler
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
    assert "task-1" in node_names
    assert "task-2" in node_names


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
    assert edge["from"] == "dependent-task"
    assert edge["to"] == "base-task"


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
    assert "name" in node
    assert "description" in node
    assert "status" in node
    assert "priority" in node
    assert "completed_at" in node
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
    """Test that the root endpoint returns HTML documentation."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()

        assert response.status == 200
        assert response.getheader("Content-type") == "text/html"

        html = response.read().decode()
        assert "TaskTree Graph API" in html
        assert "/api/graph" in html
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
