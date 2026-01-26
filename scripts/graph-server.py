#!/usr/bin/env python3
"""
TaskTree Graph API Server

A simple HTTP server that provides an API endpoint to retrieve the task dependency
graph as JSON. Uses Python's built-in http.server module.

Usage:
    python scripts/graph-server.py [--port PORT] [--db DB_PATH]

Default:
    Port: 8000
    Database: .tasktree/tasktree.db
"""

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


class GraphAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the graph API."""

    db_path: Path
    assets_dir: Path = (Path(__file__).parent / "graph-server").resolve()

    mime_types = {
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".ico": "image/x-icon",
        ".jpeg": "image/jpeg",
        ".jpg": "image/jpeg",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".txt": "text/plain; charset=utf-8",
    }

    def do_GET(self) -> None:
        """Handle GET requests."""
        request_path = urlparse(self.path).path

        if request_path == "/api/graph":
            self._handle_graph_request()
        elif request_path == "/api/tasks":
            self._handle_tasks_request()
        elif request_path == "/":
            self._handle_root_request()
        elif request_path.startswith("/static/"):
            self._handle_static_request(request_path)
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

    def _handle_tasks_request(self) -> None:
        """Handle /api/tasks endpoint request."""
        try:
            tasks_data = self._get_tasks_json()
            self._send_json_response(200, tasks_data)
        except sqlite3.OperationalError as e:
            self._send_error(500, f"Database error: {e}")
        except Exception as e:
            self._send_error(500, f"Internal server error: {e}")

    def _handle_root_request(self) -> None:
        """Handle root endpoint with task list panel and graph visualization."""
        # Get task data for the panel
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all distinct feature names for the dropdown
        cursor.execute("""
            SELECT DISTINCT feature_name 
            FROM tasks 
            ORDER BY feature_name
        """)
        features = [row[0] for row in cursor.fetchall()]

        # Get all tasks sorted by status, priority (descending), then name
        cursor.execute("""
            SELECT name, description, status, priority, created_at, started_at, completed_at, details, feature_name
            FROM tasks
            ORDER BY CASE status 
                         WHEN 'blocked' THEN 1 
                         WHEN 'in_progress' THEN 2 
                         WHEN 'pending' THEN 3 
                         WHEN 'completed' THEN 4 
                     END,
                     priority DESC,
                     name
        """)
        tasks = cursor.fetchall()

        conn.close()

        # Build task list HTML
        task_items_html = ""
        for task in tasks:
            (
                name,
                description,
                status,
                priority,
                created_at,
                started_at,
                completed_at,
                details,
                feature_name,
            ) = task

            # Status color coding
            status_colors = {
                "pending": "#2196F3",
                "in_progress": "#FFC107",
                "completed": "#4CAF50",
                "blocked": "#F44336",
            }
            status_color = status_colors.get(status, "#999")

            # Format details section with conditional rendering
            details_html = f"""
                <div class="task-details-row"><span class="task-details-label">Status:</span> {status}</div>
                <div class="task-details-row"><span class="task-details-label">Priority:</span> {priority}</div>
                <div class="task-details-row">
                    <span class="task-details-label">Description:</span>
                    <div class="task-details-value">{description if description else "None"}</div>
                </div>"""

            if details:
                details_html += f"""
                <div class="task-details-row">
                    <span class="task-details-label">Details:</span>
                    <div class="task-details-value">{details}</div>
                </div>"""

            details_html += f"""
                <div class="task-details-row"><span class="task-details-label">Created:</span> {created_at if created_at else "None"}</div>"""

            if started_at:
                details_html += f"""
                <div class="task-details-row"><span class="task-details-label">Started:</span> {started_at}</div>"""

            if completed_at:
                details_html += f"""
                <div class="task-details-row"><span class="task-details-label">Completed:</span> {completed_at}</div>"""

            task_items_html += f"""
            <div class="task-item" data-status="{status}" data-feature="{feature_name}">
                <div class="task-header" onclick="toggleTaskDetails(this)">
                    <span class="task-status-dot" style="background: {status_color};"></span>
                    <span class="task-name" title="{name}">{name}</span>
                    <span class="task-expand-icon">▶</span>
                </div>
                <div class="task-details" style="display: none;">
                    {details_html}
                </div>
            </div>"""

        feature_options = "".join(
            [f'<option value="{feat}">{feat}</option>' for feat in features]
        )
        task_items_rendered = (
            task_items_html
            if task_items_html
            else '<div style="padding: 12px; color: #999; font-size: 12px;">'
            "No tasks available"
            "</div>"
        )

        template_path = self.assets_dir / "index.html"
        template_html = template_path.read_text()
        html = template_html.replace("{{FEATURE_OPTIONS}}", feature_options).replace(
            "{{TASK_ITEMS}}", task_items_rendered
        )
        self._send_html_response(200, html)

    def _handle_static_request(self, request_path: str) -> None:
        """Serve static assets under /static."""
        relative_path = request_path.removeprefix("/static/")

        if not relative_path or relative_path.endswith("/"):
            self._send_error(404, "Not Found")
            return

        safe_path = Path(unquote(relative_path))
        asset_path = (self.assets_dir / safe_path).resolve()

        if not asset_path.is_file() or not asset_path.is_relative_to(self.assets_dir):
            self._send_error(404, "Not Found")
            return

        content_type = self.mime_types.get(
            asset_path.suffix.lower(), "application/octet-stream"
        )

        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(asset_path.read_bytes())

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

    def _get_tasks_json(self) -> dict:
        """
        Fetch all tasks from the database.

        Returns:
            Dictionary containing list of tasks with their details

        Raises:
            sqlite3.OperationalError: If database doesn't exist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT name, description, status, priority, created_at, started_at, completed_at, details, feature_name
                FROM tasks
                ORDER BY CASE status 
                             WHEN 'blocked' THEN 1 
                             WHEN 'in_progress' THEN 2 
                             WHEN 'pending' THEN 3 
                             WHEN 'completed' THEN 4 
                         END,
                         priority DESC,
                         name
            """)
            rows = cursor.fetchall()

            tasks = []
            for row in rows:
                tasks.append(
                    {
                        "name": row[0],
                        "description": row[1],
                        "status": row[2],
                        "priority": row[3],
                        "created_at": row[4],
                        "started_at": row[5],
                        "completed_at": row[6],
                        "details": row[7],
                        "feature_name": row[8],
                    }
                )

            return {"tasks": tasks}
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
