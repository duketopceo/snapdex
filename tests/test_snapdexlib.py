import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import snapdexlib as lib  # noqa: E402

INDEX = """# Screenshots

- [2026-10-07_16-48-46_slack_chat_interface.png](2026-10-07_16-48-46_slack_chat_interface.png) — slack chat interface
- [2026-10-09_13-15-50_google_sheets_spreadsheet.png](2026-10-09_13-15-50_google_sheets_spreadsheet.png) — google sheets spreadsheet
- [2026-10-11_01-22-00_code_editor_and_registrations_page.png](2026-10-11_01-22-00_code_editor_and_registrations_page.png) — code editor and registrations page
"""


class Names(unittest.TestCase):
    def test_raw_4x(self):
        self.assertEqual(lib.parse_raw("screenshot-2026-11-03_14-40-44.png"),
                         ("2026-11-03_14-40-44", None))

    def test_raw_45_with_slug(self):
        self.assertEqual(lib.parse_raw("screenshot-2026-11-04_00-47-31-herdr-app.png"),
                         ("2026-11-04_00-47-31", "herdr-app"))

    def test_raw_rejects_processed_and_other(self):
        self.assertIsNone(lib.parse_raw("2026-11-03_14-40-44_foo.png"))
        self.assertIsNone(lib.parse_raw("test-panel.png"))

    def test_indexed(self):
        self.assertEqual(lib.parse_indexed("2026-10-07_16-48-46_slack_chat_interface.png"),
                         ("2026-10-07_16-48-46", "slack chat interface"))

    def test_indexed_dedupe_suffix(self):
        self.assertEqual(lib.parse_indexed("2026-10-07_16-48-46_slack_chat_2.png")[1],
                         "slack chat")

    def test_indexed_rejects_raw(self):
        self.assertIsNone(lib.parse_indexed("screenshot-2026-10-07_16-48-46.png"))

    def test_sanitize(self):
        self.assertEqual(lib.sanitize(" Open Router: Logs! "), "open_router_logs")
        self.assertEqual(lib.sanitize(None), "screenshot")
        self.assertEqual(lib.sanitize("???"), "screenshot")
        self.assertLessEqual(len(lib.sanitize("a" * 100)), 40)

    def test_unique_target_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            ts = "2026-01-01_00-00-00"
            t1 = lib.unique_target(d, ts, "x")
            self.assertEqual(t1, Path(d) / "2026" / "01" / f"{ts}_x.png")
            t1.parent.mkdir(parents=True)
            t1.touch()
            t2 = lib.unique_target(d, ts, "x")
            self.assertEqual(t2.name, f"{ts}_x-2.png")
            t2.touch()
            self.assertEqual(lib.unique_target(d, ts, "x").name, f"{ts}_x-3.png")

    def test_safe_move_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "a.png").write_text("new")
            (d / "lib").mkdir()
            (d / "lib" / "b.png").write_text("old")
            final = lib.safe_move(d / "a.png", d / "lib" / "b.png")
            self.assertEqual(final.name, "b-2.png")
            self.assertEqual((d / "lib" / "b.png").read_text(), "old")
            self.assertEqual(final.read_text(), "new")
            self.assertFalse((d / "a.png").exists())

    def test_library_path(self):
        p = lib.library_path("/L", "2026-10-07_16-48-46", "slack_chat")
        self.assertEqual(p, Path("/L/2026/10/2026-10-07_16-48-46_slack_chat.png"))

    def test_library_dir_precedence(self):
        with tempfile.TemporaryDirectory() as h:
            self.assertEqual(lib.library_dir(env={}, home=h),
                             Path(h) / "Pictures" / "Screenshots" / "Library")
            cfg = Path(h) / "c.json"
            cfg.write_text('{"library": "/cfg/lib", "openrouter_api_key": "x"}')
            self.assertEqual(lib.library_dir(env={}, home=h, config_paths=[cfg]),
                             Path("/cfg/lib"))
            self.assertEqual(lib.library_dir(env={"SNAPDEX_LIBRARY": "/env/lib"},
                                             home=h, config_paths=[cfg]),
                             Path("/env/lib"))

    def test_jpg_accepted(self):
        self.assertEqual(lib.parse_raw("screenshot-2026-09-19_14-52-15-low.jpg"),
                         ("2026-09-19_14-52-15", "low"))
        self.assertIsNotNone(lib.parse_raw("screenshot-2026-09-19_14-52-15.jpeg"))
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "screenshot-2026-09-19_14-52-15-low.jpg").touch()
            self.assertEqual([p.name for p in lib.list_pending([d])],
                             ["screenshot-2026-09-19_14-52-15-low.jpg"])


class Migrate(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.inbox = Path(self._td.name)
        self.library = self.inbox / "Library"
        for n in ("2026-10-07_16-48-46_slack_chat.png",
                  "2026-11-01_00-00-00_foo.png"):
            (self.inbox / n).write_text(n)
        (self.inbox / "screenshot-2026-11-04_00-47-31-raw.png").touch()
        (self.inbox / "notes.png").touch()
        (self.inbox / "index.md").write_text("old")

    def tearDown(self):
        self._td.cleanup()

    def test_dry_run_changes_nothing(self):
        moves, manifest = lib.migrate(self.inbox, self.library, dry_run=True)
        self.assertIsNone(manifest)
        self.assertEqual(len([m for m in moves if m[0].suffix == ".png"]), 2)
        self.assertTrue((self.inbox / "2026-10-07_16-48-46_slack_chat.png").exists())
        self.assertFalse(self.library.exists())

    def test_migrate_moves_and_indexes(self):
        moves, manifest = lib.migrate(self.inbox, self.library)
        self.assertTrue((self.library / "2026/10/2026-10-07_16-48-46_slack_chat.png").exists())
        self.assertTrue((self.inbox / "screenshot-2026-11-04_00-47-31-raw.png").exists())
        self.assertTrue((self.inbox / "notes.png").exists())
        self.assertEqual(len(manifest.read_text().splitlines()), len(moves))
        rows = lib.parse_index((self.library / "index.md").read_text())
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertTrue((self.library / r["rel"]).is_file())

    def test_undo_restores(self):
        _, manifest = lib.migrate(self.inbox, self.library)
        restored, skipped = lib.undo_migrate(manifest, self.library)
        self.assertEqual((restored, skipped), (3, 0))
        self.assertEqual((self.inbox / "2026-11-01_00-00-00_foo.png").read_text(),
                         "2026-11-01_00-00-00_foo.png")
        self.assertEqual((self.inbox / "index.md").read_text(), "old")
        self.assertEqual(lib.parse_index((self.library / "index.md").read_text()), [])


class Dirs(unittest.TestCase):
    def test_default_layout(self):
        with tempfile.TemporaryDirectory() as h:
            src, dst = lib.screenshot_dirs(env={}, home=h)
            self.assertEqual(dst, Path(h) / "Pictures" / "Screenshots")
            self.assertEqual(src, [Path(h) / "Pictures", dst])

    def test_override_env(self):
        with tempfile.TemporaryDirectory() as h:
            src, dst = lib.screenshot_dirs(env={"OMARCHY_SCREENSHOT_DIR": "/x/shots"}, home=h)
            self.assertEqual(dst, Path("/x/shots"))

    def test_xdg_pictures(self):
        with tempfile.TemporaryDirectory() as h:
            cfg = Path(h) / ".config"
            cfg.mkdir()
            (cfg / "user-dirs.dirs").write_text('XDG_PICTURES_DIR="$HOME/Img"\n')
            self.assertEqual(lib.pictures_dir(env={}, home=h), Path(h) / "Img")


class Pending(unittest.TestCase):
    def test_pending_filters_and_orders(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for n in ("screenshot-2026-02-01_00-00-00.png",
                      "screenshot-2026-01-01_00-00-00-foot.png",
                      "2026-01-01_00-00-00_done.png", "notes.png"):
                (d / n).touch()
            got = [p.name for p in lib.list_pending([d])]
            self.assertEqual(got, ["screenshot-2026-01-01_00-00-00-foot.png",
                                   "screenshot-2026-02-01_00-00-00.png"])

    def test_min_age_and_since(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            old = d / "screenshot-2026-01-01_00-00-00.png"
            new = d / "screenshot-2026-02-01_00-00-00.png"
            old.touch(); new.touch()
            os.utime(old, (1000, 1000))
            now = time.time()
            self.assertEqual([p.name for p in lib.list_pending([d], since=now - 60)], [new.name])
            self.assertEqual([p.name for p in lib.list_pending([d], min_age=30)], [old.name])

    def test_missing_dir_ignored(self):
        self.assertEqual(lib.list_pending(["/nonexistent-snapdex"]), [])


class IndexAndSearch(unittest.TestCase):
    def setUp(self):
        self.rows = lib.parse_index(INDEX)

    def test_parse_index(self):
        self.assertEqual(len(self.rows), 3)
        self.assertEqual(self.rows[0]["caption"], "slack chat interface")
        self.assertEqual(self.rows[0]["ts"], "2026-10-07_16-48-46")

    def test_recent_newest_first_and_limit(self):
        r = lib.recent(self.rows, 2)
        self.assertEqual([x["ts"][:10] for x in r], ["2026-10-11", "2026-10-09"])

    def test_search_and_match(self):
        self.assertEqual([r["caption"] for r in lib.search(self.rows, "google sheets")],
                         ["google sheets spreadsheet"])
        self.assertEqual(lib.search(self.rows, "slack sheets"), [])

    def test_search_case_and_underscore(self):
        self.assertEqual(len(lib.search(self.rows, "CODE_editor")), 1)

    def test_empty_query_returns_recent(self):
        self.assertEqual(len(lib.search(self.rows, "  ", 2)), 2)

    def test_build_index_roundtrip_skips_raw(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "2026" / "10").mkdir(parents=True)
            (d / "2026/10/2026-10-07_16-48-46_slack_chat.png").touch()
            (d / "screenshot-2026-11-04_00-47-31-herdr-app.png").touch()
            rows = lib.parse_index(lib.build_index(d))
            self.assertEqual([r["caption"] for r in rows], ["slack chat"])
            self.assertEqual(rows[0]["rel"], "2026/10/2026-10-07_16-48-46_slack_chat.png")

    def test_index_written_only_on_change(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "2026-10-07_16-48-46_a.png").touch()  # found via rglob
            self.assertTrue(lib.write_index_if_changed(d)[1])
            self.assertFalse(lib.write_index_if_changed(d)[1])


if __name__ == "__main__":
    unittest.main()
