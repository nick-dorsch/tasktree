import json
import socket
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from time import sleep

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


def test_api_tasks_includes_feature_color(mock_db_path, server_thread):
    """Test /api/tasks includes feature_color."""
    port = server_thread
    TaskRepository.add_task("task-1", "Task 1", specification="Spec")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/api/tasks")
        response = conn.getresponse()
        data = json.loads(response.read().decode())

        task = data["tasks"][0]
        assert "feature_color" in task
        assert task["feature_color"].startswith("#")
    finally:
        conn.close()


def test_root_html_includes_feature_color_style(mock_db_path, server_thread):
    """Test root HTML includes feature color styles."""
    port = server_thread
    TaskRepository.add_task("task-1", "Task 1", specification="Spec")

    # We need to know what color 'misc' gets
    # Since hashing is deterministic, we can calculate it
    import hashlib

    colors = GraphAPIHandler.FEATURE_COLORS
    hash_val = int(hashlib.md5("misc".encode()).hexdigest(), 16)
    expected_color = colors[hash_val % len(colors)]

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()
        html = response.read().decode()

        # Check for inline style with the color
        # We look for the feature header style
        assert f"border-left: 4px solid {expected_color}" in html
        assert f"background-color: {expected_color}1A" in html
    finally:
        conn.close()
