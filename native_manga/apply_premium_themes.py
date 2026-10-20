#!/usr/bin/env python3
"""Apply native Compose premium themes to the pinned Mihon checkout.

Fail closed when any expected upstream text changes. The patch only touches
presentation source files and never edits reader, source, download or DB code.
"""
from pathlib import Path
import argparse
import shutil

THEME_SRC = Path(__file__).resolve().parent / "premium_theme" / "SeluraPremiumTheme.kt"
THEME_DST = "app/src/main/java/eu/kanade/presentation/theme/SeluraPremiumTheme.kt"

FILES = {
    "theme": "app/src/main/java/eu/kanade/presentation/theme/TachiyomiTheme.kt",
    "settings": "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsAppearanceScreen.kt",
    "tabs": "app/src/main/java/eu/kanade/presentation/library/components/LibraryTabs.kt",
    "library": "app/src/main/java/eu/kanade/presentation/library/components/LibraryContent.kt",
    "cards": "app/src/main/java/eu/kanade/presentation/library/components/CommonMangaItem.kt",
    "compact": "app/src/main/java/eu/kanade/presentation/library/components/LibraryCompactGrid.kt",
    "comfortable": "app/src/main/java/eu/kanade/presentation/library/components/LibraryComfortableGrid.kt",
    "toolbar": "app/src/main/java/eu/kanade/presentation/library/components/LibraryToolbar.kt",
    "home": "app/src/main/java/eu/kanade/tachiyomi/ui/home/HomeScreen.kt",
}

class PremiumThemePatchError(RuntimeError):
    pass


def once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise PremiumThemePatchError(
            f"{label}: expected one upstream marker, found {count}: {old[:90]!r}"
        )
    return source.replace(old, new, 1)


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "gradlew").exists() or not (root / "LICENSE").exists():
        raise PremiumThemePatchError("A complete licensed native Mihon checkout is required")
    if (root / THEME_DST).exists():
        raise PremiumThemePatchError("Premium theme already exists; refusing to overwrite")
    if not THEME_SRC.is_file():
        raise PremiumThemePatchError("Missing Selura-owned Compose theme implementation")

    files = {}
    for key, filename in FILES.items():
        file = root / filename
        if not file.is_file():
            raise PremiumThemePatchError(f"Missing upstream Kotlin source: {filename}")
        files[key] = file.read_text(encoding="utf-8")

    key = "theme"
    s = files[key]
    s = once(s,
        "import androidx.compose.runtime.Composable\nimport androidx.compose.runtime.remember\n",
        "import androidx.compose.runtime.Composable\nimport androidx.compose.runtime.CompositionLocalProvider\nimport androidx.compose.runtime.remember\n", key)
    s = once(s,
        """    val context = LocalContext.current
    val isDark = isSystemInDarkTheme()
    MaterialExpressiveTheme(
        colorScheme = remember(appTheme, isDark, isAmoled) {
            getThemeColorScheme(
                context = context,
                appTheme = appTheme,
                isDark = isDark,
                isAmoled = isAmoled,
            )
        },
        content = content,
    )""",
        """    val context = LocalContext.current
    val isDark = isSystemInDarkTheme()
    // Selura premium selector is live and stored independently of Mihon DB data.
    val premiumAppearance = remember(context) { SeluraLibraryAppearance(context) }
    val premiumSelection = premiumAppearance.theme
    val colorScheme = remember(appTheme, isDark, isAmoled, premiumSelection) {
        seluraColorScheme(
            getThemeColorScheme(context, appTheme, isDark, isAmoled),
            premiumSelection,
        )
    }
    CompositionLocalProvider(LocalSeluraLibraryAppearance provides premiumAppearance) {
        MaterialExpressiveTheme(
            colorScheme = colorScheme,
            content = content,
        )
    }""", key)
    files[key] = s

    key = "settings"
    s = files[key]
    s = once(s,
        "import eu.kanade.presentation.more.settings.Preference\n",
        "import eu.kanade.presentation.more.settings.Preference\n"
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\n"
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n", key)
    s = once(s,
        """        val amoled by amoledPref.collectAsState()

        return Preference.PreferenceGroup(""",
        """        val amoled by amoledPref.collectAsState()
        val premiumAppearance = LocalSeluraLibraryAppearance.current

        return Preference.PreferenceGroup(""", key)
    s = once(s,
        """            preferenceItems = listOf(
                Preference.PreferenceItem.CustomPreference(""",
        """            preferenceItems = listOf(
                // Selura: lightweight persistent display-only preferences.
                // They do not touch chapter, source, migration or library data.
                Preference.PreferenceItem.BasicListPreference(
                    value = premiumAppearance?.theme?.key ?: SeluraLibraryTheme.DEFAULT.key,
                    entries = SeluraLibraryTheme.entries.associate { it.key to it.label },
                    title = "Library theme",
                    onValueChanged = { premiumAppearance?.selectTheme(it) },
                ),
                Preference.PreferenceItem.BasicListPreference(
                    value = if (premiumAppearance?.backgroundArtwork != false) "on" else "off",
                    entries = mapOf("on" to "Enabled", "off" to "Disabled"),
                    title = "Atmospheric background",
                    subtitle = "%s · Original lightweight gradient artwork",
                    onValueChanged = { premiumAppearance?.setBackgroundArtwork(it == "on") },
                ),
                Preference.PreferenceItem.BasicListPreference(
                    value = if (premiumAppearance?.reducedEffects == true) "on" else "off",
                    entries = mapOf("on" to "Reduced", "off" to "Normal"),
                    title = "Visual effects",
                    onValueChanged = { premiumAppearance?.setReducedEffects(it == "on") },
                ),
                Preference.PreferenceItem.CustomPreference(""", key)
    files[key] = s

    key = "tabs"
    s = files[key]
    s = once(s,
        "import androidx.compose.foundation.pager.PagerState\n",
        "import androidx.compose.foundation.background\n"
        "import androidx.compose.foundation.border\n"
        "import androidx.compose.foundation.pager.PagerState\n"
        "import androidx.compose.foundation.shape.RoundedCornerShape\n", key)
    s = once(s,
        "import androidx.compose.runtime.Composable\n",
        "import androidx.compose.runtime.Composable\n"
        "import androidx.compose.ui.Modifier\n"
        "import androidx.compose.ui.draw.clip\n"
        "import androidx.compose.ui.graphics.Color\n"
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\n"
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n", key)
    s = once(s,
        """    val currentPageIndex = pagerState.currentPage.coerceAtMost(categories.lastIndex)
    PrimaryScrollableTabRow(""",
        """    val currentPageIndex = pagerState.currentPage.coerceAtMost(categories.lastIndex)
    val premium = LocalSeluraLibraryAppearance.current?.theme ?: SeluraLibraryTheme.DEFAULT
    val custom = premium != SeluraLibraryTheme.DEFAULT
    val tabShape = RoundedCornerShape(18.dp)
    PrimaryScrollableTabRow(""", key)
    s = once(s,
        """        edgePadding = 0.dp,
    ) {""",
        """        edgePadding = 0.dp,
        containerColor = if (custom) Color.Transparent else MaterialTheme.colorScheme.surface,
    ) {""", key)
    s = once(s,
        """            Tab(
                selected = currentPageIndex == index,""",
        """            val isActive = currentPageIndex == index
            Tab(
                modifier = if (custom) {
                    Modifier
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
                        )
                } else {
                    Modifier
                },
                selectedContentColor = MaterialTheme.colorScheme.primary,
                selected = isActive,""", key)
    files[key] = s

    key = "library"
    s = files[key]
    s = once(s,
        "import androidx.compose.foundation.layout.Column\n",
        "import androidx.compose.foundation.background\n"
        "import androidx.compose.foundation.layout.Column\n"
        "import androidx.compose.foundation.layout.fillMaxSize\n"
        "import androidx.compose.foundation.layout.fillMaxWidth\n", key)
    s = once(s,
        "import androidx.compose.runtime.Composable\n",
        "import androidx.compose.material3.MaterialTheme\n"
        "import androidx.compose.material3.Text\n"
        "import androidx.compose.runtime.Composable\n"
        "import androidx.compose.ui.text.font.FontFamily\n"
        "import androidx.compose.ui.text.style.TextAlign\n"
        "import androidx.compose.ui.unit.dp\n"
        "import androidx.compose.ui.unit.sp\n"
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\n"
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n"
        "import eu.kanade.presentation.theme.seluraLibraryBackground\n", key)
    s = once(s,
        """    Column(
        modifier = Modifier.padding(""",
        """    val appearance = LocalSeluraLibraryAppearance.current
    val premium = appearance?.theme ?: SeluraLibraryTheme.DEFAULT
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(seluraLibraryBackground(premium, appearance?.backgroundArtwork != false))
            .padding(""", key)
    s = once(s,
        """        val pagerState = rememberPagerState(currentPage) { categories.size }""",
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
        }
        val pagerState = rememberPagerState(currentPage) { categories.size }""", key)
    files[key] = s

    key = "cards"
    s = files[key]
    s = once(s,
        "import androidx.compose.foundation.background\n",
        "import androidx.compose.foundation.background\nimport androidx.compose.foundation.border\n", key)
    s = once(s,
        "import eu.kanade.presentation.manga.components.MangaCover\n",
        "import eu.kanade.presentation.manga.components.MangaCover\n"
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\n"
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n", key)
    s = once(s,
        """    Box(
        modifier = modifier
            .clip(MaterialTheme.shapes.small)
            .combinedClickable(""",
        """    val premium = LocalSeluraLibraryAppearance.current?.theme ?: SeluraLibraryTheme.DEFAULT
    val isPremium = premium != SeluraLibraryTheme.DEFAULT
    val cardShape = if (isPremium) RoundedCornerShape(14.dp) else MaterialTheme.shapes.small
    Box(
        modifier = modifier
            .clip(cardShape)
            .then(
                if (isPremium) {
                    Modifier
                        .background(MaterialTheme.colorScheme.surfaceContainerLow)
                        .border(
                            1.dp,
                            if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
                                MaterialTheme.colorScheme.primary.copy(alpha = 0.7f)
                            } else {
                                MaterialTheme.colorScheme.outline.copy(alpha = 0.7f)
                            },
                            cardShape,
                        )
                } else {
                    Modifier
                },
            )
            .combinedClickable(""", key)
    s = once(s,
        """            .selectedOutline(isSelected = isSelected, color = MaterialTheme.colorScheme.secondary)
            .padding(4.dp),""",
        """            .selectedOutline(isSelected = isSelected, color = MaterialTheme.colorScheme.secondary)
            .padding(if (isPremium) 3.dp else 4.dp),""", key)

    s = once(s,
        "import androidx.compose.material3.FilledIconButton\n",
        "import androidx.compose.material3.FilledIconButton\n"
        "import androidx.compose.material3.LinearProgressIndicator\n", key)
    s = once(s,
        """    coverBadgeEnd: @Composable (RowScope.() -> Unit)? = null,
) {
    GridItemSelectable(""",
        """    coverBadgeEnd: @Composable (RowScope.() -> Unit)? = null,
    readCount: Long = 0L,
    totalChapters: Long = 0L,
) {
    GridItemSelectable(""", key)
    s = once(s,
        """            },
        )
    }
}

/**
 * Title overlay for [MangaCompactGridItem]""",
        """                PremiumLibraryProgress(
                    readCount = readCount,
                    totalChapters = totalChapters,
                    modifier = Modifier.align(Alignment.BottomCenter),
                )
            },
        )
    }
}

/**
 * Title overlay for [MangaCompactGridItem]""", key)
    s = once(s,
        """    onClickContinueReading: (() -> Unit)? = null,
) {
    GridItemSelectable(""",
        """    onClickContinueReading: (() -> Unit)? = null,
    readCount: Long = 0L,
    totalChapters: Long = 0L,
) {
    GridItemSelectable(""", key)
    s = once(s,
        """                maxLines = titleMaxLines,
            )
        }
    }
}

/**
 * Common cover layout""",
        """                maxLines = titleMaxLines,
            )
            PremiumLibraryProgress(readCount = readCount, totalChapters = totalChapters)
        }
    }
}

/**
 * Common cover layout""", key)
    s = once(s,
        """/**
 * Layout of list item.
 */""",
        """/**
 * Shows actual read-chapter ratio from existing LibraryManga state; it never
 * infers chapter count from a cover, chapter label or source title.
 */
@Composable
private fun PremiumLibraryProgress(
    readCount: Long,
    totalChapters: Long,
    modifier: Modifier = Modifier,
) {
    val appearance = LocalSeluraLibraryAppearance.current
    if (appearance?.theme == null ||
        appearance.theme == SeluraLibraryTheme.DEFAULT ||
        totalChapters <= 0L
    ) return
    val fraction = (readCount.toFloat() / totalChapters.toFloat()).coerceIn(0f, 1f)
    Row(
        modifier = modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        LinearProgressIndicator(
            progress = { fraction },
            modifier = Modifier.weight(1f).height(4.dp),
            color = MaterialTheme.colorScheme.primary,
            trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
        )
        Text(
            text = ((fraction * 100).toInt()).toString() + "%",
            modifier = Modifier.padding(start = 6.dp),
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

/**
 * Layout of list item.
 */""", key)
    files[key] = s

    key = "compact"
    s = files[key]
    s = once(s,
        """            MangaCompactGridItem(
                isSelected = manga.id in selection,""",
        """            MangaCompactGridItem(
                readCount = libraryItem.libraryManga.readCount,
                totalChapters = libraryItem.libraryManga.totalChapters,
                isSelected = manga.id in selection,""", key)
    files[key] = s

    key = "comfortable"
    s = files[key]
    s = once(s,
        """            MangaComfortableGridItem(
                isSelected = manga.id in selection,""",
        """            MangaComfortableGridItem(
                readCount = libraryItem.libraryManga.readCount,
                totalChapters = libraryItem.libraryManga.totalChapters,
                isSelected = manga.id in selection,""", key)
    files[key] = s

    key = "toolbar"
    s = files[key]
    s = once(s,
        "import androidx.compose.ui.text.style.TextOverflow\n",
        "import androidx.compose.ui.text.style.TextOverflow\n"
        "import androidx.compose.ui.text.font.FontFamily\n"
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\n"
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n", key)
    s = once(s,
        """    val pillAlpha = if (isSystemInDarkTheme()) 0.12f else 0.08f
    SearchToolbar(""",
        """    val pillAlpha = if (isSystemInDarkTheme()) 0.12f else 0.08f
    val premium = LocalSeluraLibraryAppearance.current?.theme ?: SeluraLibraryTheme.DEFAULT
    SearchToolbar(""", key)
    s = once(s,
        """                    text = title.text,
                    maxLines = 1,""",
        """                    text = title.text,
                    style = if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
                        MaterialTheme.typography.headlineSmall.copy(fontFamily = FontFamily.Serif)
                    } else {
                        MaterialTheme.typography.titleLarge
                    },
                    color = if (premium == SeluraLibraryTheme.DEFAULT) {
                        MaterialTheme.colorScheme.onSurface
                    } else {
                        MaterialTheme.colorScheme.primary
                    },
                    maxLines = 1,""", key)
    files[key] = s

    key = "home"
    s = files[key]
    s = once(s,
        "import eu.kanade.presentation.util.Screen\n",
        "import eu.kanade.presentation.theme.LocalSeluraLibraryAppearance\n"
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n"
        "import eu.kanade.presentation.util.Screen\n", key)
    s = once(s,
        """                NavigationSuiteScaffold(
                    navigationSuiteType = navigationSuiteType,""",
        """                val appearance = LocalSeluraLibraryAppearance.current
                val isPremium = appearance?.theme != null &&
                    appearance.theme != SeluraLibraryTheme.DEFAULT
                val fadeDuration = if (appearance?.reducedEffects == true) 0 else TabFadeDuration
                NavigationSuiteScaffold(
                    navigationSuiteType = navigationSuiteType,""", key)
    s = once(s,
        """                    navigationSuiteColors = NavigationSuiteDefaults.colors(
                        navigationRailContainerColor = MaterialTheme.colorScheme
                            .surfaceColorAtElevation(3.dp),
                    ),""",
        """                    navigationSuiteColors = NavigationSuiteDefaults.colors(
                        navigationBarContainerColor = if (isPremium) {
                            MaterialTheme.colorScheme.surfaceContainer
                        } else {
                            MaterialTheme.colorScheme.surfaceColorAtElevation(3.dp)
                        },
                        navigationRailContainerColor = if (isPremium) {
                            MaterialTheme.colorScheme.surfaceContainer
                        } else {
                            MaterialTheme.colorScheme.surfaceColorAtElevation(3.dp)
                        },
                    ),""", key)
    if s.count("durationMillis = TabFadeDuration") != 2:
        raise PremiumThemePatchError("home: unexpected transition structure")
    s = s.replace("durationMillis = TabFadeDuration", "durationMillis = fadeDuration")
    files[key] = s

    # Atomic input validation: no writes until every upstream marker checked.
    for key, filename in FILES.items():
        (root / filename).write_text(files[key], encoding="utf-8")
    destination = root / THEME_DST
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(THEME_SRC, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)


if __name__ == "__main__":
    main()
