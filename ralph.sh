#!/bin/bash

# Run agent in a loop with stop condition
if [ -f "PROMPT.md" ]; then
    for i in {1..50}; do
        echo "=========================="
        echo "=== Iteration $i ==="
        echo "=========================="
        echo ""
        
        # Run opencode with prompt
        output=$(cat PROMPT.md | \
                opencode run \
                # --model opencode/big-pickle 
                # --model google/gemini-3-pro-preview
                --model anthropic/claude-sonnet-4-5\
                2>&1 | tee /dev/tty)
        
        # Check for the stop condition promise
        if echo "$output" | grep -q "<promise>COMPLETE</promise>"; then
            echo "======================================="
            echo "=== All implementations complete!!! ==="
            echo "======================================="
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
