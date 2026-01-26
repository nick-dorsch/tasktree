"""
Tests for the JSONL snapshot format documentation.
"""

from pathlib import Path


def test_snapshot_format_doc_exists() -> None:
    """Ensure the JSONL snapshot format doc exists."""
    doc_path = Path(__file__).parent.parent / "docs" / "jsonl-snapshot-format.md"
    assert doc_path.exists()
    assert doc_path.is_file()


def test_snapshot_format_doc_contains_record_types() -> None:
    """Ensure record types are documented."""
    doc_path = Path(__file__).parent.parent / "docs" / "jsonl-snapshot-format.md"
    content = doc_path.read_text(encoding="utf-8")

    for record_type in ("meta", "feature", "task", "dependency"):
        assert f"`{record_type}`" in content


def test_snapshot_format_doc_contains_serialization_settings() -> None:
    """Ensure serialization settings are documented."""
    doc_path = Path(__file__).parent.parent / "docs" / "jsonl-snapshot-format.md"
    content = doc_path.read_text(encoding="utf-8")

    assert "sort_keys" in content
    assert "separators" in content
    assert "ensure_ascii" in content


def test_snapshot_format_doc_contains_ordering_rules() -> None:
    """Ensure deterministic ordering rules are documented."""
    doc_path = Path(__file__).parent.parent / "docs" / "jsonl-snapshot-format.md"
    content = doc_path.read_text(encoding="utf-8")

    assert "Deterministic Ordering" in content
    assert "meta" in content
    assert "feature" in content
    assert "task" in content
    assert "dependency" in content
