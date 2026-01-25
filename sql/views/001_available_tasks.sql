-- View for tasks whose dependencies are all completed
DROP VIEW IF EXISTS v_available_tasks;

CREATE VIEW v_available_tasks AS
SELECT t.*
FROM tasks t
WHERE t.status = 'pending'  -- Only tasks that aren't already completed
  AND NOT EXISTS (
    -- Check for any uncompleted dependencies
    SELECT 1
    FROM dependencies d
    JOIN tasks dep_task ON d.depends_on_task_name = dep_task.name
    WHERE d.task_name = t.name
      AND dep_task.status != 'completed'
  )
  AND (
    -- Include tasks with no dependencies
    NOT EXISTS (
      SELECT 1 FROM dependencies d WHERE d.task_name = t.name
    )
    OR
    -- Or tasks that exist in dependencies table
    EXISTS (
      SELECT 1 FROM dependencies d WHERE d.task_name = t.name
    )
  )
ORDER BY t.priority DESC, t.created_at ASC;