"""
Tests for status-specific glow effects and node styling.
"""

from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM
from time import sleep

import pytest
import tasktree.graph.server as graph_server

run_server = graph_server.run_server


@pytest.fixture
def server_thread(test_db: Path):
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        port = sock.getsockname()[1]

    thread = Thread(target=run_server, args=(port, test_db), daemon=True)
    thread.start()
    sleep(0.1)
    yield port


def test_glow_filters_defined_in_index_html(server_thread):
    """Test that the status-specific glow filters are defined in index.html."""
    port = server_thread
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/")
        response = conn.getresponse()
        assert response.status == 200
        html = response.read().decode()

        # Check for filter definitions
        assert 'id="glow-available"' in html
        assert 'id="glow-in-progress"' in html
        assert 'id="glow-status"' in html

        # Check for specific colors
        assert 'flood-color="#2196F3"' in html  # Blue for available
        assert 'flood-color="#FFFF00"' in html  # Bright yellow for in-progress
    finally:
        conn.close()


def test_node_stroke_removed_in_graph_js(server_thread):
    """Test that node strokes are removed in graph.js."""
    port = server_thread
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/graph.js")
        response = conn.getresponse()
        assert response.status == 200
        js = response.read().decode()

        # Check that getNodeStroke returns 'none'
        assert "function getNodeStroke(d) {\n    return 'none';\n}" in js
        # Check that getNodeStrokeWidth returns 0
        assert "function getNodeStrokeWidth(d) {\n    return 0;\n}" in js
    finally:
        conn.close()


def test_dynamic_filter_application_in_graph_js(server_thread):
    """Test that filters are applied dynamically based on status."""
    port = server_thread
    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/graph.js")
        response = conn.getresponse()
        assert response.status == 200
        js = response.read().decode()

        # Check for dynamic filter logic
        assert "if (d.is_available) return 'url(#glow-available)';" in js
        assert "if (d.status === 'in_progress') return 'url(#glow-in-progress)';" in js
        assert "if (d.status === 'pending') return null;" in js
        assert "return 'url(#glow-status)';" in js
    finally:
        conn.close()
