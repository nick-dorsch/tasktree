"""
Tests for the drag behavior in graph.js.
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


def test_drag_behavior_implementation(server_thread):
    """Test that graph.js implements the drag-to-reheat behavior."""
    port = server_thread
    graph_js = fetch_graph_js(port)

    # Verify dragstarted implementation
    assert "function dragstarted(event, d) {" in graph_js
    assert "if (!event.active) simulation.alphaTarget(0.3).restart();" in graph_js
    assert "d.fx = d.x;" in graph_js
    assert "d.fy = d.y;" in graph_js

    # Verify dragged implementation
    assert "function dragged(event, d) {" in graph_js
    assert "d.fx = event.x;" in graph_js
    assert "d.fy = event.y;" in graph_js

    # Verify dragended implementation
    assert "function dragended(event, d) {" in graph_js
    assert "if (!event.active) simulation.alphaTarget(0);" in graph_js
    assert "d.fx = null;" in graph_js
    assert "d.fy = null;" in graph_js
