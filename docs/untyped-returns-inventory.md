# Inventory of Untyped Returns (`Dict[str, Any]`)

This document tracks all MCP tools and repository methods that return `Dict[str, Any]` instead of properly typed Pydantic models. This inventory is part of the `mcp-typed-returns` feature to improve type safety.

**Generated:** 2026-01-26

---

## Summary

| Category | Count | Methods/Tools |
|----------|-------|---------------|
| MCP Tools (Single) | 6 | `get_task`, `add_task`, `update_task`, `start_task`, `complete_task`, `add_dependency`, `add_feature` |
| MCP Tools (List) | 4 | `list_tasks`, `list_dependencies`, `get_available_tasks`, `list_features` |
| Repository Methods (Single) | 6 | `TaskRepository.get_task`, `TaskRepository.add_task`, `TaskRepository.update_task`, `TaskRepository.complete_task`, `FeatureRepository.add_feature`, `DependencyRepository.add_dependency` |
| Repository Methods (List) | 4 | `TaskRepository.list_tasks`, `DependencyRepository.list_dependencies`, `DependencyRepository.get_available_tasks`, `FeatureRepository.list_features` |

---

## MCP Tools with Untyped Returns

### Task Tools (`tools.py:36-240`)

#### 1. `list_tasks` (Line 40-66)
- **Return Type:** `List[Dict[str, Any]]`
- **Repository Call:** `TaskRepository.list_tasks()`
- **Purpose:** List tasks with optional filtering by status, priority_min, feature_name
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_list_tasks.py`
  - `tests/test_repository_with_fixture.py::test_task_repository_list_tasks`

#### 2. `get_task` (Line 69-81)
- **Return Type:** `Optional[Dict[str, Any]]`
- **Repository Call:** `TaskRepository.get_task()`
- **Purpose:** Get a specific task by name
- **Callers:** External MCP clients, called internally in `add_task` to validate dependencies (line 122)
- **Tests:**
  - `tests/test_get_task.py`
  - `tests/test_repository_with_fixture.py::test_task_repository_get_task`

#### 3. `add_task` (Line 84-154)
- **Return Type:** `Dict[str, Any]`
- **Repository Call:** `TaskRepository.add_task()`
- **Purpose:** Add a new task with optional dependencies
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_add_task.py`
  - `tests/test_repository_with_fixture.py::test_task_repository_add_task`

#### 4. `update_task` (Line 157-195)
- **Return Type:** `Optional[Dict[str, Any]]`
- **Repository Call:** `TaskRepository.update_task()`
- **Purpose:** Update an existing task's fields
- **Callers:** External MCP clients, called by `start_task` and `complete_task`
- **Tests:**
  - `tests/test_update_task.py`
  - `tests/test_repository_with_fixture.py::test_task_repository_update_task`

#### 5. `start_task` (Line 213-224)
- **Return Type:** `Optional[Dict[str, Any]]`
- **Repository Call:** `TaskRepository.update_task()`
- **Purpose:** Set task status to 'in_progress'
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_start_task.py`

#### 6. `complete_task` (Line 227-239)
- **Return Type:** `Optional[Dict[str, Any]]`
- **Repository Call:** `TaskRepository.complete_task()`
- **Purpose:** Set task status to 'completed'
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_complete_task.py`

### Dependency Tools (`tools.py:242-319`)

#### 7. `list_dependencies` (Line 246-257)
- **Return Type:** `List[Dict[str, Any]]`
- **Repository Call:** `DependencyRepository.list_dependencies()`
- **Purpose:** List all dependencies or filter by task_name
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_list_dependencies.py`
  - `tests/test_repository_with_fixture.py::test_dependency_repository_list_dependencies`

#### 8. `add_dependency` (Line 260-281)
- **Return Type:** `Dict[str, Any]`
- **Repository Call:** `DependencyRepository.add_dependency()`
- **Purpose:** Create a dependency relationship between tasks
- **Callers:** External MCP clients, called in `add_task` when dependencies provided (line 149)
- **Tests:**
  - `tests/test_add_dependency.py`
  - `tests/test_repository_with_fixture.py::test_dependency_repository_add_dependency`

#### 9. `get_available_tasks` (Line 308-319)
- **Return Type:** `List[Dict[str, Any]]`
- **Repository Call:** `DependencyRepository.get_available_tasks()`
- **Purpose:** Get pending tasks with all dependencies completed
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_get_available_tasks.py`
  - `tests/test_repository_with_fixture.py::test_dependency_repository_get_available_tasks`

### Feature Tools (`tools.py:322-374`)

#### 10. `add_feature` (Line 326-360)
- **Return Type:** `Dict[str, Any]`
- **Repository Call:** `FeatureRepository.add_feature()`
- **Purpose:** Add a new feature
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_features_table.py`

#### 11. `list_features` (Line 363-374)
- **Return Type:** `List[Dict[str, Any]]`
- **Repository Call:** `FeatureRepository.list_features()`
- **Purpose:** List features with optional enabled filter
- **Callers:** External MCP clients
- **Tests:**
  - `tests/test_features_table.py`

---

## Repository Methods with Untyped Returns

### TaskRepository (`database.py:27-192`)

#### 1. `list_tasks` (Line 31-61)
- **Return Type:** `List[Dict[str, Any]]`
- **Data Source:** `SELECT * FROM tasks` with optional filters
- **Fields Returned:** name, description, details, feature_name, priority, status, created_at, updated_at, started_at, completed_at
- **Called By:** `tools.list_tasks()`
- **Tests:** Same as MCP tool `list_tasks`

#### 2. `get_task` (Line 64-73)
- **Return Type:** `Optional[Dict[str, Any]]`
- **Data Source:** `SELECT * FROM tasks WHERE name = ?`
- **Fields Returned:** All task fields
- **Called By:** 
  - `tools.get_task()`
  - `tools.add_task()` (line 122, for dependency validation)
  - `TaskRepository.update_task()` (line 145, to check existence and return updated task)
- **Tests:** Same as MCP tool `get_task`

#### 3. `add_task` (Line 76-107)
- **Return Type:** `Dict[str, Any]`
- **Data Source:** `INSERT INTO tasks` then `SELECT * FROM tasks WHERE name = ?`
- **Fields Returned:** All task fields
- **Called By:** `tools.add_task()`
- **Tests:** Same as MCP tool `add_task`

#### 4. `update_task` (Line 110-153)
- **Return Type:** `Optional[Dict[str, Any]]`
- **Data Source:** `UPDATE tasks` then calls `get_task()`
- **Fields Returned:** All task fields via `get_task()`
- **Called By:** 
  - `tools.update_task()`
  - `tools.start_task()` (line 224)
  - `TaskRepository.complete_task()` (line 191)
- **Tests:** Same as MCP tool `update_task`

#### 5. `complete_task` (Line 186-191)
- **Return Type:** `Optional[Dict[str, Any]]`
- **Data Source:** Calls `update_task()` with status='completed'
- **Fields Returned:** All task fields via `update_task()`
- **Called By:** `tools.complete_task()`
- **Tests:** Same as MCP tool `complete_task`

### FeatureRepository (`database.py:194-244`)

#### 6. `add_feature` (Line 198-224)
- **Return Type:** `Dict[str, Any]`
- **Data Source:** `INSERT INTO features` then `SELECT * FROM features WHERE name = ?`
- **Fields Returned:** name, description, enabled, created_at
- **Called By:** `tools.add_feature()`
- **Tests:** Same as MCP tool `add_feature`

#### 7. `list_features` (Line 227-244)
- **Return Type:** `List[Dict[str, Any]]`
- **Data Source:** `SELECT * FROM features` with optional enabled filter
- **Fields Returned:** name, description, enabled, created_at
- **Called By:** `tools.list_features()`
- **Tests:** Same as MCP tool `list_features`

### DependencyRepository (`database.py:247-336`)

#### 8. `list_dependencies` (Line 251-276)
- **Return Type:** `List[Dict[str, Any]]`
- **Data Source:** `SELECT task_name, depends_on_task_name FROM dependencies`
- **Fields Returned:** task_name, depends_on_task_name
- **Called By:** `tools.list_dependencies()`
- **Tests:** Same as MCP tool `list_dependencies`

#### 9. `add_dependency` (Line 279-306)
- **Return Type:** `Dict[str, Any]`
- **Data Source:** `INSERT INTO dependencies` then returns dict literal (line 298-301)
- **Fields Returned:** task_name, depends_on_task_name
- **Called By:** 
  - `tools.add_dependency()`
  - `tools.add_task()` (line 149, when dependencies provided)
- **Tests:** Same as MCP tool `add_dependency`

#### 10. `get_available_tasks` (Line 322-336)
- **Return Type:** `List[Dict[str, Any]]`
- **Data Source:** `SELECT * FROM v_available_tasks` (SQL view)
- **Fields Returned:** All task fields (from view)
- **Called By:** `tools.get_available_tasks()`
- **Tests:** Same as MCP tool `get_available_tasks`

---

## Existing Response Models (Not Currently Used)

The codebase already has Pydantic response models defined in `models.py` (lines 256-347):

- `TaskResponse` (line 257-268) - Single task
- `TaskListResponse` (line 271-274) - List of tasks
- `DependencyResponse` (line 277-281) - Single dependency
- `DependencyListResponse` (line 284-289) - List of dependencies
- `TaskCreateResponse` (line 292-295) - Task creation result
- `TaskUpdateResponse` (line 298-303) - Task update result
- `TaskDeleteResponse` (line 306-311) - Task deletion result
- `DependencyCreateResponse` (line 314-317) - Dependency creation result
- `DependencyRemoveResponse` (line 320-325) - Dependency removal result
- `FeatureResponse` (line 328-334) - Single feature
- `FeatureListResponse` (line 337-340) - List of features
- `FeatureCreateResponse` (line 343-346) - Feature creation result

**These models are defined but NOT currently used by any tools or repository methods.**

---

## Migration Strategy Notes

### Phase 1: Repository Layer
1. Update repository methods to return Pydantic models
2. Add conversion from SQLite Row to Pydantic model
3. Maintain backward compatibility by keeping dict conversion as fallback

### Phase 2: MCP Tools Layer
1. Update MCP tools to use typed repository returns
2. Return Pydantic models from tools (FastMCP supports this)
3. Update tool type hints

### Phase 3: Testing
1. Update test assertions to work with Pydantic models
2. Add type checking to tests
3. Verify all callers handle typed returns correctly

### Considerations
- FastMCP automatically serializes Pydantic models to JSON
- Need to verify MCP clients can handle the typed responses
- Consider whether to use `.model_dump()` or let FastMCP handle serialization
- All 11 MCP tools and 10 repository methods need updating
- Tests need updating to assert on model attributes instead of dict keys

---

## Next Steps

1. **Create typed wrapper functions** that convert `Dict[str, Any]` to Pydantic models
2. **Implement repository method updates** to return Pydantic models
3. **Update MCP tools** to use typed returns
4. **Update tests** to work with Pydantic models
5. **Add mypy checks** to ensure type safety
6. **Remove old dict-based returns** after migration complete
