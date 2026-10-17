# AGENTS.md

Renames and indexes the `screenshot-*.png` files a Wayland compositor drops into
`~/Pictures`, by captioning each one with a vision model.

## Layout

- `dayflow-screenshots` — the whole program, one executable Python file.
- `README.md` — before/after examples of the rename.

## Commands

```bash
./dayflow-screenshots            # or: python3 dayflow-screenshots
```

There is no test suite, no CI, and no dependency manifest. The script is the
only artefact.

## Traps

- **It renames and moves real files in `~/Pictures`.** Run it against a copy
  first. It writes into `~/Pictures/Screenshots/` and maintains a markdown
  `index.md` catalog; a second run over an already-processed directory is not
  idempotent, because the processed files no longer match the `screenshot-*`
  glob it selects on.
- **The vision model call is the only network dependency** and it needs a key
  that is read from the environment. Without it the script cannot caption, and
  captioning is what produces the filename. It does not degrade to a
  pass-through rename.
- **Filenames are generated from model output**, so the
  `YYYY-MM-DD_HH-MM-SS_<snake_case_caption>.png` shape depends on the caption
  being sanitised. If you change the sanitising, check the collision case: two
  screenshots in the same second with the same caption.

## Related

This is the screenshot half of the Dayflow pair. The main repository is
`duketopceo/dayflow-linux`; do not assume shared code between them — this
repository is standalone and carries no dependency on it.

## Code graph index (optional accelerator)

This repo may be indexed by `codebase-memory-mcp` (CBM) on an agent's local
machine — `.codebase-memory/` is gitignored. If your harness exposes CBM
tools (`search_graph`, `trace_path`, `get_architecture`, `detect_changes`),
prefer them for structural questions — symbol lookup, caller/callee traces,
impact analysis — instead of grep/read loops. Reindex after large refactors
(`index_repository`); treat `.codebase-memory/graph.db.zst` as a local cache
artifact, never commit it.
