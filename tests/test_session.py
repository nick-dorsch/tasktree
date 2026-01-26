"""
Tests for session state management.
"""


from tasktree_mcp import session


def test_counter_starts_at_zero():
    """Test that counter initializes to 0."""
    session.reset_counter()  # Ensure clean state
    assert session.get_counter() == 0


def test_increment_counter():
    """Test that counter increments from 0 to 1."""
    session.reset_counter()
    assert session.get_counter() == 0

    new_value = session.increment_counter()
    assert new_value == 1
    assert session.get_counter() == 1


def test_counter_caps_at_max():
    """Test that counter caps at MAX_COUNTER_VALUE (1)."""
    session.reset_counter()

    # Increment multiple times
    session.increment_counter()  # 0 → 1
    session.increment_counter()  # 1 → 1 (capped)
    session.increment_counter()  # 1 → 1 (capped)

    assert session.get_counter() == 1


def test_reset_counter():
    """Test that counter resets to 0."""
    session.reset_counter()
    session.increment_counter()
    assert session.get_counter() == 1

    session.reset_counter()
    assert session.get_counter() == 0


def test_counter_cycle():
    """Test a full cycle: increment, reset, increment."""
    session.reset_counter()

    # First cycle
    assert session.get_counter() == 0
    session.increment_counter()
    assert session.get_counter() == 1

    # Reset
    session.reset_counter()
    assert session.get_counter() == 0

    # Second cycle
    session.increment_counter()
    assert session.get_counter() == 1
