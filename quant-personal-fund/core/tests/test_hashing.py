"""Unit tests for core.hashing module."""
import json
import tempfile
from pathlib import Path

import pytest

from core.hashing import hash_dict, hash_file, verify_dict_hash, verify_file_hash


class TestHashFile:
    """Tests for hash_file and verify_file_hash."""

    def test_hash_file_known_content(self):
        """SHA256 of known content matches expected value."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write(b"hello world\n")
            f.flush()
            path = f.name

        try:
            result = hash_file(path)
            # SHA256 of b"hello world\n"
            expected = "a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447"
            assert result == expected, f"Got {result}"
        finally:
            Path(path).unlink()

    def test_hash_file_deterministic(self):
        """Same file produces the same hash twice."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            f.flush()
            path = f.name

        try:
            h1 = hash_file(path)
            h2 = hash_file(path)
            assert h1 == h2
        finally:
            Path(path).unlink()

    def test_hash_file_different_content(self):
        """Different content produces different hashes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f1:
            f1.write("content A")
            f1.flush()
            path_a = f1.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f2:
            f2.write("content B")
            f2.flush()
            path_b = f2.name

        try:
            assert hash_file(path_a) != hash_file(path_b)
        finally:
            Path(path_a).unlink()
            Path(path_b).unlink()

    def test_hash_file_not_found(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            hash_file("/nonexistent/file/path.txt")

    def test_verify_file_hash_match(self):
        """Verification returns True when hash matches."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("verify me")
            f.flush()
            path = f.name

        try:
            expected = hash_file(path)
            assert verify_file_hash(path, expected) is True
        finally:
            Path(path).unlink()

    def test_verify_file_hash_mismatch(self):
        """Verification returns False when hash does not match."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("verify me")
            f.flush()
            path = f.name

        try:
            assert verify_file_hash(path, "0" * 64) is False
        finally:
            Path(path).unlink()

    def test_hash_file_empty(self):
        """Empty file produces a valid hash."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            f.flush()
            path = f.name

        try:
            result = hash_file(path)
            # SHA256 of empty string
            expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            assert result == expected
        finally:
            Path(path).unlink()


class TestHashDict:
    """Tests for hash_dict and verify_dict_hash."""

    def test_hash_dict_deterministic(self):
        """Same dict produces the same hash."""
        d = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        assert hash_dict(d) == hash_dict(d)

    def test_hash_dict_order_independent(self):
        """Key insertion order does not affect hash."""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert hash_dict(d1) == hash_dict(d2)

    def test_hash_dict_different_values(self):
        """Different values produce different hashes."""
        assert hash_dict({"a": 1}) != hash_dict({"a": 2})

    def test_hash_dict_nested(self):
        """Nested dicts hash correctly."""
        d = {
            "experiment_id": "EXP-2026-01",
            "parameters": {"lookback": 60, "target": 0.10},
            "universe": ["EURUSD", "SPX"],
        }
        result = hash_dict(d)
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex digest length

    def test_verify_dict_hash_match(self):
        """Verification returns True when hash matches."""
        d = {"key": "value"}
        h = hash_dict(d)
        assert verify_dict_hash(d, h) is True

    def test_verify_dict_hash_mismatch(self):
        """Verification returns False when hash does not match."""
        d = {"key": "value"}
        assert verify_dict_hash(d, "0" * 64) is False

    def test_hash_dict_non_serializable(self):
        """Raises TypeError for non-JSON-serializable objects."""
        with pytest.raises(TypeError):
            hash_dict({"set": {1, 2, 3}})  # sets are not JSON-serializable