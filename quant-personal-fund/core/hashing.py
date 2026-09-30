"""
Hashing utilities for data versioning and experiment reproducibility.

Provides deterministic SHA256 hashing for files and JSON-serializable Python
objects. Used to fingerprint experiment inputs, verify data integrity, and
detect parameter drift between pre-registration and scoring.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Union


def hash_file(path: Union[str, Path]) -> str:
    """
    Compute the SHA256 hash of a file.

    Args:
        path: Path to the file to hash.

    Returns:
        Hexadecimal SHA256 digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_dict(obj: Dict[str, Any]) -> str:
    """
    Compute a deterministic SHA256 hash of a JSON-serializable dictionary.

    The dictionary is serialized to a canonical JSON representation with sorted
    keys and no whitespace before hashing, ensuring determinism regardless of
    key insertion order.

    Args:
        obj: A JSON-serializable dictionary (no sets, tuples, or custom objects).

    Returns:
        Hexadecimal SHA256 digest string.

    Raises:
        TypeError: If the object is not JSON-serializable.
    """
    # Sort keys for deterministic output regardless of insertion order
    canonical_json = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def verify_file_hash(path: Union[str, Path], expected_hash: str) -> bool:
    """
    Verify that a file's SHA256 hash matches an expected value.

    Args:
        path: Path to the file.
        expected_hash: Expected hexadecimal SHA256 digest.

    Returns:
        True if the hash matches, False otherwise.
    """
    actual = hash_file(path)
    return actual == expected_hash


def verify_dict_hash(obj: Dict[str, Any], expected_hash: str) -> bool:
    """
    Verify that a dictionary's SHA256 hash matches an expected value.

    Args:
        obj: JSON-serializable dictionary.
        expected_hash: Expected hexadecimal SHA256 digest.

    Returns:
        True if the hash matches, False otherwise.
    """
    actual = hash_dict(obj)
    return actual == expected_hash