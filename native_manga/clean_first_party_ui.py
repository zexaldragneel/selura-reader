#!/usr/bin/env python3
"""Remove upstream community/promotional UI from the first-party Selura app.

This is a *presentation-only* patch over pinned Mihon Android sources after
Selura's native branding and other feature patches. Do not rename packages,
change migration/download code, remove required licenses or alter attribution.
"""
import argparse
from pathlib import Path

PREFIX = "app/src/main/java/"
MORE = PREFIX + "eu/kanade/presentation/more/MoreScreen.kt"
ABOUT = PREFIX + "eu/kanade/presentation/more/settings/screen/about/AboutScreen.kt"
LOGO = PREFIX + "eu/kanade/presentation/more/LogoHeader.kt"
MAIN = PREFIX + "eu/kanade/tachiyomi/ui/main/MainActivity.kt"
SELURA_RELEASES = "https://github.com/zexaldragneel/selura-reader/releases"


class SeluraUiPatchError(RuntimeError):
    pass


def change_one(source: str, before: str, after: str, context: str) -> str:
    amount = source.count(before)
    if amount != 1:
        raise SeluraUiPatchError(f"{context}: expected one audited marker, got {amount}")
    return source.replace(before, after, 1)


def strip_between_once(source: str, first: str, after: str, context: str) -> str:
    if source.count(first) != 1 or source.count(after) != 1:
        raise SeluraUiPatchError(f"{context}: upstream source anchor changed")
    start = source.index(first)
    end = source.index(after)
    if end <= start:
        raise SeluraUiPatchError(f"{context}: markers out of order")
    return source[:start] + source[end:]


def patch_logo(source: str) -> str:
    # This drawable is created by native_manga/apply_branding.py.
    return change_one(
        source,
        "painter = painterResource(R.drawable.ic_mihon)",
        "painter = painterResource(R.drawable.selura_manga_icon)",
        "first-party logo header",
    )


def patch_more(source: str) -> str:
    source = change_one(
        source,
        """            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_support_us),
                    icon = MaterialSymbols.RoundedFilled.VolunteerActivism,
                    onPreferenceClick = onClickSupport,
                )
            }
""", "", "remove upstream support menu",
    )
    source = change_one(
        source,
        """            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_help),
                    icon = MaterialSymbols.AutoMirroredRounded.Help,
                    onPreferenceClick = { uriHandler.openUri(Constants.URL_HELP) },
                )
            }
""", "", "remove upstream help link",
    )
    for declaration in (
        "import androidx.compose.ui.platform.LocalUriHandler\n",
        "import mihon.icons.materialsymbols.automirroredrounded.Help\n",
        "import mihon.icons.materialsymbols.roundedfilled.VolunteerActivism\n",
        "import tachiyomi.core.common.Constants\n",
        "    val uriHandler = LocalUriHandler.current\n",
    ):
        source = change_one(source, declaration, "", "remove unused community import/state")
    # Existing HomeScreen passes onClickSupport; retain its unused argument to
    # preserve navigation/API stability. The support item itself is gone.
    return source


def patch_about(source: str) -> str:
    # The original manual updater checks upstream Mihon releases. Selura's
    # separate verified GitHub metadata startup updater is left unchanged.
    source = strip_between_once(
        source, "                if (updaterEnabled) {\n",
        "                if (!BuildConfig.DEBUG) {\n",
        "remove upstream updater menu",
    )
    source = change_one(
        source,
        "onPreferenceClick = { uriHandler.openUri(RELEASE_URL) },",
        f'onPreferenceClick = {{ uriHandler.openUri("{SELURA_RELEASES}") }},',
        "route What's New to Selura releases",
    )
    source = change_one(
        source,
        """                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.privacy_policy),
                        onPreferenceClick = { uriHandler.openUri("https://mihon.app/privacy/") },
                    )
                }

""",
        "",
        "remove unrelated upstream privacy policy",
    )
    source = strip_between_once(
        source,
        "                item {\n                    Row(\n",
        "            }\n        }\n    }\n\n    /**\n     * Checks version",
        "remove upstream website/social icon row",
    )
    # Strip unused upstream release-check function (no Selura endpoint).
    source = strip_between_once(
        source,
        "    /**\n     * Checks version and shows a user prompt if an update is available.\n",
        "    fun getVersionName(withBuildDate: Boolean): String {",
        "remove upstream check-for-update implementation",
    )
    unused_imports = (
        "import androidx.compose.animation.AnimatedVisibility\n",
        "import androidx.compose.foundation.layout.Arrangement\n",
        "import androidx.compose.foundation.layout.Row\n",
        "import androidx.compose.foundation.layout.fillMaxWidth\n",
        "import androidx.compose.foundation.layout.padding\n",
        "import androidx.compose.material3.CircularProgressIndicator\n",
        "import androidx.compose.runtime.mutableStateOf\n",
        "import androidx.compose.runtime.rememberCoroutineScope\n",
        "import androidx.compose.runtime.setValue\n",
        "import androidx.compose.ui.Modifier\n",
        "import androidx.compose.ui.unit.dp\n",
        "import eu.kanade.tachiyomi.data.updater.RELEASE_URL\n",
        "import eu.kanade.tachiyomi.ui.more.NewUpdateScreen\n",
        "import eu.kanade.tachiyomi.util.system.toast\n",
        "import eu.kanade.tachiyomi.util.system.updaterEnabled\n",
        "import kotlinx.coroutines.Dispatchers\n",
        "import kotlinx.coroutines.launch\n",
        "import kotlinx.coroutines.withContext\n",
        "import logcat.LogPriority\n",
        "import mihon.app.di.appGraph\n",
        "import mihon.icons.materialsymbols.MaterialSymbols\n",
        "import mihon.icons.materialsymbols.rounded.Public\n",
        "import mihon.icons.simpleicons.Discord\n",
        "import mihon.icons.simpleicons.Facebook\n",
        "import mihon.icons.simpleicons.Github\n",
        "import mihon.icons.simpleicons.Reddit\n",
        "import mihon.icons.simpleicons.SimpleIcons\n",
        "import mihon.icons.simpleicons.X\n",
        "import tachiyomi.core.common.Constants\n",
        "import tachiyomi.core.common.util.system.logcat\n",
        "import tachiyomi.domain.release.interactor.GetApplicationRelease\n",
        "import tachiyomi.presentation.core.components.LinkIcon\n",
    )
    for imp in unused_imports:
        source = change_one(source, imp, "", "remove unused upstream social/updater imports")
    source = change_one(
        source, "        val scope = rememberCoroutineScope()\n", "",
        "remove old updater coroutine",
    )
    source = change_one(
        source, "        var isCheckingUpdates by remember { mutableStateOf(false) }\n", "",
        "remove upstream update state",
    )
    # AppGraph's crash log helper remains behind About's Version copy utility.
    for forbidden in ("mihon.app/privacy/", "x.com/mihonapp", "facebook.com/mihonapp",
                      "mihonapp", "SimpleIcons.Discord", "Constants.URL_DISCORD",
                      "Constants.URL_HELP", "RELEASE_URL"):
        if forbidden in source:
            raise SeluraUiPatchError(f"Upstream About link still present: {forbidden}")
    if "navigator.push(OpenSourceLicensesScreen())" not in source:
        raise SeluraUiPatchError("Open-source licenses must remain reachable")
    if "fun getVersionName(withBuildDate: Boolean)" not in source:
        raise SeluraUiPatchError("About version helper needed by Settings")
    return source


def patch_main(source: str) -> str:
    # The application already uses its separate Selura verified startup
    # updater. Remove only the unsolicited legacy donation campaign popup.
    return change_one(
        source,
        "                    ShowDonationCampaign()\n",
        "",
        "disable legacy donation popup",
    )


def patch(root: Path) -> None:
    root = root.resolve()
    original = {
        MORE: patch_more, ABOUT: patch_about, LOGO: patch_logo, MAIN: patch_main,
    }
    pending = {}
    for name, transformer in original.items():
        path = root / name
        if not path.is_file():
            raise SeluraUiPatchError(f"Missing pinned native source {name}")
        old = path.read_text(encoding="utf-8")
        new = transformer(old)
        if new == old:
            raise SeluraUiPatchError(f"Nothing changed: {name}")
        pending[path] = new
    manifest = root / "app/src/main/AndroidManifest.xml"
    if not manifest.is_file() or "@drawable/selura_manga_icon" not in manifest.read_text(encoding="utf-8"):
        raise SeluraUiPatchError("Selura launcher icon not in manifest")
    if not (root / "app/src/main/res/drawable/selura_manga_icon.xml").exists():
        raise SeluraUiPatchError("Selura drawable not found")
    if not (root / "LICENSE").is_file():
        raise SeluraUiPatchError("Upstream Apache-2.0 license must remain")
    # All source/attribution guards pass before mutating any files.
    for path, new in pending.items():
        path.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("upstream", type=Path)
    patch(cli.parse_args().upstream)
