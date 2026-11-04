"""Pure + IO helpers shared by the snapdex CLI, the plugin controller and tests.

Stdlib only at import time (Pillow/requests are imported lazily by the CLI)
so the plugin helpers and tests run anywhere.
"""
import json
import os
import re
import time
from pathlib import Path

TS = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}"
# Raw capture. Omarchy 4.x: screenshot-<ts>.png in ~/Pictures.
# Omarchy 4.5 (omasnap): screenshot-<ts>-<slug>.png, saved in ~/Pictures/Screenshots.
RAW_RE = re.compile(rf"^screenshot-({TS})(?:-(.+))?\.png$")
INDEXED_RE = re.compile(rf"^({TS})_(.+)\.png$")
INDEX_LINE_RE = re.compile(r"^- \[(?P<name>[^\]]+)\]\((?P<link>[^)]+)\)\s+\S+\s+(?P<cap>.*)$")
CAPTION_MAX = 40


def pictures_dir(env=None, home=None):
    env = os.environ if env is None else env
    home = Path(home) if home else Path.home()
    cfg = Path(env.get("XDG_CONFIG_HOME") or home / ".config") / "user-dirs.dirs"
    try:
        for line in cfg.read_text().splitlines():
            m = re.match(r'\s*XDG_PICTURES_DIR="?([^"]+)"?\s*$', line)
            if m:
                return Path(m.group(1).replace("$HOME", str(home)))
    except OSError:
        pass
    return home / "Pictures"


def screenshot_dirs(env=None, home=None):
    """Return (sources, dest). dest holds the indexed library.

    4.x drops raw shots in the pictures dir; 4.5 (omasnap) saves straight
    into <pictures>/Screenshots (or OMARCHY_SCREENSHOT_DIR). Watch both.
    """
    env = os.environ if env is None else env
    pics = pictures_dir(env, home)
    override = env.get("OMARCHY_SCREENSHOT_DIR") or env.get("OMASNAP_SCREENSHOT_DIR")
    dst = Path(override).expanduser() if override else pics / "Screenshots"
    sources = [pics]
    if dst not in sources:
        sources.append(dst)
    return sources, dst


def parse_raw(name):
    """-> (timestamp, slug_or_None) for an unprocessed capture, else None."""
    m = RAW_RE.match(name)
    return (m.group(1), m.group(2)) if m else None


def parse_indexed(name):
    """-> (timestamp, caption_words) for a processed file, else None."""
    m = INDEXED_RE.match(name)
    if not m:
        return None
    cap = re.sub(r"_\d+$", "", m.group(2))  # drop the _2/_3 dedupe suffix
    cap = cap or m.group(2)
    return m.group(1), cap.replace("_", " ").strip()


def sanitize(caption):
    c = str(caption if caption is not None else "screenshot").strip().lower()
    c = re.sub(r"[^a-z0-9_-]+", "_", c)
    c = re.sub(r"_+", "_", c).strip("_")[:CAPTION_MAX]
    return c or "screenshot"


def unique_target(dst_dir, ts, caption, exists=None):
    exists = exists or (lambda p: p.exists())
    dst = Path(dst_dir) / f"{ts}_{caption}.png"
    n = 2
    while exists(dst):
        dst = Path(dst_dir) / f"{ts}_{caption}_{n}.png"
        n += 1
    return dst


def list_pending(sources, min_age=0.0, since=None, now=None):
    """Raw captures in the source dirs, oldest first.

    min_age skips files still being written; since (epoch) skips older files.
    """
    now = time.time() if now is None else now
    out = []
    for d in sources:
        try:
            entries = list(Path(d).iterdir())
        except OSError:
            continue
        for p in entries:
            if not RAW_RE.match(p.name) or not p.is_file():
                continue
            try:
                mt = p.stat().st_mtime
            except OSError:
                continue
            if now - mt < min_age:
                continue
            if since is not None and mt < since:
                continue
            out.append(p)
    return sorted(out, key=lambda p: (parse_raw(p.name)[0], p.name))


def build_index(dst_dir):
    lines = ["# Screenshots", ""]
    for f in sorted(Path(dst_dir).glob("*.png")):
        if RAW_RE.match(f.name):
            continue  # not captioned yet
        parsed = parse_indexed(f.name)
        cap = parsed[1] if parsed else f.stem.replace("_", " ")
        lines.append(f"- [{f.name}]({f.name}) — {cap}")
    return "\n".join(lines) + "\n"


def write_index_if_changed(dst_dir):
    """Rewrite index.md only when content differs (keeps path units quiet)."""
    path = Path(dst_dir) / "index.md"
    text = build_index(dst_dir)
    try:
        if path.read_text() == text:
            return path, False
    except OSError:
        pass
    path.write_text(text)
    return path, True


def parse_index(text):
    """index.md text -> [{name, caption, ts}] in file order."""
    rows = []
    for line in text.splitlines():
        m = INDEX_LINE_RE.match(line.strip())
        if not m:
            continue
        name = m.group("name")
        parsed = parse_indexed(name)
        rows.append({
            "name": name,
            "caption": m.group("cap").strip(),
            "ts": parsed[0] if parsed else "",
        })
    return rows


def recent(rows, n=12):
    return sorted(rows, key=lambda r: (r["ts"], r["name"]), reverse=True)[:n]


def search(rows, query, limit=50):
    """Case-insensitive AND-match of every query word against caption+name."""
    words = [w for w in re.split(r"[\s_]+", (query or "").lower().strip()) if w]
    if not words:
        return recent(rows, limit)
    hits = []
    for r in rows:
        hay = f"{r['caption']} {r['name']}".lower().replace("_", " ")
        if all(w in hay for w in words):
            hits.append(r)
    return sorted(hits, key=lambda r: (r["ts"], r["name"]), reverse=True)[:limit]
