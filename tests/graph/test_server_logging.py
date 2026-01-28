from tasktree.graph.server import GraphAPIHandler


def test_log_message_is_silenced(capsys):
    """Test that log_message does not print anything to stdout/stderr."""
    # Let's create a dummy instance
    handler = GraphAPIHandler.__new__(GraphAPIHandler)
    handler.log_message("test format %s", "arg")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_server_startup_messages_still_print(capsys, tmp_path):
    """Test that run_server still prints startup messages."""
    from tasktree.graph.server import run_server
    import socket

    # Create a dummy database file
    db_path = tmp_path / "test.db"
    db_path.touch()

    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]

    from unittest.mock import patch, MagicMock

    with patch("tasktree.graph.server.HTTPServer") as mock_server_class:
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        run_server(port, db_path)

        captured = capsys.readouterr()
        assert "TaskTree Graph API Server" in captured.out
        assert f"Listening on: http://localhost:{port}" in captured.out
        assert "Press Ctrl+C to stop" in captured.out
