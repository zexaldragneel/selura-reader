from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


class ShelfShuffleResourcesTest(unittest.TestCase):
    def test_all_card_labels_resolve_in_android_resources(self):
        assets = Path(__file__).resolve().parents[1] / "obsidian"
        ui = (assets / "SeirynHomeTab.kt").read_text(encoding="utf-8")
        strings = ET.parse(assets / "strings.xml").getroot()
        names = {entry.attrib["name"]: entry.text for entry in strings}
        references = set(re.findall(r"R\.string\.(shuffle_\w+)", ui))
        self.assertIn("shuffle_unread", references)
        self.assertFalse(references - names.keys())
        self.assertIn("%1$d", names["shuffle_unread"])
