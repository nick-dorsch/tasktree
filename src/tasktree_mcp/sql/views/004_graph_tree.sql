-- View that outputs the task dependency graph as an ASCII tree
-- Available tasks (all dependencies completed) are marked with [✓]
DROP VIEW IF EXISTS v_graph_tree;

CREATE VIEW v_graph_tree AS
WITH RECURSIVE task_tree AS (
    -- Root tasks (no dependencies)
    SELECT 
        t.name,
        t.status,
        0 as level,
        CAST(t.name AS TEXT) as path,
        '' as prefix
    FROM tasks t
    WHERE NOT EXISTS (
        SELECT 1 FROM dependencies d 
        WHERE d.task_name = t.name
    )
    
    UNION ALL
    
    -- Dependent tasks (task depends on parent)
    SELECT 
        t.name,
        t.status,
        tt.level + 1,
        tt.path || '->' || t.name,
        tt.prefix || '  '
    FROM tasks t
    JOIN dependencies d ON t.name = d.task_name
    JOIN task_tree tt ON d.depends_on_task_name = tt.name
)
SELECT 
    prefix || '└─ ' || name || 
    CASE 
        WHEN name IN (SELECT name FROM v_available_tasks)
        THEN ' [✓]'
        ELSE ''
    END as tree_line,
    level,
    path
FROM task_tree
ORDER BY path;
