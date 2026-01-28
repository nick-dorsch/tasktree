import socket
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from time import sleep

import pytest

import tasktree.graph.server as graph_server
from tasktree.core.database import TaskRepository, FeatureRepository

run_server = graph_server.run_server


@pytest.fixture
def mock_db(test_db: Path, monkeypatch):
    """Mock the DB_PATH to use the test database."""
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


def test_graph_js_includes_progress_display_logic(server_thread):
    """Test that graph.js includes the code to display feature progress."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/graph.js")
        response = conn.getresponse()
        assert response.status == 200
        js_content = response.read().decode()

        # Check for progress calculation logic
        assert (
            "const completedTasks = featureTasks.filter(t => t.status === 'completed').length;"
            in js_content
        )
        assert "const totalTasks = featureTasks.length;" in js_content
        assert (
            "const allCompleted = completedTasks === totalTasks && totalTasks > 0;"
            in js_content
        )
        assert (
            "const countStyle = allCompleted ? ' style=\"color: #22d3ee; font-weight: bold;\"' : '';"
            in js_content
        )

        # Check for the updated HTML string
        assert "completedTasks + ' / ' + totalTasks" in js_content
        assert "feature-count\"' + countStyle + '>'" in js_content
    finally:
        conn.close()


def test_server_renders_progress_counts(mock_db, server_thread):
    """Test that the server renders 'completed / total' in the initial HTML."""
    port = server_thread

    # Add a feature and some tasks
    FeatureRepository.add_feature("test-feat", "Desc", "Spec")
    TaskRepository.add_task(
        "task-1", "Task 1", specification="Spec 1", feature_name="test-feat"
    )
    TaskRepository.add_task(
        "task-2", "Task 2", specification="Spec 2", feature_name="test-feat"
    )
    TaskRepository.complete_task("task-1")

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()
        html = response.read().decode()

        # Check for the progress count format
        assert '<span class="feature-count">1 / 2</span>' in html

        # Complete all tasks and check for green color
        TaskRepository.complete_task("task-2")

        conn.request("GET", "/")
        response = conn.getresponse()
        html = response.read().decode()

        assert (
            '<span class="feature-count" style="color: #22d3ee; font-weight: bold;">2 / 2</span>'
            in html
        )
    finally:
        conn.close()
