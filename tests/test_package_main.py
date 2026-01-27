"""
Tests for the 'python -m tasktree' entry point.
"""

import subprocess
import sys


def test_python_m_tasktree_help():
    """Test that 'python -m tasktree --help' runs successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "tasktree", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "TaskTree CLI" in result.stdout
    assert "init" in result.stdout
    assert "start" in result.stdout
    assert "reset" in result.stdout
    assert "mcp" in result.stdout


def test_python_m_tasktree_no_args():
    """Test that 'python -m tasktree' with no args shows help/usage."""
    result = subprocess.run(
        [sys.executable, "-m", "tasktree"],
        capture_output=True,
        text=True,
    )

    # Typer returns exit code 2 when a required command is missing
    assert result.returncode == 2
    assert (
        "Usage: python -m tasktree" in result.stdout or "TaskTree CLI" in result.stdout
    )
