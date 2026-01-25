-- Recursive view that computes the dependency tree with levels and paths
CREATE VIEW IF NOT EXISTS v_dependency_tree AS
WITH RECURSIVE task_tree AS (
    -- Root tasks (no dependencies)
    SELECT 
        t.name,
        t.description,
        t.status,
        t.priority,
        t.completed_at,
        0 as level,
        CAST(t.name AS TEXT) as path,
        CAST(NULL AS TEXT) as parent_name
    FROM tasks t
    WHERE NOT EXISTS (
        SELECT 1 FROM dependencies d 
        WHERE d.task_name = t.name
    )
    
    UNION ALL
    
    -- Dependent tasks (task depends on parent)
    SELECT 
        t.name,
        t.description,
        t.status,
        t.priority,
        t.completed_at,
        tt.level + 1,
        tt.path || '->' || t.name,
        d.depends_on_task_name as parent_name
    FROM tasks t
    JOIN dependencies d ON t.name = d.task_name
    JOIN task_tree tt ON d.depends_on_task_name = tt.name
)
SELECT 
    name,
    description,
    status,
    priority,
    completed_at,
    level,
    path,
    parent_name
FROM task_tree
ORDER BY path;
