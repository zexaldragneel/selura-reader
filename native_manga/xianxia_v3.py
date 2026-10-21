#!/usr/bin/env python3
"""Celestial Xianxia v3: illustrated artwork, presentation only.

Run after xianxia_v2.py. Bundles three original image assets as Android
drawable resources and switches the Celestial theme call sites from the v2
vector drawing to the illustrated versions. Every replacement is fail-closed.
Never touches covers, titles, library data, readers, extensions, downloads,
migration, progress, the application ID or signing.
"""
from pathlib import Path
import argparse
import shutil

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "premium_theme" / "assets"
ART_KT = HERE / "premium_theme" / "SeluraXianxiaArt.kt"
ART_DEST = "app/src/main/java/eu/kanade/presentation/theme/SeluraXianxiaArt.kt"
RES_DEST = "app/src/main/res/drawable-nodpi"
ASSET_FILES = ("xianxia_header.webp", "xianxia_card_corners.png", "xianxia_nav_frame.png")
V2_MARKER = "app/src/main/java/eu/kanade/presentation/theme/SeluraXianxiaOrnaments.kt"
FILES = {
    "toolbar": "app/src/main/java/eu/kanade/presentation/library/components/LibraryToolbar.kt",
    "cards": "app/src/main/java/eu/kanade/presentation/library/components/CommonMangaItem.kt",
    "library": "app/src/main/java/eu/kanade/presentation/library/components/LibraryContent.kt",
    "home": "app/src/main/java/eu/kanade/tachiyomi/ui/home/HomeScreen.kt",
}
CELESTIAL = "SeluraLibraryTheme.CELESTIAL_XIANXIA"


class XianxiaV3Error(RuntimeError):
    pass


def once(source: str, old: str, new: str, path: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise XianxiaV3Error(
            f"{path}: expected one source marker, got {occurrences}: {old[:85]!r}"
        )
    return source.replace(old, new, 1)


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise XianxiaV3Error("Pinned native Mihon checkout and LICENSE required")
    if not (root / V2_MARKER).is_file():
        raise XianxiaV3Error("xianxia_v2.py must run before xianxia_v3.py")
    if (root / ART_DEST).exists():
        raise XianxiaV3Error("v3 already installed")
    if not ART_KT.is_file():
        raise XianxiaV3Error("Missing SeluraXianxiaArt.kt")
    for name in ASSET_FILES:
        if not (ASSETS / name).is_file():
            raise XianxiaV3Error(f"Missing art asset: {name}")
        if (root / RES_DEST / name).exists():
            raise XianxiaV3Error(f"Resource already exists: {name}")
    changed = {}
    for key, path in FILES.items():
        target = root / path
        if not target.is_file():
            raise XianxiaV3Error(f"Missing native Kotlin file: {path}")
        changed[key] = target.read_text(encoding="utf-8")

    k = "toolbar"
    s = changed[k]
    s = once(s, "import eu.kanade.presentation.theme.xianxiaToolbarBackdrop\n",
             "import eu.kanade.presentation.theme.xianxiaToolbarArt\n", k)
    s = once(s, "Modifier.xianxiaToolbarBackdrop(", "Modifier.xianxiaToolbarArt(", k)
    changed[k] = s

    k = "cards"
    s = changed[k]
    s = once(s, "import eu.kanade.presentation.theme.xianxiaCardFrame\n",
             "import eu.kanade.presentation.theme.xianxiaCardArtFrame\n", k)
    s = once(s, "Modifier.xianxiaCardFrame() else Modifier)",
             "Modifier.xianxiaCardArtFrame() else Modifier)", k)
    changed[k] = s

    k = "library"
    s = changed[k]
    s = once(s, "import eu.kanade.presentation.theme.XianxiaScenery\n",
             "import eu.kanade.presentation.theme.XianxiaArtStrip\n", k)
    s = once(s, "            XianxiaScenery()\n", "            XianxiaArtStrip()\n", k)
    changed[k] = s

    k = "home"
    s = changed[k]
    s = once(s, "import androidx.compose.foundation.layout.Arrangement\n",
             "import androidx.compose.foundation.layout.Arrangement\n"
             "import androidx.compose.foundation.layout.Box\n"
             "import androidx.compose.foundation.layout.fillMaxSize\n"
             "import eu.kanade.presentation.theme.XianxiaNavFrame\n", k)
    s = once(s, "                NavigationSuiteScaffold(\n                    navigationSuiteType = navigationSuiteType,",
             "                Box(modifier = Modifier.fillMaxSize()) {\n"
             "                NavigationSuiteScaffold(\n                    navigationSuiteType = navigationSuiteType,", k)
    s = once(s, "                }\n            }\n\n            val goToLibraryTab = ",
             "                }\n"
             f"                if (appearance?.theme == {CELESTIAL} &&\n"
             "                    navigationSuiteType == NavigationSuiteType.NavigationBar &&\n"
             "                    navigationSuiteState.currentValue ==\n"
             "                    androidx.compose.material3.adaptive.navigationsuite.NavigationSuiteScaffoldValue.Visible\n"
             "                ) {\n"
             "                    XianxiaNavFrame(Modifier.align(androidx.compose.ui.Alignment.BottomCenter))\n"
             "                }\n"
             "                }\n"
             "            }\n\n            val goToLibraryTab = ", k)
    changed[k] = s

    for key, result in changed.items():
        if result == (root / FILES[key]).read_text(encoding="utf-8"):
            raise XianxiaV3Error(f"No change in expected UI file {key}")
    for key, result in changed.items():
        (root / FILES[key]).write_text(result, encoding="utf-8")
    art = root / ART_DEST
    art.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ART_KT, art)
    res = root / RES_DEST
    res.mkdir(parents=True, exist_ok=True)
    for name in ASSET_FILES:
        shutil.copyfile(ASSETS / name, res / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
