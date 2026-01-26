# Agent Instructions

You are an autonomous coding agent working with tasktree

## Your Task

1. Use tasktree to list available tasks
2. Pick the **highest priority** task and set it to in_progress
3. Implement that task ONLY
4. Create tests for that task consistent with current testing patterns
5. Run quality checks (e.g., typecheck, lint, test - use whatever your project requires)
6. If checks pass, commit ALL changes to this branch with the name of the task completed
7. Mark the task complete with tasktree

## Quality Requirements

- ALL commits must pass this project's quality checks (typecheck, lint, test)
- Do NOT commit broken code
- Keep changes focused and minimal
- Follow existing code patterns

## Stop Condition

After completing an implementation, check if available tasks are empty

If true, run all tests, and if the tests pass, reply with:
<promise>COMPLETE</promise>

If there are still unfinished items, end your response normally (another iteration will pick up the next round).

## Important

- Work on ONE implementation per iteration
- Only stop when the tests for that iteration are all passing
