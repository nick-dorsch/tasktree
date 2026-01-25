-- View that outputs the entire task graph as a JSON structure
-- Format: {"nodes": [...], "edges": [...]}
CREATE VIEW IF NOT EXISTS v_graph_json AS
SELECT json_object(
    'nodes', (
        SELECT json_group_array(
            json_object(
                'id', t.id,
                'name', t.name,
                'status', t.status,
                'priority', t.priority,
                'completed_at', t.completed_at
            )
        )
        FROM tasks t
    ),
    'edges', (
        SELECT json_group_array(
            json_object(
                'source', d.task_id,
                'target', d.depends_on_task_id,
                'source_name', t1.name,
                'target_name', t2.name
            )
        )
        FROM dependencies d
        JOIN tasks t1 ON d.task_id = t1.id
        JOIN tasks t2 ON d.depends_on_task_id = t2.id
    )
) as graph_json;
