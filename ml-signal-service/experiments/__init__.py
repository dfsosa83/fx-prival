"""Frival research experiments.

Layout contract — ROADMAP-2026-Q4-RESEARCH.md §7:

    ml-signal-service/experiments/
    ├── _core/                    # shared methodology (labels, costs, bootstrap CI)
    ├── EXP-2026-05-.../          # one folder per experiment, manifest-first
    └── ...

Existing production artifacts (notebooks/**, gold_rules/, docs/experiments/*)
are *registered* by each experiment's manifest, never moved here.
"""