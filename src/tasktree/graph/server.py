#!/usr/bin/env python3
"""
TaskTree Graph API Server

A simple HTTP server that provides an API endpoint to retrieve the task dependency
graph as JSON. Uses Python's built-in http.server module.

Usage:
    python src/tasktree/graph/server.py [--port PORT] [--db DB_PATH]

Default:
    Port: 8000
    Database: .tasktree/tasktree.db
"""

import argparse
import hashlib
import json
from importlib.resources import files
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


class GraphAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the graph API."""

    db_path: Path
    assets_dir = files("tasktree.graph.assets.graph_assets")

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

    FEATURE_COLORS = [
        "#FF6B6B",  # Coral Red
        "#4ECDC4",  # Turquoise
        "#45B7D1",  # Sky Blue
        "#96CEB4",  # Sage Green
        "#FECA57",  # Golden Yellow
        "#B983FF",  # Lavender
        "#FD79A8",  # Pink
        "#A29BFE",  # Periwinkle
        "#6C5CE7",  # Purple
        "#00B894",  # Emerald
    ]

    def _get_feature_color(self, feature_name: str) -> str:
        """Get a consistent color for a feature name."""
        hash_val = int(hashlib.md5(feature_name.encode()).hexdigest(), 16)
        return self.FEATURE_COLORS[hash_val % len(self.FEATURE_COLORS)]

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

        # Get all tasks sorted by status, priority (descending), then name
        cursor.execute("""
            SELECT
                t.name,
                t.description,
                t.status,
                t.priority,
                t.created_at,
                t.started_at,
                t.completed_at,
                t.specification,
                f.name AS feature_name,
                f.description AS feature_description,
                f.created_at AS feature_created_at
            FROM tasks t
            JOIN features f ON t.feature_id = f.id
            ORDER BY CASE t.status
                         WHEN 'blocked' THEN 1
                         WHEN 'in_progress' THEN 2
                         WHEN 'pending' THEN 3
                         WHEN 'completed' THEN 4
                     END,
                     t.priority DESC,
                     t.name
        """)
        tasks = cursor.fetchall()

        # Get feature created_at info for sorting
        cursor.execute("""
            SELECT name, created_at FROM features ORDER BY created_at DESC
        """)
        features_by_created = cursor.fetchall()
        feature_order = {name: idx for idx, (name, _) in enumerate(features_by_created)}

        conn.close()

        # Build task list HTML grouped by feature
        tasks_by_feature: dict[str, list[tuple]] = {}
        # Store feature info for each feature
        feature_info = {}

        for task in tasks:
            feature_name = task[-3]  # feature_name is now third to last
            feature_description = task[-2]  # feature_description is second to last
            feature_created_at = task[-1]  # feature_created_at is last

            if feature_name not in feature_info:
                feature_info[feature_name] = {
                    "description": feature_description,
                    "created_at": feature_created_at,
                }

            tasks_by_feature.setdefault(feature_name, []).append(task)

        task_items_html = ""
        status_colors = {
            "pending": "#2196F3",
            "in_progress": "#FFC107",
            "completed": "#4CAF50",
            "blocked": "#F44336",
        }

        for feature_name in sorted(
            tasks_by_feature.keys(), key=lambda x: feature_order.get(x, 999)
        ):
            feature_tasks = tasks_by_feature[feature_name]
            completed_tasks = len([t for t in feature_tasks if t[2] == "completed"])
            total_tasks = len(feature_tasks)
            all_completed = completed_tasks == total_tasks and total_tasks > 0
            count_style = (
                ' style="color: #4CAF50; font-weight: bold;"' if all_completed else ""
            )

            feature_tasks_html = ""
            feature_color = self._get_feature_color(feature_name)
            for task in feature_tasks:
                (
                    name,
                    description,
                    status,
                    priority,
                    created_at,
                    started_at,
                    completed_at,
                    specification,
                    _feature_name,
                    _feature_description,
                    _feature_created_at,
                ) = task

                status_color = status_colors.get(status, "#999")

                details_html = f"""
                    <div class="task-details-row"><span class="task-details-label">Status:</span> {status}</div>
                    <div class="task-details-row"><span class="task-details-label">Priority:</span> {priority}</div>
                    <div class="task-details-row">
                        <span class="task-details-label">Description:</span>
                        <div class="task-details-value">{description if description else "None"}</div>
                    </div>"""

                if specification and specification != description:
                    details_html += f"""
                    <div class="task-details-row">
                        <span class="task-details-label">Details:</span>
                        <div class="task-details-value">{specification}</div>
                    </div>"""

                details_html += f"""
                    <div class="task-details-row"><span class="task-details-label">Created:</span> {created_at if created_at else "None"}</div>"""

                if started_at:
                    details_html += f"""
                    <div class="task-details-row"><span class="task-details-label">Started:</span> {started_at}</div>"""

                if completed_at:
                    details_html += f"""
                    <div class="task-details-row"><span class="task-details-label">Completed:</span> {completed_at}</div>"""

                feature_tasks_html += f"""
                <div class="task-item" data-status="{status}" data-feature="{feature_name}" data-task-name="{name}" style="background-color: {feature_color}1A;">
                    <div class="task-header" onclick="toggleTaskDetails(this)">
                        <span class="task-status-dot" style="background: {status_color};"></span>
                        <span class="task-name" title="{name}">{name}</span>
                        <span class="task-expand-icon">▶</span>
                    </div>
                    <div class="task-details" style="display: none;">
                        {details_html}
                    </div>
                </div>"""

            feature_info_detail = feature_info[feature_name]
            task_items_html += f"""
            <div class="feature-group" data-feature="{feature_name}">
                <div class="feature-header" onclick="toggleFeatureTasks(this)" style="border-left: 4px solid {feature_color}; background-color: {feature_color}1A;">
                    <div class="feature-main-info">
                        <span class="feature-chevron">▶</span>
                        <span class="feature-name" title="{feature_name}">{feature_name}</span>
                        <span class="feature-count"{count_style}>{completed_tasks} / {total_tasks}</span>
                    </div>
                    <div class="feature-meta-info">
                        <div class="feature-description">{feature_info_detail["description"]}</div>
                        <div class="feature-created-at">{feature_info_detail["created_at"]}</div>
                    </div>
                </div>
                <div class="feature-tasks" style="display: none;">
                    {feature_tasks_html}
                </div>
            </div>"""

        task_items_rendered = (
            task_items_html
            if task_items_html
            else '<div style="padding: 12px; color: #999; font-size: 12px;">'
            "No tasks available"
            "</div>"
        )

        template_path = files("tasktree.graph.assets.graph_assets") / "index.html"
        template_html = template_path.read_text(encoding="utf-8")
        html = template_html.replace("{{TASK_ITEMS}}", task_items_rendered)
        self._send_html_response(200, html)

    def _handle_static_request(self, request_path: str) -> None:
        """Serve static assets under /static."""
        relative_path = request_path.removeprefix("/static/")

        if not relative_path or relative_path.endswith("/"):
            self._send_error(404, "Not Found")
            return

        safe_path = Path(unquote(relative_path))
        asset_path = self.assets_dir / str(safe_path)

        if not asset_path.is_file():
            self._send_error(404, "Not Found")
            return

        content_type = self.mime_types.get(
            safe_path.suffix.lower(), "application/octet-stream"
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
                SELECT
                    t.name,
                    t.description,
                    t.status,
                    t.priority,
                    t.created_at,
                    t.started_at,
                    t.completed_at,
                    t.specification,
                    t.tests_required,
                    f.name AS feature_name,
                    f.description AS feature_description,
                    f.created_at AS feature_created_at,
                    t.updated_at
                FROM tasks t
                JOIN features f ON t.feature_id = f.id
                ORDER BY CASE t.status
                             WHEN 'blocked' THEN 1
                             WHEN 'in_progress' THEN 2
                             WHEN 'pending' THEN 3
                             WHEN 'completed' THEN 4
                         END,
                         t.priority DESC,
                         t.created_at ASC
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
                        "specification": row[7],
                        "tests_required": bool(row[8]),
                        "feature_name": row[9],
                        "feature_color": self._get_feature_color(row[9]),
                        "feature_description": row[10],
                        "feature_created_at": row[11],
                        "updated_at": row[12],
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
        default=Path(".tasktree/tasktree.db"),
        help="Path to SQLite database (default: .tasktree/tasktree.db)",
    )

    args = parser.parse_args()

    run_server(args.port, args.db)


if __name__ == "__main__":
    main()
