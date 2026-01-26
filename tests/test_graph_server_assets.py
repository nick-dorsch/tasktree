"""
Tests for graph server static asset placeholders.
"""

from pathlib import Path


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
