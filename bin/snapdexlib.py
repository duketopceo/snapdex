"""Pure + IO helpers shared by the snapdex CLI, the plugin controller and tests.

Stdlib only at import time (Pillow/requests are imported lazily by the CLI)
so the plugin helpers and tests run anywhere.
"""
import errno
import json
import os
import re
import shutil
import time
from pathlib import Path

TS = r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}"
# Raw capture. Omarchy 4.x: screenshot-<ts>.png in ~/Pictures.
# Omarchy 4.5 (omasnap): screenshot-<ts>-<slug>.png, saved in ~/Pictures/Screenshots.
EXT = r"(?:png|jpe?g)"
RAW_RE = re.compile(rf"^screenshot-({TS})(?:-(.+))?\.{EXT}$", re.I)
INDEXED_RE = re.compile(rf"^({TS})_(.+)\.{EXT}$", re.I)
# Already-processed PNGs sitting flat in the inbox (what `migrate` moves).
MIGRATE_RE = re.compile(rf"^({TS})_.+\.png$")
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
    cap = re.sub(r"[_-]\d+$", "", m.group(2))  # drop the -2/_2 dedupe suffix
    cap = cap or m.group(2)
    return m.group(1), cap.replace("_", " ").strip()


def sanitize(caption):
    c = str(caption if caption is not None else "screenshot").strip().lower()
    c = re.sub(r"[^a-z0-9_-]+", "_", c)
    c = re.sub(r"_+", "_", c).strip("_")[:CAPTION_MAX]
    return c or "screenshot"


def library_dir(env=None, home=None, config_paths=()):
    """Library root: SNAPDEX_LIBRARY env, then config key "library", then
    <screenshot dir>/Library. Only the "library" key is read from configs."""
    env = os.environ if env is None else env
    if env.get("SNAPDEX_LIBRARY"):
        return Path(env["SNAPDEX_LIBRARY"]).expanduser()
    lib = None
    for path in config_paths:  # later wins
        try:
            v = json.loads(Path(path).read_text()).get("library")
        except (OSError, ValueError, AttributeError):
            continue
        if v:
            lib = v
    if lib:
        return Path(lib).expanduser()
    return screenshot_dirs(env, home)[1] / "Library"


def library_path(library, ts, caption, ext=".png", suffix=""):
    """Library/YYYY/MM/<ts>_<caption>[-N].<ext> for ts = YYYY-MM-DD_HH-MM-SS."""
    return Path(library) / ts[:4] / ts[5:7] / f"{ts}_{caption}{suffix}{ext}"


def unique_target(library, ts, caption, ext=".png", exists=None):
    """First free library_path; collisions get -2, -3, ... (never overwrite)."""
    exists = exists or (lambda p: p.exists())
    dst = library_path(library, ts, caption, ext)
    n = 2
    while exists(dst):
        dst = library_path(library, ts, caption, ext, f"-{n}")
        n += 1
    return dst


def safe_move(src, dst):
    """Move src to a path that does not exist yet; returns the final path.

    Same filesystem: hard-link + unlink (atomic, fails rather than overwrites,
    so a name collision picks the next -N). Cross-filesystem: copy to a temp
    name in the destination dir, then link that into place.
    """
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    n = 2
    cand = dst
    while True:
        try:
            try:
                os.link(src, cand)
            except OSError as e:
                if e.errno != errno.EXDEV:
                    raise
                tmp = cand.with_name(f".{cand.name}.part{os.getpid()}")
                shutil.copy2(src, tmp)
                try:
                    os.link(tmp, cand)
                finally:
                    os.unlink(tmp)
            os.unlink(src)
            return cand
        except FileExistsError:
            cand = dst.with_name(f"{dst.stem}-{n}{dst.suffix}")
            n += 1


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


def library_files(library):
    """Captioned images under the library, sorted by relative path."""
    root = Path(library)
    out = []
    for f in root.rglob("*"):
        rel = f.relative_to(root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if INDEXED_RE.match(f.name) and f.is_file():
            out.append(f)
    return sorted(out, key=lambda f: f.relative_to(root).as_posix())


def build_index(library):
    lines = ["# Screenshots", ""]
    for f in library_files(library):
        rel = f.relative_to(library).as_posix()
        cap = parse_indexed(f.name)[1]
        lines.append(f"- [{f.name}]({rel}) — {cap}")
    return "\n".join(lines) + "\n"


def write_index_if_changed(library):
    """Rewrite Library/index.md only when content differs (keeps path units
    quiet). Written via temp file + rename so readers never see a partial."""
    library = Path(library)
    library.mkdir(parents=True, exist_ok=True)
    path = library / "index.md"
    text = build_index(library)
    try:
        if path.read_text() == text:
            return path, False
    except OSError:
        pass
    tmp = library / f".index.md.{os.getpid()}"
    tmp.write_text(text)
    os.replace(tmp, path)
    return path, True


def migrate(inbox, library, dry_run=False, now=None):
    """Move flat processed PNGs from inbox into Library/YYYY/MM.

    Returns (moves, manifest_path|None); moves = [(old, new)]. The old flat
    index.md (if any) is also moved aside into the library, and recorded.
    """
    inbox, library = Path(inbox), Path(library)
    moves = []
    taken = set()
    for f in sorted(inbox.iterdir()):
        m = MIGRATE_RE.match(f.name)
        if not (m and f.is_file()):
            continue
        ts = m.group(1)
        dst = library_path(library, ts, f.name[len(ts) + 1:-4])
        n = 2
        base = dst
        while dst.exists() or dst in taken:
            dst = base.with_name(f"{base.stem}-{n}{base.suffix}")
            n += 1
        taken.add(dst)
        moves.append((f, dst))
    old_index = inbox / "index.md"
    if moves and old_index.is_file():
        moves.append((old_index, library / ".index.pre-migrate.md"))
    if dry_run:
        return moves, None
    library.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    manifest = library / f".migrate-{stamp}.tsv"
    done = []
    with open(manifest, "w") as mf:
        for old, new in moves:
            final = safe_move(old, new)
            done.append((old, final))
            mf.write(f"{old}\t{final}\n")
            mf.flush()
    write_index_if_changed(library)
    return done, manifest


def undo_migrate(manifest, library):
    """Reverse a migrate manifest. -> (restored, skipped)."""
    restored = skipped = 0
    for line in Path(manifest).read_text().splitlines():
        if "\t" not in line:
            continue
        old, new = (Path(x) for x in line.split("\t", 1))
        if not new.exists() or old.exists():
            skipped += 1
            continue
        safe_move(new, old)
        restored += 1
    write_index_if_changed(library)
    return restored, skipped


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
            "rel": m.group("link").strip(),
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
