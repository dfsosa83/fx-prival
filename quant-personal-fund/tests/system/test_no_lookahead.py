"""Initial structural anti-look-ahead guard (static inspection only).

This is an INITIAL structural guard, NOT a proof that all strategy logic is leakage-free.
Complete anti-leakage validation will be added only when a specific new experiment and its
label horizon are pre-registered. This test does not import or execute any project code.

It performs two narrow static checks:
  1. The reusable research library must not define a direct helper named `future_return`,
     `forward_return`, `next_period_return`, or `lookahead_feature` unless the same file
     contains an explicit shift/lag control or a documented label-only context.
  2. The data/signal/portfolio/risk/backtest layers must not import execution/broker modules.

Deliberately narrow: it does not flag documentation that merely mentions these terms, because
only identifier tokens and AST import nodes are inspected.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Directories whose code is checked for uncontrolled look-ahead-style helper names.
HELPER_SCOPE = ("core", "data/pipelines", "signals", "portfolio", "risk", "backtest")

# Directories that must not import execution/broker modules.
IMPORT_SCOPE = ("data/pipelines", "signals", "portfolio", "risk", "backtest")

SUSPECT_HELPERS = frozenset(
    {"future_return", "forward_return", "next_period_return", "lookahead_feature"}
)

# A file is acceptable if it shows at least one of these explicit controls/contexts.
CONTROL_MARKERS = ("shift(", ".shift", "lag", "label", "purge", "embargo")

BROKER_MODULES = frozenset(
    {"metatrader5", "mt5", "execution", "ccxt", "websocket", "requests", "dotenv"}
)


def _py_files(dirs):
    files = []
    for dirname in dirs:
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


def _defined_functions(source):
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name.lower())
    return names


def _imported_roots(source):
    roots = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0].lower())
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0].lower())
    return roots


def test_no_uncontrolled_lookahead_helper():
    violations = []
    for path in _py_files(HELPER_SCOPE):
        source = path.read_text(encoding="utf-8", errors="replace")
        hits = _defined_functions(source) & SUSPECT_HELPERS
        if not hits:
            continue
        low = source.lower()
        has_control = any(marker in low for marker in CONTROL_MARKERS)
        if not has_control:
            for name in sorted(hits):
                violations.append(
                    f"{_rel(path)}: defines '{name}' without an explicit shift/lag control or "
                    f"label-only context"
                )
    assert not violations, (
        "Potential look-ahead helpers without a documented control:\n" + "\n".join(violations)
    )


def test_research_dirs_do_not_import_execution_or_broker():
    violations = []
    for path in _py_files(IMPORT_SCOPE):
        bad = _imported_roots(path.read_text(encoding="utf-8", errors="replace")) & BROKER_MODULES
        for token in sorted(bad):
            violations.append(f"{_rel(path)}: imports prohibited module '{token}'")
    assert not violations, (
        "Execution/broker imports found in research layers:\n" + "\n".join(violations)
    )
