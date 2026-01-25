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
                WHEN t.id IN (SELECT id FROM v_available_tasks)
                THEN ' [style="rounded,filled", fillcolor=lightgreen]'
                ELSE ''
            END || ';',
            CHAR(10)
        )
        FROM tasks t
    ) || CHAR(10) ||
    CHAR(10) ||
    -- Add all edges (source -> target means target depends on source)
    (
        SELECT GROUP_CONCAT(
            '  "' || t2.name || '" -> "' || t1.name || '";',
            CHAR(10)
        )
        FROM dependencies d
        JOIN tasks t1 ON d.task_id = t1.id
        JOIN tasks t2 ON d.depends_on_task_id = t2.id
    ) || CHAR(10) ||
    '}' as dot_graph;
