import re
from pathlib import Path


def update_file(file_path):
    content = file_path.read_text()

    # Check if file already has specification="Spec" (naive check)
    # But some calls might have it and some not.
    # However, these are test files I haven't touched yet (except the ones I just did).

    # Generic replacement for TaskRepository.add_task(arg1, arg2, ...)
    # match TaskRepository.add_task( followed by arg1, comma, arg2
    # arg1 and arg2 can be quoted strings or variables.

    # Regex for: TaskRepository.add_task("str", "str"
    # Matches simple calls
    content = re.sub(
        r'TaskRepository\.add_task\(\s*"([^"]+)",\s*"([^"]+)"',
        r'TaskRepository.add_task("\1", "\2", specification="Spec"',
        content,
    )

    # Regex for: TaskRepository.add_task(var, "str"
    content = re.sub(
        r'TaskRepository\.add_task\(\s*([a-zA-Z0-9_]+),\s*"([^"]+)"',
        r'TaskRepository.add_task(\1, "\2", specification="Spec"',
        content,
    )

    # Regex for: TaskRepository.add_task(var, f"str"
    content = re.sub(
        r'TaskRepository\.add_task\(\s*([a-zA-Z0-9_]+),\s*f"([^"]+)"',
        r'TaskRepository.add_task(\1, f"\2", specification="Spec"',
        content,
    )

    # Handle the case where we just added specification="Spec" followed by existing kwargs or closing paren
    # But my regex replacement replaced the opening of the call.
    # e.g. TaskRepository.add_task("a", "b", priority=1)
    # became TaskRepository.add_task("a", "b", specification="Spec", priority=1)
    # e.g. TaskRepository.add_task("a", "b")
    # became TaskRepository.add_task("a", "b", specification="Spec")

    # Clean up double commas if any (regex shouldn't produce them if I did it right)

    # Also handle multiline calls where args are on new lines
    # TaskRepository.add_task(
    #     "name",
    #     "desc",
    # )
    # This regex won't catch that.

    # Let's try to handle multiline specifically for common patterns

    file_path.write_text(content)


files_to_process = [
    "tests/features/test_task_feature_fk.py",
    "tests/graph/test_color_coding.py",
    "tests/graph/test_graph_server.py",
    "tests/mcp/test_add_dependencies_tool.py",
    "tests/tasks/test_get_available_tasks.py",
    "tests/tasks/test_get_task.py",
    "tests/tasks/test_list_tasks.py",
    "tests/tasks/test_start_task.py",
    "tests/tasks/test_update_task.py",
]

for f in files_to_process:
    path = Path(f)
    if path.exists():
        update_file(path)
        print(f"Updated {f}")
