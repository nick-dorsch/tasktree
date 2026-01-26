#!/usr/bin/env python3
"""
TaskTree Graph API Server

A simple HTTP server that provides an API endpoint to retrieve the task dependency
graph as JSON. Uses Python's built-in http.server module.

Usage:
    python scripts/graph-server.py [--port PORT] [--db DB_PATH]

Default:
    Port: 8000
    Database: data/tasktree.db
"""

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class GraphAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the graph API."""

    db_path: Path

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/api/graph":
            self._handle_graph_request()
        elif self.path == "/":
            self._handle_root_request()
        else:
            self._send_error(404, "Not Found")

    def _handle_graph_request(self) -> None:
        """Handle /api/graph endpoint request."""
        try:
            graph_data = self._get_graph_json()
            self._send_json_response(200, graph_data)
        except sqlite3.OperationalError as e:
            self._send_error(500, f"Database error: {e}")
        except Exception as e:
            self._send_error(500, f"Internal server error: {e}")

    def _handle_root_request(self) -> None:
        """Handle root endpoint with simple HTML documentation."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>TaskTree Graph API</title>
    <style>
        body { font-family: monospace; max-width: 800px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #333; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
        pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>TaskTree Graph API</h1>
    <p>A simple API server for retrieving task dependency graphs.</p>
    
    <h2>Endpoint</h2>
    <ul>
        <li><code>GET /api/graph</code> - Retrieve the task dependency graph as JSON</li>
    </ul>
    
    <h2>Response Format</h2>
    <pre>{
  "nodes": [
    {
      "name": "task-name",
      "description": "task description",
      "status": "pending|in_progress|completed",
      "priority": 0-10,
      "completed_at": "timestamp or null",
      "is_available": 0|1
    }
  ],
  "edges": [
    {
      "from": "dependent-task",
      "to": "dependency-task"
    }
  ]
}</pre>
    
    <h2>Try It</h2>
    <p><a href="/api/graph">View current graph</a></p>
</body>
</html>"""
        self._send_html_response(200, html)

    def _get_graph_json(self) -> dict:
        """
        Fetch the graph JSON from the v_graph_json view.

        Returns:
            Dictionary containing nodes and edges

        Raises:
            sqlite3.OperationalError: If database or view doesn't exist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT graph_json FROM v_graph_json")
            result = cursor.fetchone()

            if result and result[0]:
                return json.loads(result[0])
            return {"nodes": [], "edges": []}
        finally:
            conn.close()

    def _send_json_response(self, status_code: int, data: dict) -> None:
        """Send JSON response with appropriate headers."""
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _send_html_response(self, status_code: int, html: str) -> None:
        """Send HTML response with appropriate headers."""
        self.send_response(status_code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_error(self, status_code: int, message: str) -> None:
        """Send error response as JSON."""
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        error_data = {"error": message, "status": status_code}
        self.wfile.write(json.dumps(error_data, indent=2).encode())

    def log_message(self, format: str, *args) -> None:
        """Override to provide cleaner log messages."""
        print(f"{self.address_string()} - {format % args}")


def run_server(port: int, db_path: Path) -> None:
    """
    Start the HTTP server.

    Args:
        port: Port number to listen on
        db_path: Path to the SQLite database file
    """
    # Validate database exists
    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}")
        print("Run 'task init-db' to create the database.")
        return

    # Set the db_path as a class variable so the handler can access it
    GraphAPIHandler.db_path = db_path

    server_address = ("", port)
    httpd = HTTPServer(server_address, GraphAPIHandler)

    print("TaskTree Graph API Server")
    print(f"Database: {db_path}")
    print(f"Listening on: http://localhost:{port}")
    print(f"Graph endpoint: http://localhost:{port}/api/graph")
    print("Press Ctrl+C to stop")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


def main() -> None:
    """Parse arguments and start the server."""
    parser = argparse.ArgumentParser(
        description="TaskTree Graph API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/tasktree.db"),
        help="Path to SQLite database (default: data/tasktree.db)",
    )

    args = parser.parse_args()

    run_server(args.port, args.db)


if __name__ == "__main__":
    main()
