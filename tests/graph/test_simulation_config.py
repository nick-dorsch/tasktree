"""
Tests for the D3 force simulation configuration in graph.js.
"""

from http.client import HTTPConnection
import socket
from pathlib import Path
from threading import Thread
from time import sleep

import pytest
import tasktree.graph.server as graph_server

run_server = graph_server.run_server


@pytest.fixture
def server_thread(test_db: Path):
    """Start the graph server in a background thread for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        port = sock.getsockname()[1]

    thread = Thread(target=run_server, args=(port, test_db), daemon=True)
    thread.start()
    sleep(0.1)
    yield port


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


def test_simulation_config_replaces_center_with_xy(server_thread):
    """Test that graph.js uses forceX/forceY instead of forceCenter."""
    port = server_thread
    graph_js = fetch_graph_js(port)

    # Verify forceCenter is removed from simulation initialization
    # We check that it's not in the simulation setup block
    assert ".force('center', d3.forceCenter" not in graph_js

    # Verify forceX and forceY are added
    assert ".force('x', d3.forceX(WIDTH / 2).strength(0.05))" in graph_js
    assert ".force('y', d3.forceY(HEIGHT / 2).strength(0.05))" in graph_js

    # Verify tuned strengths
    assert ".force('charge', d3.forceManyBody().strength(-30))" in graph_js
    assert ".force('link', d3.forceLink().id(d => d.id).distance(50))" in graph_js


def test_resize_handler_updates_xy_forces(server_thread):
    """Test that the resize handler updates forceX and forceY."""
    port = server_thread
    graph_js = fetch_graph_js(port)

    assert "simulation.force('x', d3.forceX(newWidth / 2).strength(0.05))" in graph_js
    assert "simulation.force('y', d3.forceY(newHeight / 2).strength(0.05))" in graph_js
    assert "simulation.force('center'" not in graph_js


def test_resize_handler_recalculates_global_dimensions(server_thread):
    """Test that the resize handler recalculates global WIDTH and HEIGHT."""
    port = server_thread
    graph_js = fetch_graph_js(port)

    # Verify global WIDTH/HEIGHT are now 'let' instead of 'const'
    assert "let WIDTH = window.innerWidth;" in graph_js
    assert "let HEIGHT = window.innerHeight;" in graph_js

    # Verify they are updated in the resize handler
    assert "WIDTH = window.innerWidth;" in graph_js
    assert "HEIGHT = window.innerHeight;" in graph_js
