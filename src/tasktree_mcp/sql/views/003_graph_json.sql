-- View that outputs the entire task graph as a JSON structure
-- Format: {"nodes": [...], "edges": [...]}
-- Each node includes an is_available flag indicating if all dependencies are complete
DROP VIEW IF EXISTS v_graph_json;

CREATE VIEW v_graph_json AS
SELECT json_object(
    'nodes', (
        SELECT json_group_array(
            json_object(
                'name', t.name,
                'description', t.description,
                'status', t.status,
                'priority', t.priority,
                'completed_at', t.completed_at,
                'started_at', t.started_at,
                'completion_minutes', CASE 
                    WHEN t.started_at IS NULL OR t.completed_at IS NULL THEN NULL
                    ELSE CAST((julianday(t.completed_at) - julianday(t.started_at)) * 24 * 60 AS INTEGER)
                END,
                'is_available', CASE WHEN t.name IN (SELECT name FROM v_available_tasks) THEN 1 ELSE 0 END
            )
        )
        FROM tasks t
    ),
    'edges', (
        SELECT json_group_array(
            json_object(
                'from', d.task_name,
                'to', d.depends_on_task_name
            )
        )
        FROM dependencies d
    )
) as graph_json;
