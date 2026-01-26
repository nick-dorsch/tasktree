-- Each task is a node in the dependency graph
CREATE TABLE IF NOT EXISTS tasks (
  name VARCHAR(55) PRIMARY KEY,
  description TEXT NOT NULL,
  details TEXT,
  feature_name VARCHAR(55) NOT NULL DEFAULT 'default',

  priority INTEGER DEFAULT 0 CHECK(priority >= 0 AND priority <= 10),
  status TEXT DEFAULT 'pending' CHECK(
    status IN (
      'pending',
      'in_progress',
      'completed',
      'blocked'
    )
  ),

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,

  FOREIGN KEY (feature_name) REFERENCES features(name)
);

-- Triggers to automatically set timestamps based on status changes

-- Trigger to set started_at when status becomes 'in_progress'
CREATE TRIGGER IF NOT EXISTS set_started_at
AFTER UPDATE ON tasks
WHEN NEW.status = 'in_progress' AND OLD.status != 'in_progress'
BEGIN
    UPDATE tasks SET started_at = CURRENT_TIMESTAMP WHERE name = NEW.name;
END;

-- Trigger to set completed_at when status becomes 'completed'
CREATE TRIGGER IF NOT EXISTS set_completed_at
AFTER UPDATE ON tasks
WHEN NEW.status = 'completed' AND OLD.status != 'completed'
BEGIN
    UPDATE tasks SET completed_at = CURRENT_TIMESTAMP WHERE name = NEW.name;
END;
