window.tasktreeGraphServerAssetsLoaded = true;

// Task list toggle functionality
function toggleTaskDetails(headerElement) {
    const taskItem = headerElement.parentElement;
    const detailsDiv = taskItem.querySelector('.task-details');
    const expandIcon = headerElement.querySelector('.task-expand-icon');

    // Check if this task is currently expanded
    const isExpanding = detailsDiv.style.display === 'none';

    if (isExpanding) {
        // Close all other expanded tasks first
        document.querySelectorAll('.task-details').forEach(details => {
            details.style.display = 'none';
        });
        document.querySelectorAll('.task-expand-icon').forEach(icon => {
            icon.classList.remove('expanded');
        });

        // Now expand this task
        detailsDiv.style.display = 'block';
        expandIcon.classList.add('expanded');
    } else {
        // Collapse this task
        detailsDiv.style.display = 'none';
        expandIcon.classList.remove('expanded');
    }
}

// Feature filter functionality
function filterTasksByFeature() {
    const selectedFeature = document.getElementById('feature-dropdown').value;
    const taskItems = document.querySelectorAll('.task-item');

    taskItems.forEach(item => {
        const taskFeature = item.getAttribute('data-feature');

        // Show all if no feature selected, otherwise only show matching feature
        if (selectedFeature === '' || taskFeature === selectedFeature) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

// Configuration
const API_ENDPOINT = '/api/graph';
const TASKS_ENDPOINT = '/api/tasks';
const WIDTH = window.innerWidth;
const HEIGHT = window.innerHeight;

// Status colors
const STATUS_COLORS = {
    pending: '#2196F3',
    in_progress: '#FFC107',
    completed: '#4CAF50',
    blocked: '#F44336',
};

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
    .on('zoom', (event) => {
        container.attr('transform', event.transform);
    });

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

function showTooltip(event, d) {
    const content = `
        <div><span class="tooltip-label">Task:</span> ${d.name}</div>
        <div><span class="tooltip-label">Description:</span> ${d.description || 'N/A'}</div>
        <div><span class="tooltip-label">Status:</span> ${d.status}</div>
        <div><span class="tooltip-label">Priority:</span> ${d.priority}</div>
        <div><span class="tooltip-label">Available:</span> ${d.is_available ? 'Yes' : 'No'}</div>
        ${d.started_at ? `<div><span class="tooltip-label">Started:</span> ${d.started_at}</div>` : ''}
        ${d.completed_at ? `<div><span class="tooltip-label">Completed:</span> ${d.completed_at}</div>` : ''}
        ${d.completion_minutes !== null && d.completion_minutes !== undefined ? `<div><span class="tooltip-label">Duration:</span> ${d.completion_minutes} min</div>` : ''}
    `;

    tooltip.html(content)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY + 10) + 'px')
        .classed('visible', true);
}

function hideTooltip() {
    tooltip.classed('visible', false);
}

function getNodeColor(d) {
    return STATUS_COLORS[d.status] || '#999';
}

function getNodeRadius(d) {
    if (d.status === 'completed') return 10;
    return 8 + (d.priority / 10) * 22;
}

function getNodeStroke(d) {
    // Highlight available tasks with a bright border
    return d.is_available ? '#00FF00' : '#333';
}

function getNodeStrokeWidth(d) {
    return d.is_available ? 3 : 2;
}

function updateGraph(graphData) {
    // Update loading state
    d3.select('#loading').style('display', 'none');

    // Store current positions BEFORE data update
    const positionCache = new Map();
    if (node) {
        node.each(d => {
            positionCache.set(d.name, {
                x: d.x,
                y: d.y,
                vx: d.vx || 0,
                vy: d.vy || 0,
                fx: d.fx,
                fy: d.fy,
            });
        });
    }

    // Convert edges from {from, to} to {source, target}
    const links = graphData.edges.map(e => ({
        source: e.from,
        target: e.to,
    }));

    const nodes = graphData.nodes;

    // Store previous counts for change detection
    const previousNodeCount = positionCache.size;
    const previousLinkCount = link ? link.size() : 0;

    // Update links (stable key function handles D3 mutation)
    link = linkGroup.selectAll('.link')
        .data(links, d => {
            const source = typeof d.source === 'object' ? d.source.name : d.source;
            const target = typeof d.target === 'object' ? d.target.name : d.target;
            return `${source}-${target}`;
        });

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
    node.each(d => {
        const cached = positionCache.get(d.name);
        if (cached) {
            d.x = cached.x;
            d.y = cached.y;
            d.vx = cached.vx;
            d.vy = cached.vy;
            d.fx = cached.fx;
            d.fy = cached.fy;
        }
        // New nodes will get default force-directed positions
    });

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
    if (structureChanged) {
        simulation.alpha(0.3).restart();
    }
}

function ticked() {
    link.attr('d', d => {
        const sourceX = d.source.x;
        const sourceY = d.source.y;
        const targetX = d.target.x;
        const targetY = d.target.y;

        // Calculate the direction vector
        const dx = targetX - sourceX;
        const dy = targetY - sourceY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist === 0) return `M${sourceX},${sourceY}L${targetX},${targetY}`;

        // Adjust the end point to stop at the target node's edge
        const targetRadius = getNodeRadius(d.target);
        const offsetX = (dx / dist) * targetRadius;
        const offsetY = (dy / dist) * targetRadius;

        const adjustedTargetX = targetX - offsetX;
        const adjustedTargetY = targetY - offsetY;

        return `M${sourceX},${sourceY}L${adjustedTargetX},${adjustedTargetY}`;
    });

    node.attr('cx', d => d.x)
        .attr('cy', d => d.y);

    label.attr('x', d => d.x)
        .attr('y', d => d.y);
}

function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

function showError(message) {
    d3.select('#loading').style('display', 'none');

    const errorDiv = d3.select('body')
        .append('div')
        .attr('class', 'error-message')
        .text(message);

    setTimeout(() => errorDiv.remove(), 5000);
}

async function fetchGraph() {
    try {
        const response = await fetch(API_ENDPOINT);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        updateGraph(data);
    } catch (error) {
        console.error('Error fetching graph:', error);
        showError(`Failed to fetch graph: ${error.message}`);
    }
}

async function fetchTasks() {
    try {
        const response = await fetch(TASKS_ENDPOINT);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        updateTaskList(data.tasks);
    } catch (error) {
        console.error('Error fetching tasks:', error);
    }
}

function updateTaskList(tasks) {
    const taskListDiv = document.querySelector('.task-list');

    if (!tasks || tasks.length === 0) {
        taskListDiv.innerHTML = '<div style="padding: 12px; color: #999; font-size: 12px;">No tasks available</div>';
        return;
    }

    // Store currently expanded task names
    const expandedTasks = new Set();
    document.querySelectorAll('.task-details').forEach((details) => {
        if (details.style.display === 'block') {
            const taskItem = details.parentElement;
            const taskName = taskItem.querySelector('.task-name').textContent;
            expandedTasks.add(taskName);
        }
    });

    // Status colors
    const statusColors = {
        pending: '#2196F3',
        in_progress: '#FFC107',
        completed: '#4CAF50',
        blocked: '#F44336',
    };

    // Build task items HTML
    let taskItemsHtml = '';

    tasks.forEach(task => {
        const statusColor = statusColors[task.status] || '#999';

        let detailsHtml = '<div class="task-details-row"><span class="task-details-label">Status:</span> ' + task.status + '</div>' +
            '<div class="task-details-row"><span class="task-details-label">Priority:</span> ' + task.priority + '</div>' +
            '<div class="task-details-row"><span class="task-details-label">Description:</span>' +
            '<div class="task-details-value">' + (task.description || 'None') + '</div></div>';

        if (task.details) {
            detailsHtml += '<div class="task-details-row"><span class="task-details-label">Details:</span>' +
                '<div class="task-details-value">' + task.details + '</div></div>';
        }

        detailsHtml += '<div class="task-details-row"><span class="task-details-label">Created:</span> ' + (task.created_at || 'None') + '</div>';

        if (task.started_at) {
            detailsHtml += '<div class="task-details-row"><span class="task-details-label">Started:</span> ' + task.started_at + '</div>';
        }

        if (task.completed_at) {
            detailsHtml += '<div class="task-details-row"><span class="task-details-label">Completed:</span> ' + task.completed_at + '</div>';
        }

        // Check if this task should be expanded
        const shouldExpand = expandedTasks.has(task.name);
        const expandIcon = '▶';
        const expandClass = shouldExpand ? 'expanded' : '';
        const displayStyle = shouldExpand ? 'block' : 'none';

        taskItemsHtml += '<div class="task-item" data-status="' + task.status + '" data-feature="' + task.feature_name + '">' +
            '<div class="task-header" onclick="toggleTaskDetails(this)">' +
            '<span class="task-status-dot" style="background: ' + statusColor + ';"></span>' +
            '<span class="task-name" title="' + task.name + '">' + task.name + '</span>' +
            '<span class="task-expand-icon ' + expandClass + '">' + expandIcon + '</span>' +
            '</div>' +
            '<div class="task-details" style="display: ' + displayStyle + ';">' +
            detailsHtml +
            '</div>' +
            '</div>';
    });

    taskListDiv.innerHTML = taskItemsHtml;
}

// Initial fetch
fetchGraph();
fetchTasks();

// Auto-refresh every 3 seconds
setInterval(() => {
    fetchGraph();
    fetchTasks();
}, 3000);

// Handle window resize
window.addEventListener('resize', () => {
    const newWidth = window.innerWidth;
    const newHeight = window.innerHeight;

    svg.attr('width', newWidth).attr('height', newHeight);

    simulation.force('center', d3.forceCenter(newWidth / 2, newHeight / 2));
    simulation.alpha(0.3).restart();
});
