#!/usr/bin/env bash
# Draw task dependency graph with colored highlighting for available tasks
# Available tasks (all dependencies completed) are shown in green

set -euo pipefail

DB_PATH="${1:-data/tasktree.db}"

# Get list of available task names
AVAILABLE_TASKS=$(sqlite3 "$DB_PATH" "SELECT name FROM v_available_tasks" | tr '\n' '|' | sed 's/|$//')

# Get the DOT graph and render with graph-easy
DOT_GRAPH=$(sqlite3 "$DB_PATH" "SELECT dot_graph FROM v_graph_dot")

# Render with graph-easy
ASCII_GRAPH=$(echo "$DOT_GRAPH" | graph-easy)

# Add ANSI color codes for available tasks
if [ -n "$AVAILABLE_TASKS" ]; then
    # Green color: \033[32m ... \033[0m
    # Use extended regex to highlight task names
    echo "$ASCII_GRAPH" | awk -v tasks="$AVAILABLE_TASKS" '
    BEGIN {
        # Split tasks into array
        split(tasks, task_array, "|")
        for (i in task_array) {
            task_names[task_array[i]] = 1
        }
    }
    {
        line = $0
        for (task in task_names) {
            if (task != "" && index(line, task) > 0) {
                # Highlight the task name in green
                gsub(task, "\033[32m" task "\033[0m", line)
            }
        }
        print line
    }'
else
    echo "$ASCII_GRAPH"
fi
