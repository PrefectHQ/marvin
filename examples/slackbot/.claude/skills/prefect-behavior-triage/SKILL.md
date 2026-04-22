---
name: prefect-behavior-triage
description: Use when a Prefect question hinges on whether observed behavior is expected, a documentation gap, or a real bug. Inspect docs and source first, then build and run a minimal reproduction only when needed.
---

# Prefect Behavior Triage

Use this skill when a user reports surprising Prefect behavior or asks whether something is a bug.

## Workflow

1. Read the relevant docs and implementation before making claims.
2. If docs and source code already answer the question, do not reproduce unnecessarily.
3. If runtime behavior still matters, create the smallest possible reproduction and run it.
4. Compare four things explicitly:
   - what the user observed
   - what the docs say
   - what the source code does
   - what the reproduction actually did
5. End with a clear classification:
   - expected behavior
   - docs unclear or outdated
   - likely bug
   - still inconclusive

## Reproduction Rules

- Prefer tiny standalone scripts over modifying existing project files.
- Write repros under `.research_cache/repros/` and reuse them if they already fit.
- Keep the repro focused on one claim or edge case.
- Use `uv run python <script>` or `uv run python - <<'PY'` for quick checks.
- If the question involves the Prefect API, use the real client or real flow/task execution rather than simulating behavior.
- If the behavior depends on configuration, log the exact assumptions in the final answer.

## Reporting Rules

- Do not call something a bug unless docs, source, and observed behavior are materially misaligned.
- If docs and source agree, treat that as intended behavior even if it is surprising.
- If source and runtime agree but docs do not, call out the documentation mismatch separately.
- Cite the specific files or commands you used to reach the conclusion.
