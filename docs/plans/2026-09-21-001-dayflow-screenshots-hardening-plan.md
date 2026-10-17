# Plan: dayflow-screenshots → 10/10

**Date:** 2026-09-21 · **Status:** proposed · **Depth:** lightweight
**Origin:** repo scorecard pass — engineering rigor 7, docs 5.

## Problem frame

A tidy single-script tool (vision-captioned screenshot organizer) with a genuinely good
README, but **no tests, no CI, and two open issues**: #1 (run as a `systemd --user`
service/watcher) and #2 (dedup + retry on vision API failure). Every edit to the script is
unverified, and transient OpenRouter failures can lose or duplicate work.

## Scope

**In:** hermetic tests, CI smoke check, systemd unit + docs (closes #1), dedup + retry
(closes #2).
**Out:** new caption providers, GUI, changing the `~/Pictures/Screenshots` layout.

## Implementation units

### U1 — Test seam (minimal refactor)
**Files:** `dayflow-screenshots` (the script)
- Extract pure functions for: target filename building, caption sanitizing, index-line
  formatting. No behavior change; the script must work exactly as before.
**Test scenarios:** n/a — verified by U2 passing against the refactored script.

### U2 — Hermetic test suite
**Files:** `tests/test_dayflow_screenshots.py` (new)
- Filename building: timestamp + snake_case caption, collision handling.
- Caption fallback: unusable caption → `screenshot`.
- Index writing: `index.md` append format, idempotent re-runs.
- HTTP stubbed: retry on transient failure, no retry on 4xx, dedup skips already-indexed files.
**Test scenarios:** vision API returns garbage → falls back, still renames; API 500s twice
then succeeds → file processed once; re-running over an indexed file → skipped, not duplicated.

### U3 — systemd watcher (closes #1)
**Files:** `systemd/dayflow-screenshots.service` (new), `README.md` (install section)
- A `--user` service (or path unit watching `~/Pictures`) with install/enable instructions.
**Test scenarios:** manual — enable, drop a `screenshot-*.png`, confirm it gets processed.

### U4 — Dedup + retry (closes #2)
**Files:** `dayflow-screenshots`
- Content-hash dedup: skip files already represented in `index.md`; bounded retries with
  backoff on transient vision-API failures.
**Test scenarios:** covered by U2 scenarios above.

### U5 — CI smoke check
**Files:** `.github/workflows/ci.yml` (new)
- `python -m py_compile` + `pytest` on push + PR.

## Key decisions

- Keep the **zero-dependency core** (Pillow + requests already required); pytest is test-only.
- Tests stub HTTP at the boundary — no OpenRouter key needed in CI.
- U1 is deliberately minimal: extract, don't redesign.

## Assumptions / open questions

- Assumes OpenRouter error shapes stay stable; U4 should treat unknown errors as retryable
  only up to the bound, then fail loudly.
