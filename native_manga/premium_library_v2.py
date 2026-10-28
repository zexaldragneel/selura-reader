#!/usr/bin/env python3
"""Premium Library 2.0 phase 1: read-only Reading Desk for existing themes.

Apply after all current Xianxia/Neon theme patches and before the final
Seiryn branding pass. Fail closed if library component source drifted.
"""
import argparse
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parent / "library_v2" / "SeirynReadingDesk.kt"
TARGET = Path("app/src/main/java/eu/kanade/presentation/library/components/SeirynReadingDesk.kt")
CONTENT = Path("app/src/main/java/eu/kanade/presentation/library/components/LibraryContent.kt")
STRINGS = Path("app/src/main/res/values/seiryn_premium_library_v2_strings.xml")


class PremiumLibraryV2PatchError(RuntimeError):
    pass


XML = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="seiryn_library_v2_heading">YOUR READING DESK</string>
    <string name="seiryn_library_v2_summary">Titles %1$d · Unread chapters %2$d · In progress %3$d</string>
    <string name="seiryn_library_v2_resume">Resume</string>
</resources>
"""


OLD = """        PullRefresh(
            refreshing = isRefreshing,"""

NEW = """        // Premium Library 2.0: show only existing, currently visible category
        // data, without loading covers or changing library/search selection.
        // Keep default Mihon Library display unchanged.
        if (premium != SeluraLibraryTheme.DEFAULT &&
            selection.isEmpty() &&
            searchQuery.isNullOrEmpty()
        ) {
            val shelfCategory = categories.getOrNull(pagerState.currentPage)
            if (shelfCategory != null) {
                val shelfItems = getItemsForCategory(shelfCategory)
                if (shelfItems.isNotEmpty()) {
                    SeirynReadingDesk(
                        items = shelfItems,
                        onContinueReading = onContinueReadingClicked,
                    )
                }
            }
        }

        PullRefresh(
            refreshing = isRefreshing,"""


def transform(source: str) -> str:
    required = [
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance",
        "import eu.kanade.presentation.theme.SeluraLibraryTheme",
        "val pagerState = rememberPagerState(currentPage) { categories.size }",
        "SeluraSkylineHeader()",
        "XianxiaArtStrip()",
        "onContinueReadingClicked: ((LibraryManga) -> Unit)?",
        "getItemsForCategory: (Category) -> List<LibraryItem>",
    ]
    for marker in required:
        if marker not in source:
            raise PremiumLibraryV2PatchError(f"Missing patched library contract: {marker}")
    count = source.count(OLD)
    if count != 1:
        raise PremiumLibraryV2PatchError(f"Expected one PullRefresh block, found {count}")
    if "SeirynReadingDesk(" in source:
        raise PremiumLibraryV2PatchError("Library 2.0 already installed")
    return source.replace(OLD, NEW, 1)


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file():
        raise PremiumLibraryV2PatchError("Licensed pinned native Mihon tree required")
    if not SOURCE.is_file():
        raise PremiumLibraryV2PatchError("Missing Seiryn reading desk component")
    target = root / TARGET
    strings = root / STRINGS
    source = root / CONTENT
    if not source.is_file() or target.exists() or strings.exists():
        raise PremiumLibraryV2PatchError("Existing library source missing or new targets already installed")
    original = source.read_text(encoding="utf-8")
    changed = transform(original)
    # Validate source contracts and target presence before mutating anything.
    target.parent.mkdir(parents=True, exist_ok=True)
    strings.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, target)
    strings.write_text(XML, encoding="utf-8")
    source.write_text(changed, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    patch(parser.parse_args().checkout)
