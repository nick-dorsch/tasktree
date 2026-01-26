#!/bin/bash

# Run agent in a loop with stop condition
if [ -f "PROMPT.md" ]; then
    for i in {1..50}; do
        echo "=== Iteration $i ==="
        
        # Run opencode with prompt
        output=$(cat prompt.md | \
                opencode run \
                --model google/gemini-3-pro-preview \
                )
        
        # Check for the stop condition promise
        if echo "$output" | grep -q "<promise>COMPLETE</promise>"; then
            echo "=== All implementations complete!!! ==="
            exit 0
        fi
        
        echo "=== Iteration $i completed, continuing... ==="
        echo ""
    done
    
    echo "=== Maximum iterations (50) reached ==="
else
    echo "Error: PROMPT.md not found in current directory"
    exit 1
fi
