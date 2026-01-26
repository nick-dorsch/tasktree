# Test Suite Review

This note records redundancy and consolidation candidates found in the current test
suite. It does not remove tests; it flags overlap to reduce runtime and maintenance.

## Candidates for consolidation or removal

1. `tests/test_repository_with_fixture.py`
   - Rationale: Duplicates core CRUD and dependency coverage already in
     `tests/test_add_task.py`, `tests/test_list_tasks.py`, `tests/test_get_task.py`,
     `tests/test_update_task.py`, `tests/test_delete_task.py`, and
     `tests/test_add_dependency.py`. The file reads like usage examples and repeats
     ordering and isolation checks.
   - Suggestion: Convert to a short smoke test or move to docs/examples.

2. `tests/test_details_field.py`
   - Rationale: The details field is already exercised in
     `tests/test_add_task.py`, `tests/test_update_task.py`, `tests/test_get_task.py`,
     and `tests/test_list_tasks.py`. Coverage is duplicated across four files.
   - Suggestion: Keep details assertions only in the most relevant per-tool tests
     (add/update/get/list) and remove the standalone file.

3. `tests/test_add_task.py` (ordering and retrieval sections)
   - Rationale: `test_add_task_ordering` overlaps with
     `tests/test_list_tasks.py::test_list_tasks_ordering_by_priority_descending`.
     `test_add_task_retrieval_after_creation` overlaps with
     `tests/test_get_task.py::test_get_task_immediately_after_creation`.
   - Suggestion: Keep ordering in list_tasks tests and keep retrieval in get_task
     tests to avoid cross-tool coupling.

4. `tests/test_get_task.py` (name variants)
   - Rationale: Name variants (special chars, unicode, case sensitivity) overlap
     with `tests/test_add_task.py` coverage for name validity and character sets.
   - Suggestion: Consolidate name-variant tests in one file (prefer add_task or
     get_task, not both).

5. `tests/test_update_task.py` vs `tests/test_start_task.py` and
   `tests/test_complete_task.py`
   - Rationale: Status transition tests duplicate behavior. For example, starting
     a task to set `started_at` is verified in both update_task and start_task
     tests; completion timestamps are verified in both update_task and complete_task
     tests.
   - Suggestion: Keep timestamp transition assertions in one place and leave the
     start/complete files to focus on endpoint-specific behavior and error cases.

6. `tests/test_database.py` vs `tests/test_repository_with_fixture.py`
   - Rationale: Isolation checks appear in both files. The repository fixture file
     repeats the same empty-db assertion as the database fixture tests.
   - Suggestion: Keep isolation tests in `tests/test_database.py` and drop the
     redundant copy.

7. `tests/test_list_tasks.py` (large dataset tests)
   - Rationale: The large dataset tests add 100 rows multiple times and cover the
     same ordering and filtering logic as smaller, deterministic tests. This can
     increase runtime without much extra signal.
   - Suggestion: Replace with a single medium-size parameterized test or move to
     a performance-focused suite if needed.

## Notes

- The suggestions above are conservative and keep at least one test for each
  behavior. Consolidation should retain coverage for ordering, filtering, and
  status transitions.
- If removal is planned, consider keeping one representative test per behavior
  and use parameterization to reduce file count.
