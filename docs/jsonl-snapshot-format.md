# JSONL Snapshot Format

This document defines the canonical JSONL snapshot schema for TaskTree.

## Overview

- One JSON object per line (JSONL).
- UTF-8 encoding, with ASCII-safe output via JSON serialization settings.
- Deterministic ordering to make snapshots diff-friendly.
- Only four record types: `meta`, `feature`, `task`, `dependency`.

## Record Types and Fields

All records include a `record_type` field set to one of: `meta`, `feature`, `task`, `dependency`.

### meta

Required fields:

- `record_type`: "meta"
- `schema_version`: string (e.g., "1")
- `generated_at`: timestamp string (see Timestamp Handling)

Optional fields:

- `tasktree_version`: string
- `source`: string (e.g., "sqlite")

### feature

Required fields:

- `record_type`: "feature"
- `name`: string
- `description`: string or null
- `enabled`: boolean
- `created_at`: timestamp string

### task

Required fields:

- `record_type`: "task"
- `name`: string
- `description`: string
- `details`: string or null
- `feature_name`: string or null
- `priority`: integer
- `status`: string
- `created_at`: timestamp string
- `updated_at`: timestamp string
- `started_at`: timestamp string or null
- `completed_at`: timestamp string or null

### dependency

Required fields:

- `record_type`: "dependency"
- `task_name`: string
- `depends_on_task_name`: string

## Deterministic Ordering

The snapshot writer must emit records in this exact order:

1. A single `meta` record
2. All `feature` records, sorted by `name` ascending
3. All `task` records, sorted by `name` ascending
4. All `dependency` records, sorted by `task_name` ascending, then `depends_on_task_name` ascending

No additional grouping or filtering is permitted in the canonical format.

## JSON Serialization Settings

To ensure deterministic output, snapshots must be serialized with:

- `sort_keys = true`
- `separators = (",", ":")`
- `ensure_ascii = true`

Do not pretty-print or indent. Each line must be a single JSON object followed by `\n`.

## Timestamp Handling

- Use the timestamp string values as stored in SQLite.
- Do not reformat or apply timezone conversions.
- Missing timestamps must be serialized as `null`.

## Versioning

- `schema_version` starts at `"1"`.
- Backward-incompatible changes require a new `schema_version` value.
