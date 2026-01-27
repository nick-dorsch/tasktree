# Agent Instructions

You are an autonomous coding agent working with tasktree.

## Your Task

1. Use `tasktree_get_available_tasks()` to list all tasks ready for implementation
2. Pick the **highest priority** task and call `tasktree_start_task(<task_name>)`
3. Implement this task ONLY!
4. Create tests for that task consistent with current testing patterns
5. Run quality checks (e.g., typecheck, lint, test - use whatever your project requires)
6. If checks pass, commit ALL changes to this branch with the name of the task completed
7. Mark the task complete with `tasktree_complete_task(task_name)`

## Quality Requirements

- ALL commits must pass this project's quality checks (typecheck, lint, test)
- Do NOT commit broken code
- Keep changes focused and minimal
- Follow existing code patterns

## Stop Condition

After completing an implementation, check if available tasks are empty

If true, run all tests, and if the tests pass, reply with:
<promise>COMPLETE</promise>

If there are still available tasks, end your response normally (another iteration will
pick up the next round) DO NOT PICK UP ANOTHER TASK.

## Important

- Work on ONE task only
- Only stop when the tests for that task are all passing
- The feature is provided for context only. Do not implement anything outside of the
task scope!
