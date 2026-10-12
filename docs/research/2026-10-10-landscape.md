# snapdex landscape (2026-10-11)

Sources are a web search run on 2026-10-11; third-party summaries, not verified against each repo. Re-check before relying on them.

## Comparable projects

| Project | What it is | Link |
|---|---|---|
| ai-renamer (ozgrozer) | Node CLI, renames by content via Ollama / LM Studio / OpenAI; GPL-3.0 | https://gittrend.io/repo/ozgrozer/ai-renamer |
| ai-file-sorter (hyperfield) | C++ desktop app, local vision model, suggestions need approval, undo | https://linuxhandbook.com/blog/ai-file-sorter/ |
| LlamaFS (iyaja) | Llama 3 via Groq, Moondream for images; not local by default | https://www.sourcepulse.org/projects/1254971 |
| ImageScan / vision-file-name | CLI, OpenAI-compatible vision API (LM Studio) renames images | https://github.com/rogu3bear/ImageScan |
| renamr (PyPI) | CLI using Ollama vision models, fully local | https://pypi.org/project/renamr/ |
| Screenshotify | CLI, vision API key required, macOS/Linux | https://aiindigo.com/tutorials/getting-started-with-screenshotify-automate-screenshot-organization |

## What they do better
- Local inference (Ollama, LM Studio): no screenshot leaves the machine. snapdex is OpenRouter-only.
- Preview/approve and undo (ai-file-sorter). snapdex renames immediately and cannot undo.
- Watch mode or GUI. snapdex is a one-shot run (issue #1 tracks a systemd watcher).

## What they do worse
- Most are general file renamers; they need prompt tuning for UI screenshots. snapdex's prompt, timestamp-preserving name and `index.md` catalog are screenshot-specific.
- Heavy runtimes (Node, C++ build) against one ~150-line Python file with two dependencies.

## What users expect
Descriptive but short names, a stable timestamp prefix, no collisions, safe failure (keep the file if captioning fails), optional local models, and an undo path.

## What is unique here
Single-file script, Wayland-first (`screenshot-*.png` from grim/omarchy), keeps the capture timestamp, rebuilds a markdown index, resizes to 640px before upload, and falls back to `screenshot` rather than dropping a file.
