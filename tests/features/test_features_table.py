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
        "id",
        "name",
        "description",
        "specification",
        "created_at",
        "updated_at",
    }
    assert expected_columns.issubset(set(columns.keys()))

    # Verify id is the primary key
    assert columns["id"]["pk"] == 1


def test_default_feature_is_seeded(test_db_connection: sqlite3.Connection):
    """Test that the default feature is automatically seeded."""
    cursor = test_db_connection.cursor()

    cursor.execute("SELECT * FROM features WHERE name = 'misc'")
    result = cursor.fetchone()

    assert result is not None
    assert result["name"] == "misc"
    assert result["description"] == "Default feature for uncategorized tasks"
    assert (
        result["specification"]
        == "Use this feature in cases where a task is minimal and does not require a feature, such as minor hotfixes, tweaks etc."
    )


def test_features_name_is_primary_key(test_db_connection: sqlite3.Connection):
    """Test that feature name is a unique primary key."""
    cursor = test_db_connection.cursor()

    # Try to insert a duplicate feature name
    cursor.execute(
        "INSERT INTO features (name, description, specification) VALUES (?, ?, ?)",
        (
            "test-feature",
            "First insert",
            "First feature specification",
        ),
    )
    test_db_connection.commit()

    # Attempt to insert duplicate should fail
    try:
        cursor.execute(
            "INSERT INTO features (name, description, specification) VALUES (?, ?, ?)",
            (
                "test-feature",
                "Duplicate insert",
                "Duplicate feature specification",
            ),
        )
        test_db_connection.commit()
        assert False, "Expected IntegrityError for duplicate feature name"
    except sqlite3.IntegrityError:
        # This is expected behavior
        pass


def test_specification_is_required(test_db_connection: sqlite3.Connection):
    """Test that specification is required for new features."""
    cursor = test_db_connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO features (name, description) VALUES (?, ?)",
            ("missing-spec", "No specification provided"),
        )
        test_db_connection.commit()
        assert False, "Expected IntegrityError for missing specification"
    except sqlite3.IntegrityError:
        pass
