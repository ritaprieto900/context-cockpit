"""Tests for atomic storage and concurrency safety."""

from pathlib import Path

import pytest

from context_cockpit.domain.exceptions import StorageError
from context_cockpit.infrastructure.storage import AtomicStorage


def test_atomic_storage_write_and_read(tmp_path: Path):
    # Arrange
    storage = AtomicStorage()
    target_file = tmp_path / "test.md"
    content = "# Test Document\n\n- [ ] Task 1\n"

    # Act
    hash_val = storage.write_text_atomic(target_file, content)
    read_back, read_hash = storage.read_text(target_file)

    # Assert
    assert target_file.exists()
    assert read_back == content
    assert hash_val == read_hash
    # Ensure no lingering temp or lock files
    assert not any(p.name.startswith(".test.md.tmp") for p in tmp_path.iterdir())


def test_atomic_storage_read_nonexistent_raises_error(tmp_path: Path):
    # Arrange
    storage = AtomicStorage()
    missing_file = tmp_path / "nonexistent.md"

    # Act & Assert
    with pytest.raises(StorageError) as exc_info:
        storage.read_text(missing_file)
    assert "does not exist" in str(exc_info.value)


def test_atomic_storage_overwrite_preserves_integrity(tmp_path: Path):
    # Arrange
    storage = AtomicStorage()
    target_file = tmp_path / "state.md"
    storage.write_text_atomic(target_file, "Initial version")

    # Act
    storage.write_text_atomic(target_file, "Second version with updates")
    updated, _ = storage.read_text(target_file)

    # Assert
    assert updated == "Second version with updates"
