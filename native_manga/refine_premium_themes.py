#!/usr/bin/env python3
"""Refine the native Selura Library chrome without modifying real manga covers.

Run after apply_branding.py, optimize_reader.py and apply_premium_themes.py
against pinned Mihon v0.21.2 source. Strict replacements fail closed.
"""
from pathlib import Path
import argparse
import shutil

SKYLINE = Path(__file__).resolve().parent / "premium_theme" / "SeluraSkylineHeader.kt"
DEST = "app/src/main/java/eu/kanade/presentation/theme/SeluraSkylineHeader.kt"
FILES = {
    "appbar": "app/src/main/java/eu/kanade/presentation/components/AppBar.kt",
    "toolbar": "app/src/main/java/eu/kanade/presentation/library/components/LibraryToolbar.kt",
    "library": "app/src/main/java/eu/kanade/presentation/library/components/LibraryContent.kt",
    "tabs": "app/src/main/java/eu/kanade/presentation/library/components/LibraryTabs.kt",
    "cards": "app/src/main/java/eu/kanade/presentation/library/components/CommonMangaItem.kt",
    "compact": "app/src/main/java/eu/kanade/presentation/library/components/LibraryCompactGrid.kt",
    "comfortable": "app/src/main/java/eu/kanade/presentation/library/components/LibraryComfortableGrid.kt",
    "grid": "app/src/main/java/eu/kanade/presentation/library/components/LazyLibraryGrid.kt",
    "home": "app/src/main/java/eu/kanade/tachiyomi/ui/home/HomeScreen.kt",
}

class ThemePolishError(RuntimeError):
    pass


def once(source: str, old: str, new: str, path: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise ThemePolishError(
            f"{path}: expected one source marker, got {occurrences}: {old[:85]!r}"
        )
    return source.replace(old, new, 1)


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise ThemePolishError("Pinned native Mihon checkout and LICENSE required")
    if not SKYLINE.is_file() or (root / DEST).exists():
        raise ThemePolishError("Missing Selura skyline source or already installed")
    changed = {}
    for key, path in FILES.items():
        target = root / path
        if not target.is_file():
            raise ThemePolishError(f"Missing original native Kotlin file: {path}")
        changed[key] = target.read_text(encoding="utf-8")

    # The progress feature from the previous visual experiment is removed
    # completely. No progress state or manga cover data is changed.
    k = "cards"
    s = changed[k]
    s = once(s, "import androidx.compose.material3.LinearProgressIndicator\n", "", k)
    s = once(s, """    coverBadgeEnd: @Composable (RowScope.() -> Unit)? = null,
    readCount: Long = 0L,
    totalChapters: Long = 0L,
) {""", """    coverBadgeEnd: @Composable (RowScope.() -> Unit)? = null,
) {""", k)
    s = once(s, """    onClickContinueReading: (() -> Unit)? = null,
    readCount: Long = 0L,
    totalChapters: Long = 0L,
) {""", """    onClickContinueReading: (() -> Unit)? = null,
) {""", k)
    s = once(s, """                PremiumLibraryProgress(
                    readCount = readCount,
                    totalChapters = totalChapters,
                    modifier = Modifier.align(Alignment.BottomCenter),
                )
""", "", k)
    s = once(s, "            PremiumLibraryProgress(readCount = readCount, totalChapters = totalChapters)\n", "", k)
    start = "/**\n * Shows actual read-chapter ratio from existing LibraryManga state;"
    end = "/**\n * Layout of list item."
    if s.count(start) != 1 or s.count(end) != 1:
        raise ThemePolishError("cards: progress function boundaries changed")
    s = s[:s.index(start)] + s[s.index(end):]
    # Borders decorate only the card's container, NOT its real image.
    s = once(s,
        """                        .border(
                            1.dp,
                            if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
                                MaterialTheme.colorScheme.primary.copy(alpha = 0.7f)
                            } else {
                                MaterialTheme.colorScheme.outline.copy(alpha = 0.7f)
                            },
                            cardShape,
                        )""",
        """                        .border(
                            1.dp,
                            Brush.linearGradient(
                                if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
                                    listOf(
                                        Color(0xFFF6D79D),
                                        Color(0xFF8E6938),
                                        Color(0xFFE7C185),
                                    )
                                } else {
                                    listOf(
                                        Color(0xFF8956FB),
                                        Color(0xFF66ABFF),
                                        Color(0xFF47287E),
                                    )
                                },
                            ),
                            cardShape,
                        )""", k)
    changed[k] = s

    for k in ("compact", "comfortable"):
        changed[k] = once(changed[k],
            """                readCount = libraryItem.libraryManga.readCount,
                totalChapters = libraryItem.libraryManga.totalChapters,
""", "", k)

    # A native vector scene in the header: no mock manga or bitmap replacements.
    k = "library"
    s = changed[k]
    s = once(s,
        "import eu.kanade.presentation.theme.seluraLibraryBackground\n",
        "import eu.kanade.presentation.theme.seluraLibraryBackground\n"
        "import eu.kanade.presentation.theme.SeluraSkylineHeader\n", k)
    s = once(s,
        """        // Original ornamental title artwork: typography and shader only,
        // without a large bitmap or additional cover requests.
        if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA &&
            appearance?.backgroundArtwork != false
        ) {
            Text(
                text = "✦  S E L U R A  ✦",
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                textAlign = TextAlign.Center,
                fontFamily = FontFamily.Serif,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.primary.copy(alpha = 0.75f),
            )
        }""",
        """        if (premium != SeluraLibraryTheme.DEFAULT) {
            SeluraSkylineHeader()
        }""", k)
    changed[k] = s

    # Existing generic AppBar still serves Browse/Settings; extend SearchToolbar
    # with an optional color so only the Library can use a transparent skyline.
    k = "appbar"
    s = changed[k]
    s = once(s,
        """fun SearchToolbar(
    searchQuery: String?,
    onChangeSearchQuery: (String?) -> Unit,
    modifier: Modifier = Modifier,
    titleContent:""",
        """fun SearchToolbar(
    searchQuery: String?,
    onChangeSearchQuery: (String?) -> Unit,
    modifier: Modifier = Modifier,
    backgroundColor: Color? = null,
    titleContent:""", k)
    s = once(s,
        """    AppBar(
        modifier = modifier,
        titleContent = {
            if (searchQuery == null) return@AppBar titleContent()""",
        """    AppBar(
        modifier = modifier,
        backgroundColor = backgroundColor,
        titleContent = {
            if (searchQuery == null) return@AppBar titleContent()""", k)
    changed[k] = s

    k = "toolbar"
    s = changed[k]
    s = once(s,
        "import androidx.compose.foundation.isSystemInDarkTheme\n",
        "import androidx.compose.foundation.isSystemInDarkTheme\n"
        "import androidx.compose.foundation.background\n", k)
    s = once(s,
        "import androidx.compose.ui.text.font.FontFamily\n",
        "import androidx.compose.ui.text.font.FontFamily\n"
        "import androidx.compose.ui.graphics.Color\n"
        "import androidx.compose.ui.graphics.Brush\n", k)
    s = once(s,
        """    SearchToolbar(
        titleContent = {""",
        """    SearchToolbar(
        modifier = if (premium != SeluraLibraryTheme.DEFAULT) {
            Modifier.background(
                Brush.horizontalGradient(
                    if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
                        listOf(Color(0xFF101B30), Color(0xFF2C3852), Color(0xFF11192D))
                    } else {
                        listOf(Color(0xFF0E1024), Color(0xFF24184B), Color(0xFF11152C))
                    },
                ),
            )
        } else {
            Modifier
        },
        backgroundColor = if (premium == SeluraLibraryTheme.DEFAULT) null else Color.Transparent,
        titleContent = {""", k)
    changed[k] = s

    # Keep real categories and badge counts, but make the capsule treatment
    # distinct from stock Material tabs. No change in pager or category identity.
    k = "tabs"
    s = changed[k]
    s = once(s, "import androidx.compose.foundation.background\n",
        "import androidx.compose.foundation.background\n"
        "import androidx.compose.foundation.layout.padding\n", k)
    s = once(s, "import androidx.compose.ui.graphics.Color\n",
        "import androidx.compose.ui.graphics.Color\n"
        "import androidx.compose.ui.graphics.Brush\n", k)
    s = once(s,
        """                    Modifier
                        .clip(tabShape)
                        .background(
                            if (isActive) MaterialTheme.colorScheme.primaryContainer
                            else MaterialTheme.colorScheme.surfaceContainer,
                        )
                        .border(
                            1.dp,
                            if (isActive) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.outlineVariant,
                            tabShape,
                        )""",
        """                    Modifier
                        .padding(horizontal = 4.dp, vertical = 4.dp)
                        .clip(tabShape)
                        .background(
                            Brush.horizontalGradient(
                                if (isActive) {
                                    listOf(
                                        MaterialTheme.colorScheme.primaryContainer,
                                        MaterialTheme.colorScheme.primary.copy(alpha = 0.42f),
                                    )
                                } else {
                                    listOf(
                                        MaterialTheme.colorScheme.surfaceContainer,
                                        MaterialTheme.colorScheme.surfaceContainerLow,
                                    )
                                },
                            ),
                        )
                        .border(
                            if (isActive) 1.5.dp else 1.dp,
                            if (isActive) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.outlineVariant,
                            tabShape,
                        )""", k)
    changed[k] = s

    # More breathing room around the real artwork; grid stays lazy and paged.
    k = "grid"
    s = changed[k]
    s = once(s,
        "import tachiyomi.presentation.core.components.FastScrollLazyVerticalGrid\n",
        "import tachiyomi.presentation.core.components.FastScrollLazyVerticalGrid\n"
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\n"
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n", k)
    s = once(s,
        """    FastScrollLazyVerticalGrid(
        columns = if (columns == 0) GridCells.Adaptive(128.dp) else GridCells.Fixed(columns),""",
        """    val premium = LocalSeluraLibraryAppearance.current?.theme != null &&
        LocalSeluraLibraryAppearance.current?.theme != SeluraLibraryTheme.DEFAULT
    FastScrollLazyVerticalGrid(
        columns = if (columns == 0) GridCells.Adaptive(128.dp) else GridCells.Fixed(columns),""", k)
    s = once(s,
        """        verticalArrangement = Arrangement.spacedBy(CommonMangaItemDefaults.GridVerticalSpacer),
        horizontalArrangement = Arrangement.spacedBy(CommonMangaItemDefaults.GridHorizontalSpacer),""",
        """        verticalArrangement = Arrangement.spacedBy(
            if (premium) 10.dp else CommonMangaItemDefaults.GridVerticalSpacer,
        ),
        horizontalArrangement = Arrangement.spacedBy(
            if (premium) 10.dp else CommonMangaItemDefaults.GridHorizontalSpacer,
        ),""", k)
    changed[k] = s

    # Active navigation colors are only visual, with the original navigation
    # callbacks, icons, badges and state still handled by Mihon.
    k = "home"
    s = changed[k]
    s = once(s,
        """        val selected = tabNavigator.current::class == tab::class
        NavigationSuiteItem(""",
        """        val selected = tabNavigator.current::class == tab::class
        val premium = LocalSeluraLibraryAppearance.current?.theme ?: SeluraLibraryTheme.DEFAULT
        NavigationSuiteItem(""", k)
    s = once(s,
        """                    painter = tab.options.icon!!,
                    contentDescription = tab.options.title,""",
        """                    painter = tab.options.icon!!,
                    contentDescription = tab.options.title,
                    tint = if (selected && premium != SeluraLibraryTheme.DEFAULT) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        if (premium == SeluraLibraryTheme.DEFAULT) {
                            androidx.compose.material3.LocalContentColor.current
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    },""", k)
    s = once(s,
        """                    style = MaterialTheme.typography.labelLarge,
                    maxLines = 1,""",
        """                    style = if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
                        MaterialTheme.typography.labelLarge.copy(
                            fontFamily = androidx.compose.ui.text.font.FontFamily.Serif,
                        )
                    } else {
                        MaterialTheme.typography.labelLarge
                    },
                    color = if (selected && premium != SeluraLibraryTheme.DEFAULT) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        if (premium == SeluraLibraryTheme.DEFAULT) {
                            androidx.compose.material3.LocalContentColor.current
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        }
                    },
                    maxLines = 1,""", k)
    changed[k] = s

    # Guards on the final render: do not touch the real cover source, reader,
    # image pipeline, DB, chapters, or original Mihon extension identifiers.
    for key, result in changed.items():
        if key == "cards" and "PremiumLibraryProgress" in result:
            raise ThemePolishError("Unexpected manga-card progress overlay remains")
        if result == (root / FILES[key]).read_text(encoding="utf-8"):
            raise ThemePolishError(f"No change in expected UI file {key}")
    for key, result in changed.items():
        (root / FILES[key]).write_text(result, encoding="utf-8")
    target = root / DEST
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SKYLINE, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
