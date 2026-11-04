# AGENTS.md

## Code graph index (optional accelerator)

This repo may be indexed by `codebase-memory-mcp` (CBM) on an agent's local
machine — `.codebase-memory/` is gitignored. If your harness exposes CBM
tools (`search_graph`, `trace_path`, `get_architecture`, `detect_changes`),
prefer them for structural questions — symbol lookup, caller/callee traces,
impact analysis — instead of grep/read loops. Reindex after large refactors
(`index_repository`); treat `.codebase-memory/graph.db.zst` as a local cache
artifact, never commit it.

## Omarchy plugin layout

| Path | Role |
|---|---|
| `manifest.json` | `kinds: ["bar-widget"]`, id `io.github.duketopceo.snapdex` |
| `Panel.qml` | Bar icon, badge and panel; theme via `Commons.*` with fallbacks (bare `Color.` breaks on 4.5) |
| `snapdex` | CLI; `--auto` is what the path unit runs |
| `bin/snapdexlib.py` | Pure logic (names, dirs, index, search) - tested |
| `bin/snapdex-ctl` | JSON controller for the panel |
| `bin/snapdex-install` / `snapdex-uninstall` | systemd user path unit |

Rules: every bound `Text` sets `textFormat: Text.PlainText`; no hex colours;
index.md is rewritten only when its content changes (otherwise the path unit
would retrigger itself).
