"""
Session state management for TaskTree.
"""

import threading

# Global session counter (in-memory)
_counter: int = 0
_counter_lock = threading.Lock()

MAX_COUNTER_VALUE = 1


def get_counter() -> int:
    """Get the current session counter value."""
    with _counter_lock:
        return _counter


def increment_counter() -> int:
    """
    Increment the session counter (capped at MAX_COUNTER_VALUE).

    Returns:
        The new counter value
    """
    global _counter
    with _counter_lock:
        _counter = min(_counter + 1, MAX_COUNTER_VALUE)
        return _counter


def reset_counter() -> None:
    """Reset the session counter to 0."""
    global _counter
    with _counter_lock:
        _counter = 0
