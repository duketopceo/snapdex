---
title: snapdex program roadmap
date: 2026-10-11
status: proposed
---
# snapdex program roadmap

Builds on PR #3 (`docs/plans/2026-09-21-001-...hardening-plan.md`, still written under the old name `dayflow-screenshots`). Its U1-U5 are kept; this plan renumbers them, adds feasibility/simplification, and adds local inference and undo from the landscape research (`docs/research/2026-10-10-landscape.md`). Written directly rather than via ce-plan (one ~150-line script). Existing issues: #1 (systemd watcher), #2 (dedup + retry).

## Now

### U1 — Test seam and hermetic tests (from PR #3 U1+U2)
- Status: not started. Evidence: no `tests/`, no CI; `snapdex` has pure helpers `sanitize`, `rebuild_index`.
- Depends on: none. Verification: `pytest` passes with HTTP stubbed; script behaviour unchanged.
- **Difficulty:** easy. Pure functions already exist; only filename building needs extracting from `main`.
- **Feasibility:** `snapdex` has no `.py` extension, so tests must load it via `importlib.machinery.SourceFileLoader`.
- **Simpler alternative:** skip the refactor; test `sanitize`/`rebuild_index` directly and `main` via a temp `$HOME`.

### U2 — CI smoke (PR #3 U5)
- Status: not started. Depends on U1. Verification: workflow green; `python -m py_compile snapdex`.
- **Difficulty:** easy. **Feasibility:** public repo, hosted Actions fine; no API key needed.
- **Simpler alternative:** `py_compile` only, add pytest once U1 lands.

### U3 — Retry and dedup (closes #2)
- Status: partial. Evidence: `caption_one` already retries 3x with backoff; `main` already avoids filename collisions with `_2` suffixes. Missing: content-hash dedup, no retry distinction for 4xx vs 5xx.
- Depends on U1. Verification: stubbed 500,500,200 processes once; 401 fails fast.
- **Difficulty:** medium. Hash storage needs a place (index.md comment or sidecar).
- **Feasibility:** OpenRouter error shapes may change.
- **Simpler alternative:** drop hash dedup; the move already removes the source, so duplicates only arise from identical captures. Just stop retrying 4xx. Delete the `"screenshot"` fallback loop duplicate: `sanitize` default and `caption_one` fallback overlap.

## Next

### U4 — systemd user watcher (closes #1)
- Status: not started. Verification: drop a `screenshot-*.png`, see it renamed.
- **Difficulty:** easy. **Feasibility:** a `.path` unit watching `~/Pictures` is enough; needs a debounce so half-written files are not read.
- **Simpler alternative:** document a one-line `inotifywait` loop in the README instead of shipping units.

### U5 — Local vision backend (Ollama / OpenAI-compatible endpoint)
- Status: idea. Evidence: peers (ai-renamer, renamr) offer it; README privacy section is the main caveat today.
- **Difficulty:** medium. Add `base_url` config key; the request body is already OpenAI-compatible.
- **Feasibility:** local models must accept `image_url` data URIs; `detail: low` may be ignored. Quality of 3-6 word captions varies by model.
- **Simpler alternative:** only make `base_url` configurable; no provider abstraction.

## Later

### U6 — `--dry-run` and undo log
- **Difficulty:** medium. Log moves to a JSONL file and add `snapdex --undo`.
- **Feasibility:** none external. **Simpler alternative:** `--dry-run` only.

### U7 — Make index.md incremental
- **Difficulty:** easy. `rebuild_index` globs and sorts every PNG each run; fine up to thousands of files.
- **Feasibility:** none. **Simpler alternative:** leave as is; revisit only if runs get slow.

## Simplification summary
Biggest: no code to delete today; the cheapest value is tests + CI (U1, U2). Avoid adding a watcher daemon or provider layer.
