-- Dependencies are edges in the graph between tasks and other tasks they depend on
CREATE TABLE IF NOT EXISTS dependencies (
  task_name TEXT NOT NULL REFERENCES tasks(name),
  depends_on_task_name TEXT NOT NULL REFERENCES tasks(name),
  PRIMARY KEY (task_name, depends_on_task_name),
  CHECK (task_name != depends_on_task_name) -- Prevent self-dependencies
);

-- Trigger to prevent circular dependencies
CREATE TRIGGER IF NOT EXISTS prevent_circular_dependencies
BEFORE INSERT ON dependencies
BEGIN
  -- Check if this would create a circular dependency by recursively checking if
  -- depends_on_task_name already depends on task_name
  SELECT CASE
    WHEN EXISTS (
      WITH RECURSIVE dependency_chain AS (
        -- Start with the task we're trying to depend on
        SELECT depends_on_task_name as task_name, 1 as depth
        FROM dependencies
        WHERE task_name = NEW.depends_on_task_name
        
        UNION ALL
        
        -- Recursively follow all dependencies
        SELECT d.depends_on_task_name, dc.depth + 1
        FROM dependencies d
        JOIN dependency_chain dc ON d.task_name = dc.task_name
        WHERE dc.depth < 10 -- Prevent infinite recursion
      )
      SELECT 1 FROM dependency_chain WHERE task_name = NEW.task_name
    ) THEN
      RAISE(ABORT, 'Circular dependencies are not allowed!')
    END;
END;
