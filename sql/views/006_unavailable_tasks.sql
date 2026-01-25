-- View for tasks that are not yet available (have uncompleted dependencies)
DROP VIEW IF EXISTS v_unavailable_tasks;

CREATE VIEW v_unavailable_tasks AS
SELECT t.*
FROM tasks t
WHERE t.status = 'pending'  -- Only pending tasks
  AND EXISTS (
    -- Check for any uncompleted dependencies
    SELECT 1
    FROM dependencies d
    JOIN tasks dep_task ON d.depends_on_task_name = dep_task.name
    WHERE d.task_name = t.name
      AND dep_task.status != 'complete'
  )
ORDER BY t.priority DESC, t.created_at ASC;
