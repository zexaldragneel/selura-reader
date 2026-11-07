#!/usr/bin/env python3
"""Integrated Obsidian screens on the pinned engine, after premium_library_v2.

Only presentation and a read-only Home ViewModel are changed. Validate every
source replacement before writing any file; duplicate application fails closed.
"""
import argparse
from pathlib import Path

BASE = "app/src/main/java/eu/kanade/"
ASSETS = Path(__file__).resolve().parent / "obsidian"


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Obsidian source contract changed: {old[:100]!r}")
    return text.replace(old, new, 1)


def apply(root):
    root = Path(root)
    if not (root / "LICENSE").is_file():
        raise ValueError("Licensed pinned engine required")
    changed = {}

    def read(path):
        return (root / path).read_text(encoding="utf-8")

    p = BASE + "tachiyomi/ui/home/HomeScreen.kt"
    s = read(p)
    s = once(s, "        val navigator = LocalNavigator.currentOrThrow\n        TabNavigator(", "        val navigator = LocalNavigator.currentOrThrow\n        val dashboardEnabled = LocalSeluraLibraryAppearance.current?.theme == SeluraLibraryTheme.SEIRYN_OBSIDIAN\n        TabNavigator(")
    s = once(s, "        LibraryTab,\n        UpdatesTab,", "        SeirynHomeTab,\n        LibraryTab,\n        UpdatesTab,")
    s = once(s, "            tab = LibraryTab,", "            tab = if (dashboardEnabled) SeirynHomeTab else LibraryTab,")
    s = once(s, "                        TABS.fastForEach { NavigationSuiteItem(it, navigationSuiteType) }", """                        val obsidian = appearance?.theme == SeluraLibraryTheme.SEIRYN_OBSIDIAN
                        TABS.filter {
                            if (obsidian) it != HistoryTab else it != SeirynHomeTab
                        }.fastForEach { NavigationSuiteItem(it, navigationSuiteType) }""")
    s = once(s, "            val goToLibraryTab = { tabNavigator.current = LibraryTab }", """            val startTab = if (dashboardEnabled) SeirynHomeTab else LibraryTab
            val goToLibraryTab = { tabNavigator.current = LibraryTab }""")
    s = once(s, "            BackHandler(enabled = tabNavigator.current != LibraryTab, onBack = goToLibraryTab)", "            BackHandler(enabled = tabNavigator.current != startTab) { tabNavigator.current = startTab }")
    # Changing theme while a dashboard is open must not strand an invisible tab.
    s = once(s, "            val startTab = if", """            LaunchedEffect(dashboardEnabled) {
                if (!dashboardEnabled &&
                    tabNavigator.current == SeirynHomeTab
                ) tabNavigator.current = LibraryTab
            }
            val startTab = if""")
    changed[p] = s

    p = BASE + "presentation/library/components/LibraryContent.kt"
    s = read(p)
    s = once(s, "    searchQuery: String?,", "    searchQuery: String?,\n    onSearchQueryChange: (String?) -> Unit,")
    s = once(s, "        } else if (premium != SeluraLibraryTheme.DEFAULT) {\n            SeluraSkylineHeader()", "        } else if (premium != SeluraLibraryTheme.DEFAULT && premium != SeluraLibraryTheme.SEIRYN_OBSIDIAN) {\n            SeluraSkylineHeader()")
    s = once(s, "        val pagerState = rememberPagerState(currentPage)", """        if (premium == SeluraLibraryTheme.SEIRYN_OBSIDIAN && selection.isEmpty()) {
            SeirynLibrarySearch(searchQuery, onSearchQueryChange, hasActiveFilters)
        }
        val pagerState = rememberPagerState(currentPage)""")
    s = once(s, "        if (premium != SeluraLibraryTheme.DEFAULT &&\n            selection.isEmpty()", "        if (premium != SeluraLibraryTheme.DEFAULT &&\n            premium != SeluraLibraryTheme.SEIRYN_OBSIDIAN &&\n            selection.isEmpty()")
    changed[p] = s

    p = BASE + "presentation/library/components/LibraryPager.kt"
    s = read(p)
    s = once(s, "import eu.kanade.tachiyomi.ui.library.LibraryItem", "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\nimport eu.kanade.presentation.theme.SeluraLibraryTheme\nimport eu.kanade.tachiyomi.ui.library.LibraryItem")
    s = once(s, "        val onClickManga: (LibraryManga) -> Unit = { onClickManga(category, it) }\n        val onLongClickManga: (LibraryManga) -> Unit = { onLongClickManga(category, it) }\n\n        when (displayMode)", """        val onClickManga: (LibraryManga) -> Unit = { onClickManga(category, it) }
        val onLongClickManga: (LibraryManga) -> Unit = { onLongClickManga(category, it) }
        val obsidian = LocalSeluraLibraryAppearance.current?.theme == SeluraLibraryTheme.SEIRYN_OBSIDIAN
        if (obsidian) {
            SeirynLibraryGrid(
                items = items,
                contentPadding = contentPadding,
                selection = selection,
                onClick = onClickManga,
                onLongClick = onLongClickManga,
                onContinueReading = onClickContinueReading,
                searchQuery = searchQuery,
                onGlobalSearch = onGlobalSearchClicked,
            )
            return@HorizontalPager
        }

        when (displayMode)""")
    changed[p] = s
    p = BASE + "tachiyomi/ui/library/LibraryTab.kt"
    s = read(p)
    s = once(s, "                    LibraryContent(\n", "                    LibraryContent(\n                        onSearchQueryChange = viewModel::search,\n")
    changed[p] = s

    p = BASE + "presentation/library/components/CommonMangaItem.kt"
    s = read(p)
    s = once(s, "listOf(\n                                        Color(0xFF8956FB),", """if (premium == SeluraLibraryTheme.SEIRYN_OBSIDIAN) listOf(
                                        Color(0xFF9B7B43), Color(0xFF38332B), Color(0xFFF1C66D),
                                    ) else listOf(
                                        Color(0xFF8956FB),""")
    changed[p] = s

    p = BASE + "presentation/manga/components/MangaInfoHeader.kt"
    s = read(p)
    s = once(s, "import eu.kanade.tachiyomi.R", "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\nimport eu.kanade.presentation.theme.SeluraLibraryTheme\nimport androidx.compose.foundation.shape.RoundedCornerShape\nimport androidx.compose.foundation.layout.width\nimport eu.kanade.tachiyomi.R")
    s = once(s, "    Box(modifier = modifier) {\n        // Backdrop", """    val obsidian = LocalSeluraLibraryAppearance.current?.theme == SeluraLibraryTheme.SEIRYN_OBSIDIAN
    Box(modifier = modifier) {
        // Backdrop""")
    s = once(s, ".blur(4.dp)\n                .alpha(0.2f)", ".blur(if (obsidian) 0.dp else 4.dp)\n                .alpha(if (obsidian) 0.45f else 0.2f)")
    s = once(s, "            if (!isTabletUi) {\n                MangaAndSourceTitlesSmall(", """            if (obsidian) {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, top = appBarPadding + 24.dp, bottom = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp),
                ) {
                    Text("S E I R Y N  /  LIBRARY", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                    MangaCover.Book(
                        data = manga,
                        modifier = Modifier.width(if (isTabletUi) 180.dp else 144.dp),
                        shape = RoundedCornerShape(18.dp),
                        contentDescription = stringResource(MR.strings.manga_cover),
                        onClick = onCoverClick,
                    )
                    MangaContentInfo(
                        title = manga.title, author = manga.author, artist = manga.artist,
                        status = manga.status, source = source, isStubSource = isStubSource,
                        doSearch = doSearch,
                    )
                }
            } else if (!isTabletUi) {
                MangaAndSourceTitlesSmall(""")
    changed[p] = s

    p = BASE + "presentation/manga/MangaScreen.kt"
    s = read(p)
    s = once(s, "import eu.kanade.presentation.manga.components.MangaInfoBox", "import eu.kanade.presentation.manga.components.SeirynDetailActions\nimport eu.kanade.presentation.manga.components.MangaInfoBox")
    # Both phone and tablet retain every existing chapter control and selection callback.
    marker = "                            doSearch = onSearch,\n                        )"
    if s.count(marker) != 2:
        raise ValueError("Phone/tablet details contract changed")
    s = s.replace(marker, marker + """
                        SeirynDetailActions(
                            chapters = state.chapters,
                            onContinue = onContinueReading,
                            onFilter = """ + "ON_FILTER" + """,
                            sourceUnavailable = state.source is StubSource,
                            onFindSource = onMigrateClicked,
                        )""")
    # Phone and tablet parameter names differ.
    s = s.replace("onFilter = ON_FILTER", "onFilter = onFilterClicked", 1)
    s = s.replace("onFilter = ON_FILTER", "onFilter = onFilterButtonClicked", 1)
    changed[p] = s

    p = BASE + "presentation/manga/components/MangaChapterListItem.kt"
    s = read(p)
    s = once(s, "import androidx.compose.foundation.combinedClickable", "import androidx.compose.foundation.background\nimport androidx.compose.foundation.border\nimport androidx.compose.foundation.shape.RoundedCornerShape\nimport eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\nimport eu.kanade.presentation.theme.SeluraLibraryTheme\nimport androidx.compose.foundation.combinedClickable")
    s = once(s, "    val start = getSwipeAction(", "    val obsidian = LocalSeluraLibraryAppearance.current?.theme == SeluraLibraryTheme.SEIRYN_OBSIDIAN\n    val start = getSwipeAction(")
    s = once(s, "            modifier = modifier\n                .selectedBackground(selected)", """            modifier = modifier
                .then(if (obsidian) Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
                    .background(MaterialTheme.colorScheme.surfaceContainerLow, RoundedCornerShape(16.dp))
                    .border(1.dp, if (bookmark) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(16.dp)) else Modifier)
                .selectedBackground(selected)""")
    changed[p] = s

    p = BASE + "presentation/reader/appbars/ReaderAppBars.kt"
    s = read(p)
    s = once(s, "import androidx.compose.material3.MaterialTheme", "import androidx.compose.material3.Text\nimport androidx.compose.material3.LinearProgressIndicator\nimport androidx.compose.ui.res.stringResource\nimport eu.kanade.tachiyomi.R\nimport eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\nimport eu.kanade.presentation.theme.SeluraLibraryTheme\nimport androidx.compose.material3.MaterialTheme")
    s = once(s, "    val backgroundColor = MaterialTheme.colorScheme", "    val obsidian = LocalSeluraLibraryAppearance.current?.theme == SeluraLibraryTheme.SEIRYN_OBSIDIAN\n    val backgroundColor = MaterialTheme.colorScheme")
    s = once(s, "            Column(verticalArrangement = Arrangement.spacedBy(MaterialTheme.padding.small)) {", """            Column(verticalArrangement = Arrangement.spacedBy(MaterialTheme.padding.small)) {
                if (obsidian && totalPages > 0) {
                    Column(
                        Modifier.fillMaxWidth().background(MaterialTheme.colorScheme.surfaceContainerLowest).padding(horizontal = 24.dp, vertical = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                            Text(stringResource(R.string.seiryn_reader_focus), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                            Text(stringResource(R.string.seiryn_reader_progress, currentPage, totalPages,
                                (currentPage.toLong() * 100 / totalPages).toInt().coerceIn(0, 100)), style = MaterialTheme.typography.labelMedium)
                        }
                        LinearProgressIndicator(
                            progress = { (currentPage.toFloat() / totalPages).coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth(),
                            color = MaterialTheme.colorScheme.primary,
                            trackColor = MaterialTheme.colorScheme.outlineVariant,
                        )
                    }
                }""")
    changed[p] = s

    p = BASE + "presentation/reader/appbars/ReaderBottomBar.kt"
    s = read(p)
    s = once(s, "import androidx.compose.foundation.layout.Row", "import androidx.compose.foundation.layout.Column\nimport androidx.compose.material3.Text\nimport androidx.compose.material3.MaterialTheme\nimport eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\nimport eu.kanade.presentation.theme.SeluraLibraryTheme\nimport androidx.compose.foundation.layout.Row")
    s = once(s, "    Row(\n", """    if (LocalSeluraLibraryAppearance.current?.theme == SeluraLibraryTheme.SEIRYN_OBSIDIAN) {
        Row(modifier = modifier, horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
            ReaderTool(readingMode.icon, stringResource(MR.strings.viewer), onClickReadingMode, Modifier.weight(1f))
            ReaderTool(orientation.icon, stringResource(MR.strings.rotation_type), onClickOrientation, Modifier.weight(1f))
            ReaderTool(if (cropEnabled) MaterialSymbols.Rounded.Crop else CustomMaterialSymbols.Rounded.CropOff,
                stringResource(MR.strings.pref_crop_borders), onClickCropBorder, Modifier.weight(1f))
            ReaderTool(MaterialSymbols.Rounded.Settings, stringResource(MR.strings.action_settings), onClickSettings, Modifier.weight(1f))
        }
        return
    }
    Row(
""")
    s += '''
@Composable
private fun ReaderTool(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, onClick: () -> Unit, modifier: Modifier) {
    androidx.compose.material3.TextButton(onClick = onClick, modifier = modifier) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(icon, contentDescription = null)
            Text(label, style = MaterialTheme.typography.labelSmall, maxLines = 2, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
        }
    }
}
'''
    changed[p] = s

    copies = {
        "SeirynHomeIcon.kt": BASE + "tachiyomi/ui/home/SeirynHomeIcon.kt",
        "SeirynHomeViewModel.kt": BASE + "tachiyomi/ui/home/SeirynHomeViewModel.kt",
        "SeirynHomeTab.kt": BASE + "tachiyomi/ui/home/SeirynHomeTab.kt",
        "SeirynDetailActions.kt": BASE + "presentation/manga/components/SeirynDetailActions.kt",
        "SeirynLibrarySearch.kt": BASE + "presentation/library/components/SeirynLibrarySearch.kt",
        "SeirynLibraryGrid.kt": BASE + "presentation/library/components/SeirynLibraryGrid.kt",
        "strings.xml": "app/src/main/res/values/seiryn_obsidian_strings.xml",
    }
    for source, target in copies.items():
        if (root / target).exists():
            raise ValueError(f"Obsidian already installed: {target}")
        changed[target] = (ASSETS / source).read_text(encoding="utf-8")
    for path, content in changed.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    apply(parser.parse_args().checkout)
