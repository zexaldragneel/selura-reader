import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

MODULE = Path(__file__).resolve().parents[1] / "obsidian_ui.py"
spec = importlib.util.spec_from_file_location("obsidian_ui", MODULE)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class ObsidianPatchTests(unittest.TestCase):
    def test_rejects_ambiguous_source_marker(self):
        for source in ("absent", "same same"):
            with self.assertRaises(ValueError):
                patch.once(source, "same", "changed")

    def test_missing_engine_does_not_create_partial_ui(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("Apache License")
            with self.assertRaises(FileNotFoundError):
                patch.apply(root)
            self.assertEqual([p.name for p in root.iterdir()], ["LICENSE"])

    def test_resources_parse_and_have_unique_names(self):
        strings = ET.parse(patch.ASSETS / "strings.xml").getroot()
        names = [s.attrib["name"] for s in strings]
        self.assertEqual(len(names), len(set(names)))
        for source in patch.ASSETS.glob("*.kt"):
            import re
            for name in re.findall(r"R.string.(seiryn_\w+)", source.read_text()):
                self.assertIn(name, names)

    def test_resume_uses_history_chapter_and_preserves_cancellation(self):
        model = (patch.ASSETS / "SeirynHomeViewModel.kt").read_text()
        ui = (patch.ASSETS / "SeirynHomeTab.kt").read_text()
        self.assertIn("history.mangaId, history.chapterId, onlyUnread = false", model)
        self.assertIn("catch (e: CancellationException) { throw e }", ui)
        self.assertIn("ReaderActivity.newIntent(context, chapter.mangaId, chapter.id)", ui)
        # No dashboard write path may mutate a library or mark chapters read.
        for forbidden in ("UpdateManga", "SetReadStatus", "SetMangaCategories", "RemoveHistory", "DownloadManager"):
            self.assertNotIn(forbidden, model)


if __name__ == "__main__":
    unittest.main()
