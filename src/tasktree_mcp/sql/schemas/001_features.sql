-- Features table to track which features are available/enabled
CREATE TABLE IF NOT EXISTS features (
  id CHAR(32) PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  name VARCHAR(55) NOT NULL UNIQUE,
  description TEXT NOT NULL,
  specification TEXT NOT NULL,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS set_features_updated_at
AFTER UPDATE ON features
WHEN NEW.updated_at = OLD.updated_at
BEGIN
  UPDATE features
  SET updated_at = CURRENT_TIMESTAMP
  WHERE id = NEW.id;
END;

-- Seed the default feature (required for basic operation)
INSERT OR IGNORE INTO features (name, description, specification) VALUES
(
  'misc',
  'Default feature for uncategorized tasks',
  'Use this feature in cases where a task is minimal and does not require a feature, such as minor hotfixes, tweaks etc.'
);
