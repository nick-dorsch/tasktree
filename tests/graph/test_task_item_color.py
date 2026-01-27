import socket
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from time import sleep
import hashlib

import pytest

import tasktree.graph.server as graph_server
from tasktree.core.database import TaskRepository

GraphAPIHandler = graph_server.GraphAPIHandler
run_server = graph_server.run_server


@pytest.fixture
def mock_db_path(test_db: Path, monkeypatch):
    """
    Mock the DB_PATH to use the test database.
    """
    import tasktree.core.database as db_module

    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    return test_db


@pytest.fixture
def server_thread(test_db: Path):
    """
    Start the graph server in a background thread for testing.
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


def test_task_item_includes_feature_color_background(mock_db_path, server_thread):
    """Test that task-item has a background-color style with the feature color."""
    port = server_thread
    TaskRepository.add_task("task-1", "Task 1", specification="Spec")

    colors = GraphAPIHandler.FEATURE_COLORS
    hash_val = int(hashlib.md5("misc".encode()).hexdigest(), 16)
    expected_color = colors[hash_val % len(colors)]

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()
        html = response.read().decode()

        # Check for task-item style with the color and 10% opacity (1A)
        assert 'class="task-item"' in html
        assert f'style="background-color: {expected_color}1A;"' in html
    finally:
        conn.close()


def test_graph_js_updates_task_item_with_color(server_thread):
    """Test that graph.js includes the code to set task-item background color."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/graph.js")
        response = conn.getresponse()
        assert response.status == 200
        js_content = response.read().decode()

        # Check for the line that sets the task-item background color
        assert "task-item" in js_content
        assert "background-color: ' + featureColor + '1A" in js_content
    finally:
        conn.close()
