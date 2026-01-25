-- View that outputs the task dependency graph in DOT format (Graphviz)
-- Can be piped to graph-easy for ASCII visualization or to dot for image generation
-- Available tasks (all dependencies completed) are highlighted with green color
DROP VIEW IF EXISTS v_graph_dot;

CREATE VIEW v_graph_dot AS
SELECT 
    'digraph TaskTree {' || CHAR(10) ||
    '  rankdir=TB;' || CHAR(10) ||
    '  node [shape=box, style=rounded];' || CHAR(10) ||
    CHAR(10) ||
    -- Add all nodes with highlighting for available tasks
    (
        SELECT GROUP_CONCAT(
            '  "' || t.name || '"' || 
            CASE 
                WHEN t.name IN (SELECT name FROM v_available_tasks)
                THEN ' [style="rounded,filled", fillcolor=lightgreen]'
                ELSE ''
            END || ';',
            CHAR(10)
        )
        FROM tasks t
    ) || CHAR(10) ||
    CHAR(10) ||
    -- Add all edges (from -> to means from depends on to)
    (
        SELECT GROUP_CONCAT(
            '  "' || d.depends_on_task_name || '" -> "' || d.task_name || '";',
            CHAR(10)
        )
        FROM dependencies d
    ) || CHAR(10) ||
    '}' as dot_graph;
