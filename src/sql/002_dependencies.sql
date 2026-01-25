-- Dependencies are edges in the graph between tasks and other tasks they depend on
-- From task: the source of the dependency
-- To task: the task that is dependent on it
CREATE TABLE IF NOT EXISTS dependencies (
  to_task_id INTEGER NOT NULL REFERENCES tasks(id),
  from_task_id INTEGER NOT NULL REFERENCES tasks(id),
  PRIMARY KEY (to_task_id, from_task_id)
);
