-- View that outputs the task dependency graph as an ASCII tree
-- Available tasks (all dependencies completed) are marked with [✓]
DROP VIEW IF EXISTS v_graph_tree;

CREATE VIEW v_graph_tree AS
WITH RECURSIVE task_tree AS (
    -- Root tasks (no dependencies)
    SELECT 
        t.id,
        t.name,
        t.status,
        0 as level,
        CAST(t.id AS TEXT) as path,
        '' as prefix
    FROM tasks t
    WHERE NOT EXISTS (
        SELECT 1 FROM dependencies d 
        WHERE d.task_id = t.id
    )
    
    UNION ALL
    
    -- Dependent tasks (task depends on parent)
    SELECT 
        t.id,
        t.name,
        t.status,
        tt.level + 1,
        tt.path || '->' || t.id,
        tt.prefix || '  '
    FROM tasks t
    JOIN dependencies d ON t.id = d.task_id
    JOIN task_tree tt ON d.depends_on_task_id = tt.id
)
SELECT 
    prefix || '└─ ' || name || 
    CASE 
        WHEN id IN (SELECT id FROM v_available_tasks)
        THEN ' [✓]'
        ELSE ''
    END as tree_line,
    level,
    path
FROM task_tree
ORDER BY path;
