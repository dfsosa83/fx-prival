"""Static execution-isolation guard for the QPF research library.

This test enforces — by STATIC INSPECTION ONLY — that research-library code cannot reach
broker, execution, or credential infrastructure. It does not import any project module and does
not execute any project code.

Scanned directories (the reusable research library):
    core/, data/pipelines/, signals/, portfolio/, risk/, backtest/, llm_tools/, monitoring/

Explicitly EXCLUDED (they contain historical, standalone, or sanctioned artifacts):
    audits/, scripts/, experiments/, execution/

Narrow, documented exception:
    data/pipelines/download.py is the sanctioned data-acquisition module and may reference the
    DATA VENDORS `yfinance` and `fredapi`. These are market-data vendors, not broker/execution
    code. The exception is limited to that single file and those two tokens. Every
    broker/execution token remains forbidden there and everywhere else in the scanned set.
"""

from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = (
    "core",
    "data/pipelines",
    "signals",
    "portfolio",
    "risk",
    "backtest",
    "llm_tools",
    "monitoring",
)

EXCLUDED_DIRS = ("audits", "scripts", "experiments", "execution")

# Broker / execution / credential tokens: forbidden everywhere in the scanned set.
BROKER_MODULES = frozenset(
    {"metatrader5", "mt5", "execution", "ccxt", "websocket", "requests", "dotenv"}
)

# Data-vendor tokens: allowed ONLY in the sanctioned acquisition module.
VENDOR_MODULES = frozenset({"yfinance", "fredapi"})
VENDOR_ALLOWLIST = frozenset({"data/pipelines/download.py"})

# Prohibited credential-path literals.
PROHIBITED_PATH_LITERALS = ("credentials.env",)


def _py_files():
    files = []
    for dirname in SCAN_DIRS:
        root = PROJECT_ROOT / dirname
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return files


def _rel(path):
    return path.relative_to(PROJECT_ROOT).as_posix()


def _source(path):
    return path.read_text(encoding="utf-8", errors="replace")


def _imported_roots(source):
    """Top-level module names from `import x` / `from x import y` (relative imports skipped)."""
    roots = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0].lower())
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0].lower())
    return roots


def _name_tokens(source):
    """Identifier tokens only; comments and string literals are skipped by the tokenizer."""
    names = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.NAME:
                names.add(tok.string.lower())
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Fall back to AST-only coverage for this file if it cannot be tokenized.
        pass
    return names


def _scan_files():
    files = _py_files()
    assert files, "No Python files found to scan; check PROJECT_ROOT / SCAN_DIRS."
    return files


def test_scanned_dirs_present():
    """Sanity: the isolation scan must cover the expected research-library directories."""
    present = {d for d in SCAN_DIRS if (PROJECT_ROOT / d).exists()}
    assert present == set(SCAN_DIRS), f"Missing scan directories: {set(SCAN_DIRS) - present}"


def test_excluded_dirs_not_scanned():
    """Guard: historical/standalone directories must never be part of the isolation scan."""
    scanned_parents = {_rel(p).split("/")[0] for p in _scan_files()}
    assert scanned_parents.isdisjoint(set(EXCLUDED_DIRS)), (
        f"Excluded directories leaked into the scan: {scanned_parents & set(EXCLUDED_DIRS)}"
    )


def test_research_library_does_not_import_broker_or_execution():
    violations = []
    for path in _scan_files():
        bad = _imported_roots(_source(path)) & BROKER_MODULES
        for token in sorted(bad):
            violations.append(f"{_rel(path)}: imports prohibited module '{token}'")
    assert not violations, (
        "Broker/execution/credential imports found in the research library:\n"
        + "\n".join(violations)
    )


def test_research_library_does_not_reference_broker_or_execution_names():
    violations = []
    for path in _scan_files():
        bad = _name_tokens(_source(path)) & BROKER_MODULES
        for token in sorted(bad):
            violations.append(f"{_rel(path)}: references prohibited name '{token}'")
    assert not violations, (
        "Broker/execution/credential identifiers found in the research library:\n"
        + "\n".join(violations)
    )


def test_research_library_does_not_reference_credential_paths():
    violations = []
    for path in _scan_files():
        low = _source(path).lower()
        for literal in PROHIBITED_PATH_LITERALS:
            if literal in low:
                violations.append(f"{_rel(path)}: references credential path literal '{literal}'")
    assert not violations, (
        "Credential path references found in the research library:\n" + "\n".join(violations)
    )


def test_data_vendors_only_in_allowlisted_acquisition_module():
    violations = []
    for path in _scan_files():
        rel = _rel(path)
        if rel in VENDOR_ALLOWLIST:
            continue
        source = _source(path)
        found = (_imported_roots(source) | _name_tokens(source)) & VENDOR_MODULES
        for token in sorted(found):
            violations.append(
                f"{rel}: references data-vendor '{token}' outside the allowlist {VENDOR_ALLOWLIST}"
            )
    assert not violations, (
        "Data-vendor references found outside the sanctioned acquisition module:\n"
        + "\n".join(violations)
    )
