"""
Tests for the graph viewer HTML (scripts/graph-viewer.html).

Tests that the HTML file exists and contains required D3.js visualization components.
"""

from pathlib import Path

import pytest


@pytest.fixture
def graph_viewer_path():
    """Get the path to the graph viewer HTML file."""
    return Path(__file__).parent.parent / "scripts" / "graph-viewer.html"


def test_graph_viewer_file_exists(graph_viewer_path):
    """Test that the graph viewer HTML file exists."""
    assert graph_viewer_path.exists()
    assert graph_viewer_path.is_file()


def test_graph_viewer_has_html_structure(graph_viewer_path):
    """Test that the HTML file has basic HTML structure."""
    content = graph_viewer_path.read_text()

    # Check for basic HTML structure
    assert "<!DOCTYPE html>" in content
    assert "<html" in content
    assert "<head>" in content
    assert "<body>" in content
    assert "</html>" in content


def test_graph_viewer_includes_d3_library(graph_viewer_path):
    """Test that the HTML includes the D3.js library."""
    content = graph_viewer_path.read_text()

    # Check for D3.js CDN link
    assert "d3js.org/d3" in content or "d3.min.js" in content


def test_graph_viewer_has_graph_container(graph_viewer_path):
    """Test that the HTML has a container for the graph."""
    content = graph_viewer_path.read_text()

    # Check for graph container element
    assert 'id="graph"' in content


def test_graph_viewer_has_api_endpoint_config(graph_viewer_path):
    """Test that the HTML defines the API endpoint."""
    content = graph_viewer_path.read_text()

    # Check for API endpoint configuration
    assert "localhost:8000" in content or "API_ENDPOINT" in content
    assert "/api/graph" in content


def test_graph_viewer_has_status_colors(graph_viewer_path):
    """Test that status-based color coding is defined."""
    content = graph_viewer_path.read_text()

    # Check for status colors (case-insensitive)
    content_lower = content.lower()

    # Should define colors for different statuses
    assert "pending" in content_lower
    assert "in_progress" in content_lower or "in progress" in content_lower
    assert "completed" in content_lower


def test_graph_viewer_has_force_simulation(graph_viewer_path):
    """Test that D3 force simulation is configured."""
    content = graph_viewer_path.read_text()

    # Check for D3 force simulation elements
    assert "forceSimulation" in content or "force simulation" in content.lower()


def test_graph_viewer_has_tooltip(graph_viewer_path):
    """Test that tooltip functionality is included."""
    content = graph_viewer_path.read_text()

    # Check for tooltip elements
    assert "tooltip" in content.lower()


def test_graph_viewer_tooltip_shows_task_name(graph_viewer_path):
    """Test that tooltip displays task name."""
    content = graph_viewer_path.read_text()

    # Check for task name in tooltip
    assert "d.name" in content


def test_graph_viewer_tooltip_shows_description(graph_viewer_path):
    """Test that tooltip displays task description."""
    content = graph_viewer_path.read_text()

    # Check for description in tooltip
    assert "d.description" in content or "Description:" in content


def test_graph_viewer_tooltip_shows_status(graph_viewer_path):
    """Test that tooltip displays task status."""
    content = graph_viewer_path.read_text()

    # Check for status in tooltip
    assert "d.status" in content or "Status:" in content


def test_graph_viewer_tooltip_shows_priority(graph_viewer_path):
    """Test that tooltip displays task priority."""
    content = graph_viewer_path.read_text()

    # Check for priority in tooltip
    assert "d.priority" in content or "Priority:" in content


def test_graph_viewer_tooltip_has_hover_events(graph_viewer_path):
    """Test that tooltip is triggered by hover events."""
    content = graph_viewer_path.read_text()

    # Check for mouseover event to show tooltip
    assert "mouseover" in content.lower() or "mouseenter" in content.lower()

    # Check for mouseout event to hide tooltip
    assert "mouseout" in content.lower() or "mouseleave" in content.lower()


def test_graph_viewer_tooltip_has_show_function(graph_viewer_path):
    """Test that tooltip has a show function."""
    content = graph_viewer_path.read_text()

    # Check for showTooltip function
    assert "showTooltip" in content or "show_tooltip" in content.lower()


def test_graph_viewer_tooltip_has_hide_function(graph_viewer_path):
    """Test that tooltip has a hide function."""
    content = graph_viewer_path.read_text()

    # Check for hideTooltip function
    assert "hideTooltip" in content or "hide_tooltip" in content.lower()


def test_graph_viewer_tooltip_element_exists(graph_viewer_path):
    """Test that tooltip HTML element is defined."""
    content = graph_viewer_path.read_text()

    # Check for tooltip element in HTML
    assert 'id="tooltip"' in content or "id='tooltip'" in content


def test_graph_viewer_tooltip_styling(graph_viewer_path):
    """Test that tooltip has CSS styling."""
    content = graph_viewer_path.read_text()

    # Check for tooltip class in CSS
    assert ".tooltip" in content


def test_graph_viewer_has_node_rendering(graph_viewer_path):
    """Test that node rendering is implemented."""
    content = graph_viewer_path.read_text()

    # Check for node-related code
    assert "node" in content.lower()
    # Check for circle or similar node shape
    assert "circle" in content.lower() or "rect" in content.lower()


def test_graph_viewer_has_link_rendering(graph_viewer_path):
    """Test that link/edge rendering is implemented."""
    content = graph_viewer_path.read_text()

    # Check for link/edge-related code
    assert "link" in content.lower() or "edge" in content.lower()


def test_graph_viewer_has_drag_behavior(graph_viewer_path):
    """Test that drag-and-drop behavior is implemented."""
    content = graph_viewer_path.read_text()

    # Check for drag behavior
    assert "drag" in content.lower()


def test_graph_viewer_has_zoom_behavior(graph_viewer_path):
    """Test that zoom/pan behavior is implemented."""
    content = graph_viewer_path.read_text()

    # Check for zoom functionality
    assert "zoom" in content.lower()


def test_graph_viewer_has_auto_refresh(graph_viewer_path):
    """Test that auto-refresh functionality is included."""
    content = graph_viewer_path.read_text()

    # Check for interval/polling mechanism
    assert "setInterval" in content or "setTimeout" in content


def test_graph_viewer_has_error_handling(graph_viewer_path):
    """Test that error handling is implemented."""
    content = graph_viewer_path.read_text()

    # Check for error handling
    assert "catch" in content or "error" in content.lower()


def test_graph_viewer_has_fetch_api_call(graph_viewer_path):
    """Test that the HTML fetches data from the API."""
    content = graph_viewer_path.read_text()

    # Check for fetch API call
    assert "fetch" in content.lower()


def test_graph_viewer_has_arrowhead_marker(graph_viewer_path):
    """Test that directed graph arrows are defined."""
    content = graph_viewer_path.read_text()

    # Check for SVG marker definition for arrows
    assert "marker" in content.lower()
    assert "arrowhead" in content.lower() or "arrow" in content.lower()


def test_graph_viewer_styling_included(graph_viewer_path):
    """Test that CSS styling is included."""
    content = graph_viewer_path.read_text()

    # Check for style tag or CSS
    assert "<style>" in content or "css" in content.lower()


def test_graph_viewer_has_title(graph_viewer_path):
    """Test that the HTML has a descriptive title."""
    content = graph_viewer_path.read_text()

    # Check for title
    assert "<title>" in content
    assert "TaskTree" in content or "Graph" in content


def test_graph_viewer_responsive_design(graph_viewer_path):
    """Test that viewport meta tag is included for responsive design."""
    content = graph_viewer_path.read_text()

    # Check for viewport meta tag
    assert "viewport" in content


def test_graph_viewer_uses_svg(graph_viewer_path):
    """Test that visualization uses SVG."""
    content = graph_viewer_path.read_text()

    # Check for SVG usage
    assert "svg" in content.lower()


def test_graph_viewer_has_priority_based_sizing(graph_viewer_path):
    """Test that priority-based node sizing is implemented."""
    content = graph_viewer_path.read_text()

    # Check for priority-based sizing logic
    assert "priority" in content.lower()


def test_graph_viewer_node_size_range(graph_viewer_path):
    """Test that node size scales from 8px (min priority) to 30px (max priority)."""
    content = graph_viewer_path.read_text()

    # Find the getNodeRadius function
    lines = content.split("\n")
    found_function = False
    for i, line in enumerate(lines):
        if "function getNodeRadius" in line or "getNodeRadius(d)" in line:
            # Get the function body (next few lines)
            function_body = "\n".join(lines[i : i + 5])

            # Should return 8 + something based on priority
            assert "return 8 +" in function_body, (
                "Node radius should start at minimum 8 pixels"
            )

            # For priority 10, should return 30 (8 + 22)
            # Formula: 8 + (priority / 10) * 22
            assert "* 22" in function_body, (
                "Node radius should scale with factor of 22 to reach max 30px at priority 10"
            )

            # Should use priority in calculation
            assert "priority" in function_body.lower(), (
                "Node radius should be based on priority"
            )

            found_function = True
            break

    assert found_function, "Could not find getNodeRadius function"


def test_graph_viewer_has_available_task_highlighting(graph_viewer_path):
    """Test that available tasks are visually highlighted."""
    content = graph_viewer_path.read_text()

    # Check for is_available flag usage
    assert "is_available" in content or "available" in content.lower()


def test_graph_viewer_has_glow_filter(graph_viewer_path):
    """Test that a glow filter is defined for highlighting available tasks."""
    content = graph_viewer_path.read_text()

    # Check for filter definition in SVG defs (via D3.js)
    assert "filter" in content.lower()
    assert ".attr('id', 'glow')" in content or '.attr("id", "glow")' in content

    # Check for Gaussian blur effect (creates the glow)
    assert "feGaussianBlur" in content

    # Check for merge nodes (combines blur with original graphic)
    assert "feMerge" in content


def test_graph_viewer_applies_glow_to_available_tasks(graph_viewer_path):
    """Test that the glow filter is applied to available tasks."""
    content = graph_viewer_path.read_text()

    # Check that nodes have filter attribute based on is_available
    assert "filter" in content.lower()
    assert "url(#glow)" in content

    # Should conditionally apply filter based on is_available
    # Look for pattern: d.is_available ? 'url(#glow)' : null
    assert "is_available" in content and "url(#glow)" in content


def test_graph_viewer_has_position_caching(graph_viewer_path):
    """Test that position caching is implemented to preserve node positions."""
    content = graph_viewer_path.read_text()

    # Check for position caching mechanism
    assert "positionCache" in content or "position_cache" in content.lower()
    # Should use Map for caching
    assert "Map()" in content or "new Map" in content


def test_graph_viewer_preserves_node_positions(graph_viewer_path):
    """Test that existing node positions are preserved across updates."""
    content = graph_viewer_path.read_text()

    # Should cache x, y coordinates
    assert ".x" in content and ".y" in content
    # Should cache velocity (vx, vy)
    assert ".vx" in content or "vx" in content
    assert ".vy" in content or "vy" in content


def test_graph_viewer_has_smart_simulation_restart(graph_viewer_path):
    """Test that simulation restart is conditional based on structural changes."""
    content = graph_viewer_path.read_text()

    # Should detect structural changes
    assert "structureChanged" in content or "structure_changed" in content.lower()
    # Should have conditional logic for restart
    assert "if" in content and "restart()" in content


def test_graph_viewer_only_restarts_on_structure_change(graph_viewer_path):
    """Test that simulation only restarts when structure changes, not for property updates."""
    content = graph_viewer_path.read_text()

    # Should detect structural changes
    assert "structureChanged" in content

    # Should restart simulation with alpha for structural changes
    assert "alpha(0.3)" in content or "alpha(0.5)" in content

    # Should have conditional restart (only if structureChanged)
    # This prevents drift during property-only updates
    lines = content.split("\n")
    found_conditional_restart = False
    for i, line in enumerate(lines):
        if "if (structureChanged)" in line or "if(structureChanged)" in line:
            # Check the next few lines for alpha restart
            next_lines = "\n".join(lines[i : i + 5])
            if "alpha(" in next_lines and "restart()" in next_lines:
                found_conditional_restart = True
                break

    assert found_conditional_restart, (
        "Simulation restart should only occur when structureChanged is true"
    )


def test_graph_viewer_no_simulation_restart_for_property_updates(graph_viewer_path):
    """Test that simulation does NOT restart for property-only updates (fixes drift bug)."""
    content = graph_viewer_path.read_text()

    # Find the structureChanged conditional block
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "if (structureChanged)" in line or "if(structureChanged)" in line:
            # Look for the closing brace and check there's no else block with restart
            # The else block would cause drift on property updates
            next_lines = lines[i : i + 10]

            # Should NOT have an else block that restarts the simulation
            # This was the cause of the drift bug
            has_problematic_else = False
            in_else_block = False
            for j, next_line in enumerate(next_lines):
                if "} else {" in next_line or "}else{" in next_line:
                    in_else_block = True
                if in_else_block and "alpha(" in next_line and "restart()" in next_line:
                    has_problematic_else = True
                    break

            assert not has_problematic_else, (
                "Found else block that restarts simulation for property updates - "
                "this causes graph drift bug. Only structural changes should restart simulation."
            )
            break


def test_graph_viewer_has_stable_link_key_function(graph_viewer_path):
    """Test that link data join uses stable key function to handle D3 mutations."""
    content = graph_viewer_path.read_text()

    # The key function should handle both string and object forms of source/target
    # This prevents edges from disappearing during polling after D3 mutates the data
    assert "typeof d.source === 'object'" in content, (
        "Link key function should check if d.source is an object (after D3 mutation)"
    )
    assert "typeof d.target === 'object'" in content, (
        "Link key function should check if d.target is an object (after D3 mutation)"
    )

    # Should extract the name property when it's an object
    assert "d.source.name" in content, (
        "Link key function should extract name from source object reference"
    )
    assert "d.target.name" in content, (
        "Link key function should extract name from target object reference"
    )

    # Find the link data join and verify the stable key function
    lines = content.split("\n")
    found_stable_key_pattern = False
    for i, line in enumerate(lines):
        if ".data(links," in line and "d =>" in line:
            # Check the next few lines for the stable key function logic
            next_lines = "\n".join(lines[i : i + 5])
            if (
                "typeof d.source === 'object'" in next_lines
                and "typeof d.target === 'object'" in next_lines
                and "d.source.name" in next_lines
                and "d.target.name" in next_lines
            ):
                found_stable_key_pattern = True
                break

    assert found_stable_key_pattern, (
        "Link data join should use a stable key function that handles both "
        "string IDs (initial) and object references (after D3 mutation)"
    )


def test_graph_viewer_has_legend(graph_viewer_path):
    """Test that the graph viewer includes a legend."""
    content = graph_viewer_path.read_text()

    # Check for legend element
    assert "legend" in content.lower()
    # Check for legend div with class
    assert 'class="legend"' in content or "class='legend'" in content


def test_graph_viewer_legend_shows_status_colors(graph_viewer_path):
    """Test that the legend shows status color meanings."""
    content = graph_viewer_path.read_text()

    # Legend should show all three status states
    content_lower = content.lower()
    assert "pending" in content_lower
    assert "in progress" in content_lower or "in_progress" in content_lower
    assert "completed" in content_lower

    # Should show the actual colors in the legend
    assert "#2196F3" in content  # Blue for pending
    assert "#FFC107" in content  # Yellow for in_progress
    assert "#4CAF50" in content  # Green for completed


def test_graph_viewer_legend_shows_node_size_meaning(graph_viewer_path):
    """Test that the legend explains node size (priority-based)."""
    content = graph_viewer_path.read_text()

    # Legend should mention node size or priority
    content_lower = content.lower()
    assert "node size" in content_lower or "priority" in content_lower

    # Should show examples of different priorities
    # Looking for references to priority levels (0, 5, 10) or min/max
    has_priority_examples = (
        "priority 0" in content_lower
        or "priority 5" in content_lower
        or "priority 10" in content_lower
        or "lowest" in content_lower
        or "highest" in content_lower
    )
    assert has_priority_examples, "Legend should show priority examples"


def test_graph_viewer_legend_shows_available_task_indicator(graph_viewer_path):
    """Test that the legend explains the available task highlighting."""
    content = graph_viewer_path.read_text()

    # Legend should explain available tasks
    content_lower = content.lower()
    assert "available" in content_lower

    # Should mention the green border
    assert "#00FF00" in content or "00FF00" in content  # Green border color
    assert "border" in content_lower or "glow" in content_lower


def test_graph_viewer_legend_shows_dependency_arrows(graph_viewer_path):
    """Test that the legend explains what arrows/dependencies mean."""
    content = graph_viewer_path.read_text()

    # Legend should explain dependencies
    content_lower = content.lower()
    assert "dependenc" in content_lower or "arrow" in content_lower

    # Should show visual representation of an arrow
    # Looking for CSS classes like legend-arrow or arrow styling
    assert "legend-arrow" in content or "arrow" in content_lower


def test_graph_viewer_legend_has_styling(graph_viewer_path):
    """Test that the legend has CSS styling."""
    content = graph_viewer_path.read_text()

    # Check for legend CSS class
    assert ".legend" in content
    # Legend should be positioned (absolutely or fixed)
    assert "position:" in content.lower() or "position :" in content.lower()


def test_graph_viewer_legend_positioned_correctly(graph_viewer_path):
    """Test that the legend is positioned in a non-intrusive location."""
    content = graph_viewer_path.read_text()

    # Find the legend CSS block
    lines = content.split("\n")
    found_legend_css = False
    for i, line in enumerate(lines):
        if ".legend {" in line or ".legend{" in line:
            # Get the CSS block (next ~15 lines)
            css_block = "\n".join(lines[i : i + 15])

            # Should be absolutely positioned
            assert (
                "position: absolute" in css_block or "position:absolute" in css_block
            ), "Legend should be absolutely positioned"

            # Should be positioned at top/bottom and left/right
            has_positioning = (
                "top:" in css_block
                or "bottom:" in css_block
                or "right:" in css_block
                or "left:" in css_block
            )
            assert has_positioning, (
                "Legend should have top/bottom/left/right positioning"
            )

            found_legend_css = True
            break

    assert found_legend_css, "Could not find .legend CSS definition"


def test_graph_viewer_legend_has_title(graph_viewer_path):
    """Test that the legend has a title."""
    content = graph_viewer_path.read_text()

    # Legend should have a title section
    assert "legend-title" in content.lower() or (
        "legend" in content.lower() and "title" in content.lower()
    )


def test_graph_viewer_completed_nodes_fixed_size(graph_viewer_path):
    """Test that completed task nodes use fixed small size regardless of priority."""
    content = graph_viewer_path.read_text()

    # Find the getNodeRadius function
    lines = content.split("\n")
    found_function = False
    for i, line in enumerate(lines):
        if "function getNodeRadius" in line or "getNodeRadius(d)" in line:
            # Get the function body (next ~10 lines)
            function_body = "\n".join(lines[i : i + 10])

            # Should check for completed status
            assert (
                "d.status === 'completed'" in function_body
                or 'd.status === "completed"' in function_body
            ), "getNodeRadius should check if status is completed"

            # Should return fixed size (10) for completed tasks
            assert "return 10;" in function_body, (
                "Completed tasks should return fixed radius of 10"
            )

            found_function = True
            break

    assert found_function, "Could not find getNodeRadius function"


def test_graph_viewer_non_completed_nodes_priority_scaling(graph_viewer_path):
    """Test that pending/in_progress nodes still use priority-based scaling."""
    content = graph_viewer_path.read_text()

    # Find the getNodeRadius function
    lines = content.split("\n")
    found_function = False
    for i, line in enumerate(lines):
        if "function getNodeRadius" in line or "getNodeRadius(d)" in line:
            # Get the function body (next ~10 lines)
            function_body = "\n".join(lines[i : i + 10])

            # Should still have priority-based scaling for non-completed tasks
            assert "8 + (d.priority / 10) * 22" in function_body, (
                "Non-completed tasks should still use priority-based scaling (8 + (priority/10) * 22)"
            )

            # Should have both the completed check AND the priority scaling
            has_completed_check = (
                "d.status === 'completed'" in function_body
                or 'd.status === "completed"' in function_body
            )
            has_priority_scaling = "d.priority" in function_body

            assert has_completed_check and has_priority_scaling, (
                "Function should have both completed check and priority scaling logic"
            )

            found_function = True
            break

    assert found_function, "Could not find getNodeRadius function"


def test_graph_viewer_legend_shows_completed_fixed_size(graph_viewer_path):
    """Test that the legend indicates completed tasks have fixed small size."""
    content = graph_viewer_path.read_text()

    # Legend should mention completed tasks have fixed size
    content_lower = content.lower()

    # Check for "completed" and "fixed" or "small" in close proximity
    assert "completed" in content_lower, "Legend should mention completed tasks"

    # The legend should show completed as fixed small size
    # Looking for "Completed (fixed small)" or similar
    assert "fixed" in content_lower or "small" in content_lower, (
        "Legend should indicate completed tasks have fixed or small size"
    )
