"""Premium Library 2.0 contracts: read-only reading desk, existing themes/reader."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("premium_v2", ROOT / "premium_library_v2.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CONTENT = """package eu.kanade.presentation.library.components
import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance
import eu.kanade.presentation.theme.SeluraLibraryTheme

fun LibraryContent(
    onContinueReadingClicked: ((LibraryManga) -> Unit)?,
    getItemsForCategory: (Category) -> List<LibraryItem>,
) {
    val pagerState = rememberPagerState(currentPage) { categories.size }
    if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
        XianxiaArtStrip()
    } else {
        SeluraSkylineHeader()
    }
        PullRefresh(
            refreshing = isRefreshing,
        ) {}
}
"""


class PremiumLibraryV2Contracts(unittest.TestCase):
    def test_exact_source_patch_reuses_existing_manga_and_category_state(self):
        updated = module.transform(CONTENT)
        self.assertIn("val shelfCategory = categories.getOrNull(pagerState.currentPage)", updated)
        self.assertIn("val shelfItems = getItemsForCategory(shelfCategory)", updated)
        self.assertIn("SeirynReadingDesk(", updated)
        self.assertIn("onContinueReading = onContinueReadingClicked", updated)
        self.assertIn("premium != SeluraLibraryTheme.DEFAULT", updated)
        self.assertIn("selection.isEmpty()", updated)
        self.assertIn("searchQuery.isNullOrEmpty()", updated)
        self.assertIn("PullRefresh(", updated)
        with self.assertRaises(module.PremiumLibraryV2PatchError):
            module.transform(updated)

    def test_no_mutations_or_new_cover_decoding_on_shelf(self):
        kt = module.SOURCE.read_text(encoding="utf-8")
        for expected in (
            "summarizeSeirynReadingDesk(items: List<LibraryItem>)",
            "val snapshot = remember(items) { summarizeSeirynReadingDesk(items) }",
            "if (manga.hasStarted && manga.unreadCount > 0L)",
            "val lastRead = manga.lastRead",
            "lastRead > previousRead",
            "onContinueReading(toResume)",
            "if (onContinueReading != null && toResume != null)",
            "manga.title",
            "item.unreadCount.coerceAtLeast(0L)",
        ):
            self.assertIn(expected, kt)
        for excluded in (
            "MangaCover(", "ImageRequest(", "LinearProgressIndicator(",
            "progressBar", "collectAsState(", "getChapterList(", "updateManga(",
            "database.", "delete(", "newCall(", "request(", "WebView(",
            "SortedMap(", ".sortedBy(", "launch(", "readHistory",
        ):
            self.assertNotIn(excluded, kt)

    def test_localized_labels_and_no_forced_default_theme(self):
        labels = ET.fromstring(module.XML)
        items = {x.attrib.get("name"): x.text for x in labels.findall("string")}
        self.assertEqual(
            set(items),
            {"seiryn_library_v2_heading", "seiryn_library_v2_summary", "seiryn_library_v2_resume"},
        )
        self.assertIn("%1$d", items["seiryn_library_v2_summary"])
        self.assertIn("%2$d", items["seiryn_library_v2_summary"])
        self.assertIn("%3$d", items["seiryn_library_v2_summary"])
        self.assertIn("if (premium != SeluraLibraryTheme.DEFAULT", module.NEW)

    def test_in_memory_pinned_source_failure_is_atomic(self):
        for marker in (
            "XianxiaArtStrip()", "SeluraSkylineHeader()",
            "getItemsForCategory: (Category) -> List<LibraryItem>",
            "val pagerState = rememberPagerState(currentPage) { categories.size }",
            "PullRefresh(",
        ):
            with self.subTest(marker=marker):
                with self.assertRaises(module.PremiumLibraryV2PatchError):
                    module.transform(CONTENT.replace(marker, "upstream changed"))

    def test_file_patch_keeps_original_library_on_validation_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("Apache License\n", encoding="utf-8")
            library_file = root / module.CONTENT
            library_file.parent.mkdir(parents=True, exist_ok=True)
            library_file.write_text(CONTENT.replace("XianxiaArtStrip()", "drift()"), encoding="utf-8")
            with self.assertRaises(module.PremiumLibraryV2PatchError):
                module.patch(root)
            self.assertNotIn("SeirynReadingDesk(", library_file.read_text(encoding="utf-8"))
            self.assertFalse((root / module.TARGET).exists())
            self.assertFalse((root / module.STRINGS).exists())

    def test_file_patch_writes_component_and_fails_closed_on_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("Apache License\n", encoding="utf-8")
            lib = root / module.CONTENT
            lib.parent.mkdir(parents=True, exist_ok=True)
            lib.write_text(CONTENT, encoding="utf-8")
            module.patch(root)
            self.assertEqual((root / module.TARGET).read_text(), module.SOURCE.read_text())
            self.assertIn("SeirynReadingDesk(", lib.read_text())
            with self.assertRaises(module.PremiumLibraryV2PatchError):
                module.patch(root)


if __name__ == "__main__":
    unittest.main()
