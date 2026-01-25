-- Each task is a node in the dependency graph
CREATE TABLE IF NOT EXISTS tasks (
  name VARCHAR(55) PRIMARY KEY,
  description TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  priority INTEGER DEFAULT 0,
  details TEXT,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);
