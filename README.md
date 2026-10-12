<p align="center"><img src="assets/brand/wordmark.svg" alt="snapdex" height="64"></p>

> Logo is a proposal pending owner sign-off.

Auto-rename and index screenshots with a vision model.

Takes the `screenshot-*.png` files a Wayland compositor drops in `~/Pictures`
(e.g. via `grim`/`omarchy-capture-screenshot`), captions each one with a vision
model, and moves them into `~/Pictures/Screenshots/` as
`YYYY-MM-DD_HH-MM-SS_<snake_case_caption>.png` — plus a markdown `index.md`
catalog of everything processed.

Before:

```
~/Pictures/screenshot-2026-09-05_01-55-46.png
```

After:

```
~/Pictures/Screenshots/2026-09-05_01-55-46_daily_standup_log.png
~/Pictures/Screenshots/index.md
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
`~/Pictures/Screenshots/`.

MIT licensed.

## Status and roadmap

See [ROADMAP.md](ROADMAP.md), [DESIGN.md](DESIGN.md) and [docs/research/2026-10-10-landscape.md](docs/research/2026-10-10-landscape.md). No tests or CI yet.

## Contributing

Issues and PRs welcome; keep the script a single dependency-light file.
