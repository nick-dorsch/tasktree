-- Features table to track which features are available/enabled
CREATE TABLE IF NOT EXISTS features (
  name VARCHAR(55) PRIMARY KEY,
  description TEXT,
  enabled BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS set_features_updated_at
AFTER UPDATE ON features
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE features
  SET updated_at = CURRENT_TIMESTAMP
  WHERE name = NEW.name;
END;

-- Seed the default feature (required for basic operation)
INSERT OR IGNORE INTO features (name, description, enabled) VALUES
('default', 'Default feature set for basic task management', TRUE);
