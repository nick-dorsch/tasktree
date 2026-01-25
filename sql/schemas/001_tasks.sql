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
      'complete',
      'blocked'
    )
  ),

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);
