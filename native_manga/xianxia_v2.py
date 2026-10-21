#!/usr/bin/env python3
"""Celestial Xianxia v2: richer theme chrome, presentation only.

Run after refine_premium_themes.py against the pinned, already-patched native
Mihon tree. Every replacement is fail-closed (exactly one match required).
Touches only Compose presentation files. Never touches cover loading, covers,
titles, library data, readers, extensions, downloads or progress state.
"""
from pathlib import Path
import argparse
import shutil

ORNAMENTS = Path(__file__).resolve().parent / "premium_theme" / "SeluraXianxiaOrnaments.kt"
DEST = "app/src/main/java/eu/kanade/presentation/theme/SeluraXianxiaOrnaments.kt"
FILES = {
    "toolbar": "app/src/main/java/eu/kanade/presentation/library/components/LibraryToolbar.kt",
    "tabs": "app/src/main/java/eu/kanade/presentation/library/components/LibraryTabs.kt",
    "cards": "app/src/main/java/eu/kanade/presentation/library/components/CommonMangaItem.kt",
    "library": "app/src/main/java/eu/kanade/presentation/library/components/LibraryContent.kt",
    "home": "app/src/main/java/eu/kanade/tachiyomi/ui/home/HomeScreen.kt",
}
CELESTIAL = "SeluraLibraryTheme.CELESTIAL_XIANXIA"


class XianxiaError(RuntimeError):
    pass


def once(source: str, old: str, new: str, path: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise XianxiaError(
            f"{path}: expected one source marker, got {occurrences}: {old[:85]!r}"
        )
    return source.replace(old, new, 1)


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise XianxiaError("Pinned native Mihon checkout and LICENSE required")
    if not ORNAMENTS.is_file() or (root / DEST).exists():
        raise XianxiaError("Missing ornament source or v2 already installed")
    if not (root / "app/src/main/java/eu/kanade/presentation/theme/SeluraSkylineHeader.kt").is_file():
        raise XianxiaError("refine_premium_themes.py must run before xianxia_v2.py")
    changed = {}
    for key, path in FILES.items():
        target = root / path
        if not target.is_file():
            raise XianxiaError(f"Missing original native Kotlin file: {path}")
        changed[key] = target.read_text(encoding="utf-8")

    # Toolbar: ink backdrop with sun/moon/clouds, brush wordmark, seal, count pill.
    k = "toolbar"
    s = changed[k]
    s = once(s,
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n",
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n"
        "import eu.kanade.presentation.theme.XianxiaLibraryTitle\n"
        "import eu.kanade.presentation.theme.xianxiaToolbarBackdrop\n", k)
    s = once(s,
        "        modifier = if (premium != SeluraLibraryTheme.DEFAULT) {\n            Modifier.background(",
        f"        modifier = if (premium == {CELESTIAL}) {{\n"
        "            Modifier.xianxiaToolbarBackdrop(\n"
        "                LocalSeluraLibraryAppearance.current?.backgroundArtwork != false,\n"
        "            )\n"
        "        } else if (premium != SeluraLibraryTheme.DEFAULT) {\n            Modifier.background(", k)
    s = once(s,
        "        titleContent = {\n            Row(verticalAlignment = Alignment.CenterVertically) {\n                Text(\n                    text = title.text,",
        "        titleContent = {\n"
        f"            if (premium == {CELESTIAL}) {{\n"
        "                XianxiaLibraryTitle(title = title.text, count = title.numberOfManga)\n"
        "                return@SearchToolbar\n"
        "            }\n"
        "            Row(verticalAlignment = Alignment.CenterVertically) {\n                Text(\n                    text = title.text,", k)
    changed[k] = s

    # Category tabs: dark inlay, gold frame, corner brackets, pagoda glyph.
    k = "tabs"
    s = changed[k]
    s = once(s,
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n",
        "import eu.kanade.presentation.theme.SeluraLibraryTheme\n"
        "import eu.kanade.presentation.theme.XianxiaPagodaGlyph\n"
        "import eu.kanade.presentation.theme.xianxiaTabFrame\n", k)
    s = once(s,
        "                modifier = if (custom) {\n",
        f"                modifier = if (premium == {CELESTIAL}) {{\n"
        "                    Modifier\n"
        "                        .padding(horizontal = 2.dp, vertical = 2.dp)\n"
        "                        .clip(RoundedCornerShape(8.dp))\n"
        "                        .xianxiaTabFrame(isActive)\n"
        "                } else if (custom) {\n", k)
    s = once(s,
        """                text = {
                    TabText(
                        text = category.visualName,
                        badgeCount = getItemCountForCategory(category),
                    )
                },""",
        f"""                text = {{
                    if (premium == {CELESTIAL}) {{
                        androidx.compose.foundation.layout.Row(
                            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                            horizontalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(4.dp),
                        ) {{
                            if (isActive) {{
                                XianxiaPagodaGlyph(tint = Color(0xFFF6D79D))
                            }}
                            androidx.compose.material3.ProvideTextStyle(
                                MaterialTheme.typography.labelMedium.copy(
                                    fontFamily = androidx.compose.ui.text.font.FontFamily.Serif,
                                    fontSize = 12.sp,
                                ),
                            ) {{
                                TabText(
                                    text = category.visualName,
                                    badgeCount = getItemCountForCategory(category),
                                )
                            }}
                        }}
                    }} else {{
                        TabText(
                            text = category.visualName,
                            badgeCount = getItemCountForCategory(category),
                        )
                    }}
                }},""", k)
    changed[k] = s

    # Cards: ornate frame on the container edge; serif title with a deeper scrim.
    # The cover composable, its model and its alpha are not touched.
    k = "cards"
    s = changed[k]
    s = once(s,
        "import androidx.compose.ui.graphics.Brush\n",
        "import androidx.compose.ui.graphics.Brush\n"
        "import eu.kanade.presentation.theme.xianxiaCardFrame\n", k)
    s = once(s,
        "            .selectedOutline(isSelected = isSelected, color = MaterialTheme.colorScheme.secondary)\n"
        "            .padding(if (isPremium) 3.dp else 4.dp),",
        "            .selectedOutline(isSelected = isSelected, color = MaterialTheme.colorScheme.secondary)\n"
        f"            .then(if (premium == {CELESTIAL}) Modifier.xianxiaCardFrame() else Modifier)\n"
        "            .padding(if (isPremium) 3.dp else 4.dp),", k)
    s = once(s,
        "    onClickContinueReading: (() -> Unit)? = null,\n) {\n    Box(\n"
        "        modifier = Modifier\n            .clip(RoundedCornerShape(bottomStart = 4.dp, bottomEnd = 4.dp))",
        "    onClickContinueReading: (() -> Unit)? = null,\n) {\n"
        f"    val celestial = LocalSeluraLibraryAppearance.current?.theme == {CELESTIAL}\n"
        "    Box(\n"
        "        modifier = Modifier\n            .clip(RoundedCornerShape(bottomStart = 4.dp, bottomEnd = 4.dp))", k)
    s = once(s, "                    1f to Color(0xAA000000),",
        "                    1f to Color(if (celestial) 0xE6050810 else 0xAA000000),", k)
    s = once(s, "            .fillMaxHeight(0.33f)",
        "            .fillMaxHeight(if (celestial) 0.45f else 0.33f)", k)
    s = once(s,
        """            minLines = 1,
        )
        if (onClickContinueReading != null) {""",
        """            minLines = 1,
            maxLines = if (celestial) 3 else 2,
        )
        if (onClickContinueReading != null) {""", k)
    s = once(s,
        "            style = MaterialTheme.typography.titleSmall.copy(\n                color = Color.White,",
        "            style = MaterialTheme.typography.titleSmall.copy(\n"
        "                color = if (celestial) Color(0xFFF3E6C8) else Color.White,\n"
        "                fontFamily = if (celestial) {\n"
        "                    androidx.compose.ui.text.font.FontFamily.Serif\n"
        "                } else {\n"
        "                    MaterialTheme.typography.titleSmall.fontFamily\n"
        "                },", k)
    changed[k] = s

    # Library: richer scenery strip for Celestial only; Neon keeps its header.
    k = "library"
    s = changed[k]
    s = once(s,
        "import eu.kanade.presentation.theme.SeluraSkylineHeader\n",
        "import eu.kanade.presentation.theme.SeluraSkylineHeader\n"
        "import eu.kanade.presentation.theme.XianxiaScenery\n", k)
    s = once(s,
        "        if (premium != SeluraLibraryTheme.DEFAULT) {\n            SeluraSkylineHeader()\n        }",
        f"        if (premium == {CELESTIAL}) {{\n"
        "            XianxiaScenery()\n"
        "        } else if (premium != SeluraLibraryTheme.DEFAULT) {\n"
        "            SeluraSkylineHeader()\n"
        "        }", k)
    changed[k] = s

    # Navigation: compact ink/chrome typography; callbacks, badges and touch targets untouched.
    k = "home"
    s = changed[k]
    s = once(s,
        "import androidx.compose.foundation.layout.Arrangement\n",
        "import androidx.compose.foundation.layout.Arrangement\n"
        "import androidx.compose.foundation.layout.size\n", k)
    s = once(s,
        "import androidx.compose.ui.unit.dp\n",
        "import androidx.compose.ui.unit.dp\n"
        "import androidx.compose.ui.unit.sp\n", k)
    s = once(s,
        """                    painter = tab.options.icon!!,
                    contentDescription = tab.options.title,""",
        """                    painter = tab.options.icon!!,
                    contentDescription = tab.options.title,
                    modifier = if (premium == SeluraLibraryTheme.CELESTIAL_XIANXIA) {
                        Modifier.size(21.dp)
                    } else {
                        Modifier
                    },""", k)
    s = once(s,
        """MaterialTheme.typography.labelLarge.copy(
                            fontFamily = androidx.compose.ui.text.font.FontFamily.Serif,
                        )""",
        """MaterialTheme.typography.labelSmall.copy(
                            fontFamily = androidx.compose.ui.text.font.FontFamily.Serif,
                            fontSize = 11.sp,
                        )""", k)
    s = once(s,
        "                        navigationBarContainerColor = if (isPremium) {\n"
        "                            MaterialTheme.colorScheme.surfaceContainer",
        "                        navigationBarContainerColor = if (isPremium) {\n"
        f"                            if (appearance?.theme == {CELESTIAL}) {{\n"
        "                                androidx.compose.ui.graphics.Color(0xFF0C0908)\n"
        "                            } else {\n"
        "                                MaterialTheme.colorScheme.surfaceContainer\n"
        "                            }", k)
    changed[k] = s

    for key, result in changed.items():
        if result == (root / FILES[key]).read_text(encoding="utf-8"):
            raise XianxiaError(f"No change in expected UI file {key}")
    for key, result in changed.items():
        (root / FILES[key]).write_text(result, encoding="utf-8")
    target = root / DEST
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ORNAMENTS, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
