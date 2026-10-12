# snapdex design direction: "Contact Sheet"

snapdex is a CLI with no UI. The design surfaces are the README, terminal output, the generated `index.md`, and the logo. Direction: quiet, photographic-darkroom feel: warm paper, dark ink, one safety-orange accent used for "the caption", monospace for everything that is a filename.

## Reference lock (decision ledger)
Refero skill was not used (no UI to research; written directly). References studied conceptually: crop-mark / viewfinder corners (screenshot tools), photographic contact sheets, and snake_case filenames as the product's real output.
- D1: Mark = crop corners + caption bar, because the product is "capture, then name it".
- D2: Monospace wordmark, because output is filenames.
- D3: One accent only; no gradients.

## Tokens
| Token | Light | Dark | Contrast (on bg) |
|---|---|---|---|
| bg | #F6F4EE | #14171A | - |
| ink | #1B1F23 | #EDEAE2 | 15.07 / 14.97 |
| muted | #5B6168 | #9AA0A6 | 5.69 / 6.81 |
| accent | #C2410C | #FB923C | 4.71 / 7.95 (AA) |

Type: JetBrains Mono / Adwaita Mono bold for the wordmark and filenames; system sans for prose.

## Glyph style
Square-capped strokes, 6 on a 64 grid, 16-unit corners; no rounding.

## Motion
None. The CLI prints one line per file (`old -> new`) and a summary; no spinners or colour required. If colour is added later, use the accent for the caption part of the new name only and honour `NO_COLOR`.

## Surfaces
- README: wordmark at top, before/after block.
- Terminal: plain lines, already in place.
- `index.md`: plain list; a thumbnail column is a possible later step.
