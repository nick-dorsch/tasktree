"""
Tests for the features table schema and default feature seeding.
"""

import sqlite3


def test_features_table_exists(test_db_connection: sqlite3.Connection):
    """Test that the features table exists."""
    cursor = test_db_connection.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='features'"
    )
    result = cursor.fetchone()
    assert result is not None


def test_features_table_schema(test_db_connection: sqlite3.Connection):
    """Test that the features table has the correct schema."""
    cursor = test_db_connection.cursor()

    # Check that the table has expected columns
    cursor.execute("PRAGMA table_info(features)")
    columns = {row["name"]: row for row in cursor.fetchall()}

    expected_columns = {
        "name",
        "description",
        "enabled",
        "created_at",
    }
    assert expected_columns.issubset(set(columns.keys()))

    # Verify name is the primary key
    assert columns["name"]["pk"] == 1

    # Verify enabled column has correct type
    assert "BOOLEAN" in columns["enabled"]["type"].upper()


def test_default_feature_is_seeded(test_db_connection: sqlite3.Connection):
    """Test that the default feature is automatically seeded."""
    cursor = test_db_connection.cursor()

    cursor.execute("SELECT * FROM features WHERE name = 'default'")
    result = cursor.fetchone()

    assert result is not None
    assert result["name"] == "default"
    assert result["description"] == "Default feature set for basic task management"
    assert result["enabled"] == 1


def test_features_name_is_primary_key(test_db_connection: sqlite3.Connection):
    """Test that feature name is a unique primary key."""
    cursor = test_db_connection.cursor()

    # Try to insert a duplicate feature name
    cursor.execute(
        "INSERT INTO features (name, description) VALUES (?, ?)",
        ("test-feature", "First insert"),
    )
    test_db_connection.commit()

    # Attempt to insert duplicate should fail
    try:
        cursor.execute(
            "INSERT INTO features (name, description) VALUES (?, ?)",
            ("test-feature", "Duplicate insert"),
        )
        test_db_connection.commit()
        assert False, "Expected IntegrityError for duplicate feature name"
    except sqlite3.IntegrityError:
        # This is expected behavior
        pass


def test_enabled_values_round_trip(test_db_connection: sqlite3.Connection):
    """Test that enabled values are stored as provided."""
    cursor = test_db_connection.cursor()

    cursor.execute(
        "INSERT INTO features (name, enabled) VALUES (?, ?)",
        ("enabled-feature", 1),
    )
    cursor.execute(
        "INSERT INTO features (name, enabled) VALUES (?, ?)",
        ("disabled-feature", 0),
    )
    test_db_connection.commit()

    cursor.execute(
        "SELECT name, enabled FROM features WHERE name IN (?, ?)",
        ("enabled-feature", "disabled-feature"),
    )
    rows = {row["name"]: row["enabled"] for row in cursor.fetchall()}
    assert rows["enabled-feature"] == 1
    assert rows["disabled-feature"] == 0


def test_default_enabled_value(test_db_connection: sqlite3.Connection):
    """Test that enabled defaults to 1 (enabled) when not specified."""
    cursor = test_db_connection.cursor()

    cursor.execute(
        "INSERT INTO features (name, description) VALUES (?, ?)",
        ("auto-enabled", "Should default to enabled"),
    )
    test_db_connection.commit()

    cursor.execute("SELECT enabled FROM features WHERE name = ?", ("auto-enabled",))
    result = cursor.fetchone()
    assert result["enabled"] == 1
