-- Dependencies are edges in the graph between tasks and other tasks they depend on
CREATE TABLE IF NOT EXISTS dependencies (
  task_id INTEGER NOT NULL REFERENCES tasks(id),
  depends_on_task_id INTEGER NOT NULL REFERENCES tasks(id),
  PRIMARY KEY (task_id, depends_on_task_id),
  CHECK (task_id != depends_on_task_id) -- Prevent self-dependencies
);

-- Trigger to prevent circular dependencies
CREATE TRIGGER IF NOT EXISTS prevent_circular_dependencies
BEFORE INSERT ON dependencies
BEGIN
  -- Check if this would create a circular dependency by recursively checking if
  -- depends_on_task_id already depends on task_id
  SELECT CASE
    WHEN EXISTS (
      WITH RECURSIVE dependency_chain AS (
        -- Start with the task we're trying to depend on
        SELECT depends_on_task_id as task_id, 1 as depth
        FROM dependencies
        WHERE task_id = NEW.depends_on_task_id
        
        UNION ALL
        
        -- Recursively follow all dependencies
        SELECT d.depends_on_task_id, dc.depth + 1
        FROM dependencies d
        JOIN dependency_chain dc ON d.task_id = dc.task_id
        WHERE dc.depth < 10 -- Prevent infinite recursion
      )
      SELECT 1 FROM dependency_chain WHERE task_id = NEW.task_id
    ) THEN
      RAISE(ABORT, 'Circular dependencies are not allowed!')
    END;
END;
