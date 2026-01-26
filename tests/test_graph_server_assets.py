"""
Tests for graph server static asset placeholders.
"""

import importlib.util
import socket
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread
from time import sleep

import pytest


scripts_dir = Path(__file__).parent.parent / "scripts"
graph_server_path = scripts_dir / "graph-server.py"

spec = importlib.util.spec_from_file_location("graph_server", graph_server_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load graph-server module")
graph_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_server)

run_server = graph_server.run_server


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

    thread = Thread(target=run_server, args=(port, test_db), daemon=True)
    thread.start()

    sleep(0.5)

    yield port


def test_graph_server_assets_directory_exists() -> None:
    """Ensure the graph server assets directory exists."""
    assets_dir = Path(__file__).parent.parent / "scripts" / "graph-server"
    assert assets_dir.exists()
    assert assets_dir.is_dir()


def test_graph_server_assets_files_exist() -> None:
    """Ensure placeholder asset files are present."""
    assets_dir = Path(__file__).parent.parent / "scripts" / "graph-server"
    index_file = assets_dir / "index.html"
    graph_js_file = assets_dir / "graph.js"

    assert index_file.exists()
    assert index_file.is_file()
    assert graph_js_file.exists()
    assert graph_js_file.is_file()


def test_graph_server_assets_placeholders_have_expected_content() -> None:
    """Ensure placeholder files have expected minimal content."""
    assets_dir = Path(__file__).parent.parent / "scripts" / "graph-server"
    index_content = (assets_dir / "index.html").read_text()
    graph_js_content = (assets_dir / "graph.js").read_text()

    assert "<!DOCTYPE html>" in index_content
    assert "graph.js" in index_content
    assert "tasktreeGraphServerAssetsLoaded" in graph_js_content


def test_graph_server_handler_has_no_inline_html() -> None:
    """Ensure handler does not embed inline HTML templates."""
    server_file = Path(__file__).parent.parent / "scripts" / "graph-server.py"
    server_content = server_file.read_text()

    assert "<!DOCTYPE html>" not in server_content
    assert "<style>" not in server_content
    assert "<body>" not in server_content


def test_graph_server_index_template_has_placeholders() -> None:
    """Ensure index template contains placeholder tokens."""
    assets_dir = Path(__file__).parent.parent / "scripts" / "graph-server"
    index_content = (assets_dir / "index.html").read_text()

    assert "{{FEATURE_OPTIONS}}" in index_content
    assert "{{TASK_ITEMS}}" in index_content


def test_static_asset_serves_graph_js(server_thread):
    """Ensure /static/graph.js is served with JS mime type."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/graph.js")
        response = conn.getresponse()

        assert response.status == 200
        assert (
            response.getheader("Content-type")
            == "application/javascript; charset=utf-8"
        )

        body = response.read().decode()
        assert "tasktreeGraphServerAssetsLoaded" in body
    finally:
        conn.close()


def test_static_asset_serves_index_html(server_thread):
    """Ensure /static/index.html is served with HTML mime type."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/index.html")
        response = conn.getresponse()

        assert response.status == 200
        assert response.getheader("Content-type") == "text/html; charset=utf-8"

        body = response.read().decode()
        assert "<!DOCTYPE html>" in body
    finally:
        conn.close()


def test_static_asset_missing_returns_404(server_thread):
    """Ensure missing static assets return 404 JSON error."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/missing-file.js")
        response = conn.getresponse()

        assert response.status == 404
        assert response.getheader("Content-type") == "application/json"
    finally:
        conn.close()


def test_static_asset_path_traversal_blocked(server_thread):
    """Ensure path traversal does not escape assets directory."""
    port = server_thread

    conn = HTTPConnection("localhost", port)
    try:
        conn.request("GET", "/static/../graph-server.py")
        response = conn.getresponse()

        assert response.status == 404
    finally:
        conn.close()
