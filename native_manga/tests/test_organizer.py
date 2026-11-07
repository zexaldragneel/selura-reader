import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("organizer", ROOT / "organizer.py")
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class OrganizerTests(unittest.TestCase):
    def test_resource_references_resolve(self):
        import re
        names = [s.attrib['name'] for s in ET.parse(patch.ASSETS / 'strings.xml').getroot()]
        self.assertEqual(len(names), len(set(names)))
        for file in patch.ASSETS.glob('*.kt'):
            for name in re.findall(r'R.string.(organizer_\w+)', file.read_text()):
                self.assertIn(name, names)

    def test_failed_patch_does_not_write_partial_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / patch.BASE / 'tachiyomi/ui/home/SeirynHomeTab.kt'
            path.parent.mkdir(parents=True)
            original = 'OutlinedButton(onClick = { tabs.current = LibraryTab })'
            path.write_text(original)
            with self.assertRaises(FileNotFoundError):
                patch.apply(root)
            self.assertEqual(path.read_text(), original)

    def test_persistence_and_downloads_preserve_library(self):
        model = (patch.ASSETS / 'OrganizerViewModel.kt').read_text()
        self.assertIn('downloadCache.changes', model)
        self.assertIn('getDownloadCounts(library.map', model)
        self.assertIn('.commit()', model)
        self.assertIn('mutex.withLock', model)
        for forbidden in ('SetMangaCategories', 'UpdateManga', 'deleteFiles', 'SetReadStatus'):
            self.assertNotIn(forbidden, model)

    def test_ambiguous_anchor_rejected(self):
        with self.assertRaises(ValueError):
            patch.once('anchor anchor', 'anchor', 'replacement')


if __name__ == '__main__':
    unittest.main()

