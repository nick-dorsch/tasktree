window.tasktreeGraphServerAssetsLoaded = true;

// Feature list toggle functionality
function toggleFeatureTasks(headerElement) {
    const featureGroup = headerElement.parentElement;
    const tasksContainer = featureGroup.querySelector('.feature-tasks');
    const isExpanding = tasksContainer.style.display === 'none';

    if (isExpanding) {
        tasksContainer.style.display = 'block';
        headerElement.classList.add('expanded');
    } else {
        tasksContainer.style.display = 'none';
        headerElement.classList.remove('expanded');
    }
}

// Task list toggle functionality
function toggleTaskDetails(headerElement) {
    const taskItem = headerElement.parentElement;
    const detailsDiv = taskItem.querySelector('.task-details');
    const expandIcon = headerElement.querySelector('.task-expand-icon');

    // Check if this task is currently expanded
    const isExpanding = detailsDiv.style.display === 'none';

    // Close all other expanded tasks first
    document.querySelectorAll('.task-details').forEach(details => {
        details.style.display = 'none';
    });
    document.querySelectorAll('.task-expand-icon').forEach(icon => {
        icon.classList.remove('expanded');
    });
    document.querySelectorAll('.task-item').forEach(item => {
        item.removeAttribute('data-expanded');
    });

    if (isExpanding) {
        // Now expand this task
        detailsDiv.style.display = 'block';
        expandIcon.classList.add('expanded');
        taskItem.setAttribute('data-expanded', 'true');
    }
}

// Configuration
const API_ENDPOINT = '/api/graph';
const TASKS_ENDPOINT = '/api/tasks';
const WIDTH = window.innerWidth;
const HEIGHT = window.innerHeight;

// Status colors
const STATUS_COLORS = {
    pending: '#6366f1',
    in_progress: '#fff000',
    completed: '#22d3ee',
    blocked: '#f43f5e',
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
    .attr('fill', '#4B3D61');

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
    .force('link', d3.forceLink().id(d => d.id).distance(150))
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
        <div style="margin-bottom: 8px; border-bottom: 1px solid rgba(157, 80, 187, 0.2); padding-bottom: 4px;">
            <span class="tooltip-label" style="color: #ffd700;">Task:</span> 
            <span style="font-weight: 800; color: #ede9fe;">${d.name}</span>
        </div>
        <div><span class="tooltip-label">Description:</span> <span style="color: #c4b5fd;">${d.description || 'N/A'}</span></div>
        <div><span class="tooltip-label">Status:</span> <span style="color: ${STATUS_COLORS[d.status]};">${d.status}</span></div>
        <div><span class="tooltip-label">Priority:</span> <span style="color: #ddd6fe;">${d.priority}</span></div>
        <div><span class="tooltip-label">Available:</span> <span style="color: ${d.is_available ? '#ff7e00' : '#6b7280'};">${d.is_available ? 'Yes' : 'No'}</span></div>
        ${d.started_at ? `<div><span class="tooltip-label">Started:</span> <span style="color: #ddd6fe;">${d.started_at}</span></div>` : ''}
        ${d.completed_at ? `<div><span class="tooltip-label">Completed:</span> <span style="color: #ddd6fe;">${d.completed_at}</span></div>` : ''}
        ${d.completion_minutes !== null && d.completion_minutes !== undefined ? `<div><span class="tooltip-label">Duration:</span> <span style="color: #ddd6fe;">${d.completion_minutes} min</span></div>` : ''}
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
    if (d.is_available) return '#ff7e00';
    return STATUS_COLORS[d.status] || '#999';
}

function getNodeRadius(d) {
    if (d.status === 'completed') return 10;
    return 8 + (d.priority / 10) * 22;
}

function getNodeStroke(d) {
    return 'none';
}

function getNodeStrokeWidth(d) {
    return 0;
}

function updateGraph(graphData) {
    // Update loading state
    d3.select('#loading').style('display', 'none');

    // Store current positions BEFORE data update
    const positionCache = new Map();
    if (node) {
        node.each(d => {
            positionCache.set(d.id, {
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
            const source = typeof d.source === 'object' ? d.source.id : d.source;
            const target = typeof d.target === 'object' ? d.target.id : d.target;
            return `${source}-${target}`;
        });

    link.exit().remove();

    const linkEnter = link.enter()
        .append('path')
        .attr('class', 'link');

    link = linkEnter.merge(link);

    // Update nodes
    node = nodeGroup.selectAll('.node')
        .data(nodes, d => d.id);

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
        const cached = positionCache.get(d.id);
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
        .attr('data-status', d => d.status)
        .style('--base-radius', d => getNodeRadius(d) + 'px')
        .attr('filter', d => {
            if (d.is_available) return 'url(#glow-available)';
            if (d.status === 'in_progress') return 'url(#glow-in-progress)';
            if (d.status === 'pending') return null;
            return 'url(#glow-status)';
        });

    // Update labels
    label = labelGroup.selectAll('.node-label')
        .data(nodes, d => d.id);

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

    label.attr('x', d => d.x + getNodeRadius(d) * 0.7)
        .attr('y', d => d.y - getNodeRadius(d) * 0.7);
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
        taskListDiv.innerHTML = '<div style="padding: 12px; color: #7c3aed; font-size: 12px;">No tasks available</div>';
        return;
    }

    // Store currently expanded task names
    const expandedTasks = new Set();
    document.querySelectorAll('.task-item[data-expanded="true"]').forEach((taskItem) => {
        const taskName = taskItem.getAttribute('data-task-name');
        if (taskName) {
            expandedTasks.add(taskName);
        }
    });
    document.querySelectorAll('.task-details').forEach((details) => {
        if (details.style.display === 'block') {
            const taskItem = details.parentElement;
            const taskName = taskItem.querySelector('.task-name').textContent;
            expandedTasks.add(taskName);
        }
    });

    // Store currently expanded features
    const expandedFeatures = new Set();
    document.querySelectorAll('.feature-group').forEach((group) => {
        const tasksContainer = group.querySelector('.feature-tasks');
        if (tasksContainer && tasksContainer.style.display === 'block') {
            const featureName = group.getAttribute('data-feature');
            if (featureName) {
                expandedFeatures.add(featureName);
            }
        }
    });

    // Status colors
    const statusColors = {
        pending: '#6366f1',
        in_progress: '#fff000',
        completed: '#22d3ee',
        blocked: '#f43f5e',
    };

    // Group tasks by feature
    const tasksByFeature = new Map();
    tasks.forEach(task => {
        if (!tasksByFeature.has(task.feature_name)) {
            tasksByFeature.set(task.feature_name, []);
        }
        tasksByFeature.get(task.feature_name).push(task);
    });

    const sortedFeatures = Array.from(tasksByFeature.keys()).sort((a, b) =>
        a.localeCompare(b)
    );

    // Build feature groups HTML
    let taskItemsHtml = '';

    sortedFeatures.forEach(featureName => {
        const featureTasks = tasksByFeature.get(featureName) || [];
        const isExpanded = expandedFeatures.has(featureName);
        const featureDisplay = isExpanded ? 'block' : 'none';
        const featureClass = isExpanded ? 'expanded' : '';
        const featureColor = featureTasks.length > 0 && featureTasks[0].feature_color ? featureTasks[0].feature_color : '#ccc';

        let featureTasksHtml = '';

        featureTasks.forEach(task => {
            const statusColor = statusColors[task.status] || '#999';

            let detailsHtml = '<div class="task-details-row"><span class="task-details-label">Status:</span> ' + task.status + '</div>' +
                '<div class="task-details-row"><span class="task-details-label">Priority:</span> ' + task.priority + '</div>' +
                '<div class="task-details-row"><span class="task-details-label">Description:</span>' +
                '<div class="task-details-value">' + (task.description || 'None') + '</div></div>';

            if (task.specification && task.specification !== task.description) {
                detailsHtml += '<div class="task-details-row"><span class="task-details-label">Details:</span>' +
                    '<div class="task-details-value">' + task.specification + '</div></div>';
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
            const expandedAttr = shouldExpand ? ' data-expanded="true"' : '';

            featureTasksHtml += '<div class="task-item" data-status="' + task.status + '" data-feature="' + task.feature_name + '" data-task-name="' + task.name + '"' + expandedAttr + ' style="background-color: ' + featureColor + '1A;">' +
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

        const completedTasks = featureTasks.filter(t => t.status === 'completed').length;
        const totalTasks = featureTasks.length;
        const allCompleted = completedTasks === totalTasks && totalTasks > 0;
        const countStyle = allCompleted ? ' style="color: #22d3ee; font-weight: bold;"' : '';

        taskItemsHtml += '<div class="feature-group" data-feature="' + featureName + '">' +
            '<div class="feature-header ' + featureClass + '" onclick="toggleFeatureTasks(this)" style="border-left: 4px solid ' + featureColor + '; background-color: ' + featureColor + '1A;">' +
            '<div class="feature-main-info">' +
            '<span class="feature-chevron">▶</span>' +
            '<span class="feature-name" title="' + featureName + '">' + featureName + '</span>' +
            '<span class="feature-count"' + countStyle + '>' + completedTasks + ' / ' + totalTasks + '</span>' +
            '</div>' +
            '</div>' +
            '<div class="feature-tasks" style="display: ' + featureDisplay + ';">' +
            featureTasksHtml +
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
