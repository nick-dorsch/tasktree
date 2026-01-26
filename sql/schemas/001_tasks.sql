-- Each task is a node in the dependency graph
CREATE TABLE IF NOT EXISTS tasks (
  name VARCHAR(55) PRIMARY KEY,
  description TEXT NOT NULL,
  details TEXT,

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
  completed_at TIMESTAMP
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

-- Trigger to clear started_at when status changes from 'in_progress' to something else
CREATE TRIGGER IF NOT EXISTS clear_started_at
AFTER UPDATE ON tasks
WHEN NEW.status != 'in_progress' AND OLD.status = 'in_progress'
BEGIN
    UPDATE tasks SET started_at = NULL WHERE name = NEW.name;
END;

-- Trigger to clear completed_at when status changes from 'completed' to something else
CREATE TRIGGER IF NOT EXISTS clear_completed_at
AFTER UPDATE ON tasks
WHEN NEW.status != 'completed' AND OLD.status = 'completed'
BEGIN
    UPDATE tasks SET completed_at = NULL WHERE name = NEW.name;
END;
