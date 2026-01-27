-- View that outputs the task dependency graph in DOT format (Graphviz)
-- Can be piped to graph-easy for ASCII visualization or to dot for image generation
-- Tasks are colored by status: pending=blue, in_progress=yellow, completed=green
-- Available tasks (pending with all dependencies completed) have a thicker border
DROP VIEW IF EXISTS v_graph_dot;

CREATE VIEW v_graph_dot AS
SELECT 
    'digraph TaskTree {' || CHAR(10) ||
    '  rankdir=TB;' || CHAR(10) ||
    '  node [shape=box, style=rounded];' || CHAR(10) ||
    CHAR(10) ||
    -- Add all nodes with status-based color coding
    COALESCE(
        (
            SELECT GROUP_CONCAT(
                '  "' || t.name || '" [' ||
                'style="rounded,filled"' ||
                CASE t.status
                    WHEN 'pending' THEN ', fillcolor=lightblue'
                    WHEN 'in_progress' THEN ', fillcolor=yellow'
                    WHEN 'completed' THEN ', fillcolor=lightgreen'
                    WHEN 'blocked' THEN ', fillcolor=lightgray'
                    ELSE ', fillcolor=white'
                END ||
                -- Add thicker border for available tasks
                CASE 
                    WHEN t.id IN (SELECT id FROM v_available_tasks)
                    THEN ', penwidth=3'
                    ELSE ''
                END ||
                '];',
                CHAR(10)
            )
            FROM tasks t
        ),
        ''
    ) || CHAR(10) ||
    CHAR(10) ||
    -- Add all edges (from -> to means from depends on to)
    COALESCE(
        (
            SELECT GROUP_CONCAT(
                '  "' || parent.name || '" -> "' || child.name || '";',
                CHAR(10)
            )
            FROM dependencies d
            JOIN tasks parent ON parent.id = d.depends_on_task_id
            JOIN tasks child ON child.id = d.task_id
        ),
        ''
    ) || CHAR(10) ||
    '}' as dot_graph;
