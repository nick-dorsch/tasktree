-- View that emits deterministic JSONL snapshot lines using JSON1
-- Columns:
--   record_order: ordering bucket (meta=0, feature=1, task=2, dependency=3)
--   sort_name: primary sort key within bucket
--   sort_secondary: secondary sort key within bucket
--   json_line: JSON text for the snapshot line
DROP VIEW IF EXISTS v_snapshot_jsonl_lines;

CREATE VIEW v_snapshot_jsonl_lines AS
WITH meta AS (
  SELECT CURRENT_TIMESTAMP AS generated_at
)
SELECT
  0 AS record_order,
  '' AS sort_name,
  '' AS sort_secondary,
  json_object(
    'record_type', 'meta',
    'schema_version', '1',
    'generated_at', meta.generated_at,
    'source', 'sqlite'
  ) AS json_line
FROM meta

UNION ALL

SELECT
  1 AS record_order,
  f.name AS sort_name,
  '' AS sort_secondary,
  json_object(
    'record_type', 'feature',
    'name', f.name,
    'description', f.description,
    'enabled', json(CASE WHEN f.enabled THEN 'true' ELSE 'false' END),
    'created_at', f.created_at,
    'updated_at', f.updated_at
  ) AS json_line
FROM features f

UNION ALL

SELECT
  2 AS record_order,
  t.name AS sort_name,
  '' AS sort_secondary,
  json_object(
    'record_type', 'task',
    'name', t.name,
    'description', t.description,
    'details', t.details,
    'feature_name', t.feature_name,
    'tests_required', json(CASE WHEN t.tests_required THEN 'true' ELSE 'false' END),
    'priority', t.priority,
    'status', t.status,
    'created_at', t.created_at,
    'updated_at', t.updated_at,
    'started_at', t.started_at,
    'completed_at', t.completed_at
  ) AS json_line
FROM tasks t

UNION ALL

SELECT
  3 AS record_order,
  d.task_name AS sort_name,
  d.depends_on_task_name AS sort_secondary,
  json_object(
    'record_type', 'dependency',
    'task_name', d.task_name,
    'depends_on_task_name', d.depends_on_task_name
  ) AS json_line
FROM dependencies d;
