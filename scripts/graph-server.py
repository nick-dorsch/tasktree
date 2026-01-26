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
        """Handle root endpoint with task list panel and graph visualization."""
        # Get task data for the panel
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all tasks sorted by status, priority (descending), then name
        cursor.execute("""
            SELECT name, description, status, priority, created_at, started_at, completed_at, details
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

        # Get overall started_at and completed_at from node data
        cursor.execute("""
            SELECT MIN(started_at), MAX(completed_at)
            FROM tasks
            WHERE started_at IS NOT NULL OR completed_at IS NOT NULL
        """)
        overall_times = cursor.fetchone()
        overall_started = overall_times[0] if overall_times else None
        overall_completed = overall_times[1] if overall_times else None

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
                <div class="task-details-row"><span class="task-details-label">Description:</span> {description if description else "None"}</div>"""

            if details:
                details_html += f"""
                <div class="task-details-row"><span class="task-details-label">Details:</span> {details}</div>"""

            details_html += f"""
                <div class="task-details-row"><span class="task-details-label">Created:</span> {created_at if created_at else "None"}</div>"""

            if started_at:
                details_html += f"""
                <div class="task-details-row"><span class="task-details-label">Started:</span> {started_at}</div>"""

            if completed_at:
                details_html += f"""
                <div class="task-details-row"><span class="task-details-label">Completed:</span> {completed_at}</div>"""

            task_items_html += f"""
            <div class="task-item" data-status="{status}">
                <div class="task-header" onclick="toggleTaskDetails(this)">
                    <span class="task-status-dot" style="background: {status_color};"></span>
                    <span class="task-name" title="{name}">{name}</span>
                    <span class="task-expand-icon">▶</span>
                </div>
                <div class="task-details" style="display: none;">
                    {details_html}
                </div>
            </div>"""

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
            <div class="panel-meta">
                {f"Started: {overall_started}" if overall_started else "Not started"}<br>
                {f"Completed: {overall_completed}" if overall_completed else "Not completed"}
            </div>
        </div>
        <div class="task-list">
            {task_items_html if task_items_html else '<div style="padding: 12px; color: #999; font-size: 12px;">No tasks available</div>'}
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
        </div>
        
        <div class="legend-section">
            <div class="legend-section-title">Available Tasks</div>
            <div class="legend-item">
                <div class="legend-color-box available" style="background: #2196F3;"></div>
                <span>Green border + glow</span>
            </div>
        </div>
        
        <div class="legend-section">
            <div class="legend-section-title">Node Size</div>
            <div class="legend-item">
                <span class="legend-size-example" style="width: 8px; height: 8px;"></span>
                <span>Priority 0 (lowest)</span>
            </div>
            <div class="legend-item">
                <span class="legend-size-example" style="width: 19px; height: 19px;"></span>
                <span>Priority 5 (medium)</span>
            </div>
            <div class="legend-item">
                <span class="legend-size-example" style="width: 30px; height: 30px;"></span>
                <span>Priority 10 (highest)</span>
            </div>
        </div>
        
        <div class="legend-section">
            <div class="legend-section-title">Dependencies</div>
            <div class="legend-item">
                <div class="legend-arrow"></div>
                <span>Points to dependent</span>
            </div>
        </div>
    </div>

    <script>
        // Task list toggle functionality
        function toggleTaskDetails(headerElement) {{
            const taskItem = headerElement.parentElement;
            const detailsDiv = taskItem.querySelector('.task-details');
            const expandIcon = headerElement.querySelector('.task-expand-icon');
            
            if (detailsDiv.style.display === 'none') {{
                detailsDiv.style.display = 'block';
                expandIcon.classList.add('expanded');
            }} else {{
                detailsDiv.style.display = 'none';
                expandIcon.classList.remove('expanded');
            }}
        }}

        // Configuration
        const API_ENDPOINT = '/api/graph';
        const WIDTH = window.innerWidth;
        const HEIGHT = window.innerHeight;
        
        // Status colors
        const STATUS_COLORS = {{
            'pending': '#2196F3',      // Blue
            'in_progress': '#FFC107',  // Yellow/Amber
            'completed': '#4CAF50',    // Green
            'blocked': '#F44336'       // Red
        }};

        // Create SVG
        const svg = d3.select('#graph')
            .append('svg')
            .attr('width', WIDTH)
            .attr('height', HEIGHT);

        // Define arrowhead marker for directed edges
        const defs = svg.append('defs');
        
        defs.append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 4.5)
            .attr('markerHeight', 4.5)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#666');

        // Define glow filter for available tasks
        const filter = defs.append('filter')
            .attr('id', 'glow')
            .attr('x', '-50%')
            .attr('y', '-50%')
            .attr('width', '200%')
            .attr('height', '200%');

        filter.append('feGaussianBlur')
            .attr('stdDeviation', '3')
            .attr('result', 'coloredBlur');

        const feMerge = filter.append('feMerge');
        feMerge.append('feMergeNode').attr('in', 'coloredBlur');
        feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

        // Create container for zoom/pan
        const container = svg.append('g');

        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {{
                container.attr('transform', event.transform);
            }});

        svg.call(zoom);

        // Initialize force simulation
        const simulation = d3.forceSimulation()
            .force('link', d3.forceLink().id(d => d.name).distance(150))
            .force('charge', d3.forceManyBody().strength(-400))
            .force('center', d3.forceCenter(WIDTH / 2, HEIGHT / 2))
            .force('collision', d3.forceCollide().radius(30));

        // Graph elements
        let linkGroup = container.append('g').attr('class', 'links');
        let nodeGroup = container.append('g').attr('class', 'nodes');
        let labelGroup = container.append('g').attr('class', 'labels');

        let link, node, label;

        // Tooltip
        const tooltip = d3.select('#tooltip');

        function showTooltip(event, d) {{
            const content = `
                <div><span class="tooltip-label">Task:</span> ${{d.name}}</div>
                <div><span class="tooltip-label">Description:</span> ${{d.description || 'N/A'}}</div>
                <div><span class="tooltip-label">Status:</span> ${{d.status}}</div>
                <div><span class="tooltip-label">Priority:</span> ${{d.priority}}</div>
                <div><span class="tooltip-label">Available:</span> ${{d.is_available ? 'Yes' : 'No'}}</div>
                ${{d.started_at ? `<div><span class="tooltip-label">Started:</span> ${{d.started_at}}</div>` : ''}}
                ${{d.completed_at ? `<div><span class="tooltip-label">Completed:</span> ${{d.completed_at}}</div>` : ''}}
                ${{d.completion_minutes !== null && d.completion_minutes !== undefined ? `<div><span class="tooltip-label">Duration:</span> ${{d.completion_minutes}} min</div>` : ''}}
            `;
            
            tooltip.html(content)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY + 10) + 'px')
                .classed('visible', true);
        }}

        function hideTooltip() {{
            tooltip.classed('visible', false);
        }}

        function getNodeColor(d) {{
            return STATUS_COLORS[d.status] || '#999';
        }}

        function getNodeRadius(d) {{
            if (d.status === 'completed') return 10;
            return 8 + (d.priority / 10) * 22;
        }}

        function getNodeStroke(d) {{
            // Highlight available tasks with a bright border
            return d.is_available ? '#00FF00' : '#333';
        }}

        function getNodeStrokeWidth(d) {{
            return d.is_available ? 3 : 2;
        }}

        function updateGraph(graphData) {{
            // Update loading state
            d3.select('#loading').style('display', 'none');

            // Store current positions BEFORE data update
            const positionCache = new Map();
            if (node) {{
                node.each(d => {{
                    positionCache.set(d.name, {{
                        x: d.x,
                        y: d.y,
                        vx: d.vx || 0,
                        vy: d.vy || 0,
                        fx: d.fx,
                        fy: d.fy
                    }});
                }});
            }}

            // Convert edges from {{from, to}} to {{source, target}}
            const links = graphData.edges.map(e => ({{
                source: e.from,
                target: e.to
            }}));

            const nodes = graphData.nodes;

            // Store previous counts for change detection
            const previousNodeCount = positionCache.size;
            const previousLinkCount = link ? link.size() : 0;

            // Update links (stable key function handles D3 mutation)
            link = linkGroup.selectAll('.link')
                .data(links, d => {{
                    const source = typeof d.source === 'object' ? d.source.name : d.source;
                    const target = typeof d.target === 'object' ? d.target.name : d.target;
                    return `${{source}}-${{target}}`;
                }});

            link.exit().remove();

            const linkEnter = link.enter()
                .append('path')
                .attr('class', 'link');

            link = linkEnter.merge(link);

            // Update nodes
            node = nodeGroup.selectAll('.node')
                .data(nodes, d => d.name);

            node.exit().remove();

            const nodeEnter = node.enter()
                .append('circle')
                .attr('class', 'node')
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended))
                .on('mouseover', showTooltip)
                .on('mouseout', hideTooltip);

            node = nodeEnter.merge(node);

            // Restore positions for existing nodes AFTER data join
            node.each(d => {{
                const cached = positionCache.get(d.name);
                if (cached) {{
                    d.x = cached.x;
                    d.y = cached.y;
                    d.vx = cached.vx;
                    d.vy = cached.vy;
                    d.fx = cached.fx;
                    d.fy = cached.fy;
                }}
                // New nodes will get default force-directed positions
            }});

            node.attr('r', getNodeRadius)
                .attr('fill', getNodeColor)
                .attr('stroke', getNodeStroke)
                .attr('stroke-width', getNodeStrokeWidth)
                .attr('filter', d => d.is_available ? 'url(#glow)' : null);

            // Update labels
            label = labelGroup.selectAll('.node-label')
                .data(nodes, d => d.name);

            label.exit().remove();

            const labelEnter = label.enter()
                .append('text')
                .attr('class', 'node-label')
                .attr('dy', 4);

            label = labelEnter.merge(label);

            label.text(d => d.name.length > 20 ? d.name.substring(0, 18) + '...' : d.name);

            // Detect structural changes
            const structureChanged = 
                nodes.length !== previousNodeCount ||
                links.length !== previousLinkCount;

            // Update simulation
            simulation.nodes(nodes).on('tick', ticked);
            simulation.force('link').links(links);
            
            // Only reheat simulation if structure changed
            if (structureChanged) {{
                simulation.alpha(0.3).restart();
            }}
        }}

        function ticked() {{
            link.attr('d', d => {{
                const sourceX = d.source.x;
                const sourceY = d.source.y;
                const targetX = d.target.x;
                const targetY = d.target.y;
                
                // Calculate the direction vector
                const dx = targetX - sourceX;
                const dy = targetY - sourceY;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist === 0) return `M${{sourceX}},${{sourceY}}L${{targetX}},${{targetY}}`;
                
                // Adjust the end point to stop at the target node's edge
                const targetRadius = getNodeRadius(d.target);
                const offsetX = (dx / dist) * targetRadius;
                const offsetY = (dy / dist) * targetRadius;
                
                const adjustedTargetX = targetX - offsetX;
                const adjustedTargetY = targetY - offsetY;
                
                return `M${{sourceX}},${{sourceY}}L${{adjustedTargetX}},${{adjustedTargetY}}`;
            }});

            node.attr('cx', d => d.x)
                .attr('cy', d => d.y);

            label.attr('x', d => d.x)
                .attr('y', d => d.y);
        }}

        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}

        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}

        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}

        function showError(message) {{
            d3.select('#loading').style('display', 'none');
            
            const errorDiv = d3.select('body')
                .append('div')
                .attr('class', 'error-message')
                .text(message);
            
            setTimeout(() => errorDiv.remove(), 5000);
        }}

        async function fetchGraph() {{
            try {{
                const response = await fetch(API_ENDPOINT);
                
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                }}
                
                const data = await response.json();
                updateGraph(data);
            }} catch (error) {{
                console.error('Error fetching graph:', error);
                showError(`Failed to fetch graph: ${{error.message}}`);
            }}
        }}

        // Initial fetch
        fetchGraph();

        // Auto-refresh every 3 seconds
        setInterval(fetchGraph, 3000);

        // Handle window resize
        window.addEventListener('resize', () => {{
            const newWidth = window.innerWidth;
            const newHeight = window.innerHeight;
            
            svg.attr('width', newWidth).attr('height', newHeight);
            
            simulation.force('center', d3.forceCenter(newWidth / 2, newHeight / 2));
            simulation.alpha(0.3).restart();
        }});
    </script>
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
