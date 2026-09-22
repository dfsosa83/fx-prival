"""Shared methodology for all Frival experiments (ROADMAP-2026-Q4 §7 _core/).

- costs.py     — single source of truth for per-pair trading friction (Issue C)
- bootstrap.py — overlap-aware moving-block bootstrap CI on EV/R (Issue B)

Nothing in _core/ may import experiment-specific code, and no experiment may
carry its own copy of these constants/functions.
"""