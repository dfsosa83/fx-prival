# Continuity Protocol

Permanent workflow for future chats. Under 1,200 words.

## Mandatory first-read sequence

```text
1. quant-personal-fund/research_control/PROJECT_HANDOFF.md
2. quant-personal-fund/research_control/NEXT_ACTION.md
3. quant-personal-fund/research_control/RESEARCH_LEDGER.yaml
4. quant-personal-fund/research_control/CONTINUITY_PROTOCOL.md
5. Only the source artifacts listed in NEXT_ACTION.md
```

## Source precedence

1. Existing experiment decision artifacts and immutable manifests/snapshots **override** summaries.
2. `NEXT_ACTION.md` governs the scope of the immediate task.
3. `RESEARCH_LEDGER.yaml` governs global status and prohibitions.
4. `PROJECT_HANDOFF.md` provides human-readable orientation.
5. The full chat archive is **recovery-only**, never daily operating context.

When state documents conflict, an agent must **ask for clarification rather than assume**.

## State update rule

Future agents may update continuity files **only at the end of a completed, explicitly authorized
stage**, and only after verifying artifact paths and decisions.

## File placement rule

- Global state belongs **only** in `quant-personal-fund/research_control/`.
- Experiment-specific evidence belongs **only** in that experiment folder.
- Raw-data artifacts belong **only** in the designated raw-data location.
- Do **not** duplicate global handoffs in experiment folders.
- Do **not** create ad hoc summaries at repository root.
- Do **not** scatter copies of prompts or transcript excerpts.

## New-chat bootstrap template

```text
We are continuing the Forex/XAUUSD quantitative research repository.

Before proposing or performing any work:

1. Read, in this exact order:
   - `quant-personal-fund/research_control/PROJECT_HANDOFF.md`
   - `quant-personal-fund/research_control/NEXT_ACTION.md`
   - `quant-personal-fund/research_control/RESEARCH_LEDGER.yaml`
   - `quant-personal-fund/research_control/CONTINUITY_PROTOCOL.md`
   - only the source artifacts named by `NEXT_ACTION.md`.

2. Treat immutable manifests, snapshots and decision artifacts as higher
   precedence than summaries.

3. Return first:
   - active research family;
   - current project state;
   - immediate authorized action;
   - blocked/prohibited actions;
   - exact artifacts read;
   - any inconsistency or missing provenance.

4. Do not access raw data, MT5, broker, credentials, network, execution,
   market-data sources or run calculations until the project state has been
   summarized and the user gives an explicit task authorization.
```

## Session-close template

```text
Before stopping after a completed authorized stage:

1. Verify the created/modified artifacts and final decision.
2. Update only:
   - `quant-personal-fund/research_control/PROJECT_HANDOFF.md`
   - `quant-personal-fund/research_control/RESEARCH_LEDGER.yaml`
   - `quant-personal-fund/research_control/NEXT_ACTION.md`
3. Keep the handoff concise; do not copy the chat transcript.
4. Record only verified facts, blockers, immutable artifact paths, final
   decisions, prohibitions and the exact next authorized action.
5. Do not broaden authorization or change a frozen protocol in these files.
```

## Required guardrails

- No silent protocol changes after outcomes.
- No PnL/execution before explicit staged authorization.
- `NOT_UTC` handling for all timestamp labels.
- Hash verification before statistical screens.
- Max available label exclusion in snapshots.
- FX/XAUUSD separate strata in H6.
- One active next action only.
- An agent must ask for clarification rather than assume when state documents conflict.
