-- Features table to track which features are available/enabled
CREATE TABLE IF NOT EXISTS features (
  name VARCHAR(55) PRIMARY KEY,
  description TEXT,
  enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed the default feature (required for basic operation)
INSERT OR IGNORE INTO features (name, description, enabled) VALUES
('default', 'Default feature set for basic task management', TRUE);
