# snapdex

Auto-rename and index screenshots with a vision model.

Takes the `screenshot-*.png` files a Wayland compositor drops in `~/Pictures`
(Omarchy 4.x) or `~/Pictures/Screenshots` (Omarchy 4.5 `omasnap`, named
`screenshot-<ts>-<slug>.png`), captions each one with a vision
model, and moves them out of the inbox into the Library as
`~/Pictures/Screenshots/Library/YYYY/MM/YYYY-MM-DD_HH-MM-SS_<snake_case_caption>.png`
(name collisions get a `-2` suffix, nothing is overwritten) — plus a markdown
`Library/index.md` (paths relative to the Library). `.jpg`/`.jpeg` captures
are accepted too.

Before:

```
~/Pictures/screenshot-2026-09-05_01-55-46.png
```

After:

```
~/Pictures/Screenshots/Library/2026/09/2026-09-05_01-55-46_daily_standup_log.png
~/Pictures/Screenshots/Library/index.md
```

## How it works

- One OpenRouter vision request per image (`detail: low`, ~30 output tokens)
  with retries; falls back to `screenshot` if the caption is unusable.
- Config resolution, later wins: `~/.config/dayflow/config.json` (legacy
  fallback) → `~/.config/snapdex/config.json` → `OPENROUTER_API_KEY` env var
  as a final fallback for the key only. Reads `openrouter_api_key` and
  `model`.
- Default model: `google/gemma-4-31b-it`. Any OpenRouter vision model works.

## Requirements

- Python 3 with `Pillow` and `requests` (`pip install pillow requests`)
- An OpenRouter API key in one of the config locations above

## Install

```sh
install -Dm755 snapdex ~/.local/bin/snapdex
snapdex
```

## Usage

```sh
snapdex   # processes all ~/Pictures/screenshot-*.png
```

Tip: wrap your screenshot hotkey so every capture gets organized
automatically — call `snapdex` in the background after your screenshot tool
saves the file.

## Config

`~/.config/snapdex/config.json` — only the keys you want to set:

```json
{
  "model": "google/gemma-4-31b-it",
  "openrouter_api_key": "sk-or-..."
}
```

Either key may be omitted: `model` falls back to the default; the API key
falls back to the legacy dayflow config, then to `OPENROUTER_API_KEY`.

## Privacy

Screenshots are resized to 640px JPEG thumbnails before being sent to
OpenRouter for captioning. The renamed files and index stay local in
`~/Pictures/Screenshots/Library/`.

## Omarchy plugin

This repo is also an Omarchy shell plugin (`io.github.duketopceo.snapdex`):
a camera bar icon with a badge of unprocessed shots, plus a panel with the
last 12 captioned screenshots (click opens, right-click copies the path), a
caption search box, a "Process now" button and an auto-processing toggle.

```sh
omarchy plugin add https://github.com/duketopceo/snapdex --enable
```

Auto-processing is a systemd user path unit (`snapdex.path`, installed by
`bin/snapdex-install`, removed by `bin/snapdex-uninstall [--purge]`), so it
works with the bar closed. It only touches shots taken after you switch it
on, at most 10 per run, and leaves a shot alone if captioning fails. The
backlog is processed only by "Process now" / `snapdex`.

Folders: sources are `~/Pictures` and the screenshot folder
(`OMARCHY_SCREENSHOT_DIR`, default `~/Pictures/Screenshots`) — the inbox, which
only ever holds unprocessed `screenshot-*` files. Results land in the Library
(`library` config key or `SNAPDEX_LIBRARY`, default `<screenshot folder>/Library`).

Existing flat libraries: `snapdex migrate --dry-run`, then `snapdex migrate`
moves captioned files into `Library/YYYY/MM`, rewrites the index and writes a
manifest `Library/.migrate-<ts>.tsv`; reverse it with
`snapdex migrate --undo <tsv>`. The API key may also come from omaseal: set
`"omaseal": "service/account"` in the config.

Tests: `python3 -m unittest discover -s tests`.

MIT licensed.
