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
        return

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskTree Graph Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            overflow: hidden;
            background-color: #1a1a1a;
        }}

        #graph {{
            width: 100vw;
            height: 100vh;
        }}

        /* Glass Panel Styling */
        .task-panel {{
            position: fixed;
            top: 20px;
            left: 20px;
            width: 320px;
            max-height: calc(100vh - 40px);
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            z-index: 100;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .panel-header {{
            padding: 16px 20px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.05);
        }}

        .panel-title {{
            font-weight: bold;
            font-size: 16px;
            color: #4fc3f7;
            margin-bottom: 8px;
        }}

        .panel-meta {{
            font-size: 11px;
            color: #aaa;
            line-height: 1.4;
        }}

        .feature-filter {{
            margin-top: 8px;
        }}

        .feature-filter select {{
            width: 100%;
            padding: 6px 10px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #e0e0e0;
            font-size: 12px;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .feature-filter select:hover {{
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.3);
        }}

        .feature-filter select:focus {{
            outline: none;
            border-color: #4fc3f7;
            box-shadow: 0 0 0 2px rgba(79, 195, 247, 0.2);
        }}

        .feature-filter option {{
            background: #2a2a2a;
            color: #e0e0e0;
        }}

        .task-list {{
            overflow-y: auto;
            flex: 1;
            padding: 8px;
        }}

        .task-list::-webkit-scrollbar {{
            width: 6px;
        }}

        .task-list::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
        }}

        .task-list::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }}

        .task-list::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        .task-item {{
            padding: 0;
            margin-bottom: 8px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            transition: all 0.2s;
            overflow: hidden;
        }}

        .task-item:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.2);
        }}

        .task-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px;
            cursor: pointer;
            user-select: none;
        }}

        .task-header:hover {{
            background: rgba(255, 255, 255, 0.03);
        }}

        .task-status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .task-name {{
            flex: 1;
            font-weight: 600;
            font-size: 13px;
            color: #e0e0e0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .task-expand-icon {{
            font-size: 10px;
            color: #aaa;
            flex-shrink: 0;
            transition: transform 0.2s;
        }}

        .task-expand-icon.expanded {{
            transform: rotate(90deg);
        }}

        .task-details {{
            padding: 0 12px 12px 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            background: rgba(0, 0, 0, 0.2);
        }}

        .task-details-row {{
            font-size: 11px;
            color: #999;
            line-height: 1.6;
            margin: 6px 0;
            padding-left: 16px;
        }}

        .task-details-label {{
            font-weight: 600;
            color: #aaa;
            display: inline-block;
            min-width: 80px;
        }}

        .task-details-value {{
            display: block;
            margin-top: 4px;
            padding-left: 16px;
            max-height: 100px;
            overflow-y: auto;
            word-wrap: break-word;
            white-space: pre-wrap;
        }}

        .task-details-value::-webkit-scrollbar {{
            width: 4px;
        }}

        .task-details-value::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 2px;
        }}

        .task-details-value::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 2px;
        }}

        .task-details-value::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        .node {{
            cursor: pointer;
            stroke-width: 2px;
        }}

        .node-label {{
            font-size: 10px;
            fill: #e0e0e0;
            text-anchor: middle;
            pointer-events: none;
            user-select: none;
        }}

        .link {{
            stroke: #666;
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
            fill: none;
            marker-end: url(#arrowhead);
        }}

        .tooltip {{
            position: absolute;
            padding: 10px;
            background: rgba(0, 0, 0, 0.9);
            color: #fff;
            border: 1px solid #666;
            border-radius: 5px;
            pointer-events: none;
            font-size: 12px;
            opacity: 0;
            transition: opacity 0.3s;
            max-width: 300px;
            z-index: 1000;
        }}

        .tooltip.visible {{
            opacity: 1;
        }}

        .tooltip-label {{
            font-weight: bold;
            color: #4fc3f7;
        }}

        .error-message {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(244, 67, 54, 0.9);
            color: white;
            padding: 20px 40px;
            border-radius: 5px;
            font-size: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}

        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #e0e0e0;
            font-size: 18px;
        }}

        .legend {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 15px;
            color: #e0e0e0;
            font-size: 12px;
            z-index: 100;
            min-width: 200px;
        }}

        .legend-title {{
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 10px;
            color: #4fc3f7;
        }}

        .legend-section {{
            margin-bottom: 12px;
        }}

        .legend-section:last-child {{
            margin-bottom: 0;
        }}

        .legend-section-title {{
            font-weight: bold;
            margin-bottom: 5px;
            font-size: 11px;
            color: #aaa;
            text-transform: uppercase;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            margin: 4px 0;
        }}

        .legend-color-box {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
            border: 2px solid #333;
        }}

        .legend-color-box.available {{
            border: 2px solid #00FF00;
            box-shadow: 0 0 5px #00FF00;
        }}

        .legend-size-example {{
            display: inline-block;
            border-radius: 50%;
            background: #666;
            margin-right: 8px;
            vertical-align: middle;
        }}

        .legend-arrow {{
            width: 30px;
            height: 2px;
            background: #666;
            margin-right: 8px;
            position: relative;
        }}

        .legend-arrow::after {{
            content: '';
            position: absolute;
            right: 0;
            top: -3px;
            width: 0;
            height: 0;
            border-left: 6px solid #666;
            border-top: 4px solid transparent;
            border-bottom: 4px solid transparent;
        }}
    </style>
</head>
<body>
    <!-- Task List Panel -->
    <div class="task-panel">
        <div class="panel-header">
            <div class="panel-title">Tasks</div>
            <div class="feature-filter">
                <select id="feature-dropdown" onchange="filterTasksByFeature()">
                    <option value="">All Features</option>
                    {feature_options}
                </select>
            </div>
        </div>
        <div class="task-list">
            {task_items_rendered}
        </div>
    </div>

    <div id="graph"></div>
    <div class="tooltip" id="tooltip"></div>
    <div class="loading" id="loading">Loading graph data...</div>
    
    <div class="legend">
        <div class="legend-title">Legend</div>
        
        <div class="legend-section">
            <div class="legend-section-title">Status</div>
            <div class="legend-item">
                <div class="legend-color-box" style="background: #F44336;"></div>
                <span>Blocked</span>
            </div>
            <div class="legend-item">
                <div class="legend-color-box" style="background: #FFC107;"></div>
                <span>In Progress</span>
            </div>
            <div class="legend-item">
                <div class="legend-color-box" style="background: #2196F3;"></div>
                <span>Pending</span>
            </div>
            <div class="legend-item">
                <div class="legend-color-box" style="background: #4CAF50;"></div>
                <span>Completed</span>
            </div>
            <div class="legend-item">
                <div class="legend-color-box available" style="background: #2196F3;"></div>
                <span>Available</span>
            </div>
        </div>
    </div>

    <script src="/static/graph.js"></script>
</body>
</html>"""
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
