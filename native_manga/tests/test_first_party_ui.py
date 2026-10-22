"""Protect visible Selura branding without altering manga engines or licenses."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "clean_first_party_ui.py"
spec = importlib.util.spec_from_file_location("first_party_ui", SCRIPT)
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)

MORE = """package eu.kanade.presentation.more
import androidx.compose.ui.platform.LocalUriHandler
import mihon.icons.materialsymbols.automirroredrounded.Help
import mihon.icons.materialsymbols.roundedfilled.VolunteerActivism
import tachiyomi.core.common.Constants
object MoreScreen {
    val uriHandler = LocalUriHandler.current
    onClickSupport: () -> Unit,
    item { TextPreferenceWidget(title = stringResource(MR.strings.label_settings)) }
            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_support_us),
                    icon = MaterialSymbols.RoundedFilled.VolunteerActivism,
                    onPreferenceClick = onClickSupport,
                )
            }
            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.pref_category_about),
                    onPreferenceClick = onClickAbout,
                )
            }
            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_help),
                    icon = MaterialSymbols.AutoMirroredRounded.Help,
                    onPreferenceClick = { uriHandler.openUri(Constants.URL_HELP) },
                )
            }
}
"""
LOGO = """package eu.kanade.presentation.more
object LogoHeader {
    painter = painterResource(R.drawable.ic_mihon)
    modifier = Modifier.size(64.dp)
}
"""
MAIN = """class MainActivity {
    if (!isBenchmarkBuildType) {
        if (isLaunch) {
            SeluraStartupUpdateCheck()
            CheckForUpdates()
        }
        ShowOnboarding()
                    ShowDonationCampaign()
    }
}
"""

# The pinned About screen has a single upstream social row. Build this
# minimal fixture with the same exact audited import and code anchors.
# Dedicated native workflow checks apply this patch to the real full source.
def about_fixture():
    import_source = SCRIPT.read_text(encoding="utf-8")
    start = import_source.index("    unused_imports = (")
    stop = import_source.index("    for imp in unused_imports:", start)
    imports = re.findall(r'"(import [^"]+\\n)"', import_source[start:stop])
    imports = [bytes(x, "utf-8").decode("unicode_escape") for x in imports]
    prelude = "\n".join(s.strip() for s in imports)
    return (
        prelude + "\n" +
        """
import mihon.app.di.appGraph
object AboutScreen {
        val scope = rememberCoroutineScope()
        val context = LocalContext.current
        val navigator = LocalNavigator.currentOrThrow
        val uriHandler = LocalUriHandler.current
        val crashLogUtil = remember { context.appGraph.crashLogUtil }
        var isCheckingUpdates by remember { mutableStateOf(false) }
                if (updaterEnabled) {
                    item {
                        TextPreferenceWidget(
                            title = stringResource(MR.strings.check_for_updates),
                        )
                    }
                }

                if (!BuildConfig.DEBUG) {
                    item {
                        TextPreferenceWidget(
                            title = stringResource(MR.strings.whats_new),
                            onPreferenceClick = { uriHandler.openUri(RELEASE_URL) },
                        )
                    }
                }

                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.licenses),
                        onPreferenceClick = { navigator.push(OpenSourceLicensesScreen()) },
                    )
                }

                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.privacy_policy),
                        onPreferenceClick = { uriHandler.openUri("https://mihon.app/privacy/") },
                    )
                }

                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),
                        horizontalArrangement = Arrangement.Center,
                    ) {
                        LinkIcon(
                            label = "Discord",
                            icon = SimpleIcons.Discord,
                            url = Constants.URL_DISCORD,
                        )
                        LinkIcon(
                            label = "Facebook",
                            icon = SimpleIcons.Facebook,
                            url = "https://facebook.com/mihonapp",
                        )
                        LinkIcon(
                            label = "Reddit",
                            icon = SimpleIcons.Reddit,
                            url = "https://www.reddit.com/r/mihonapp",
                        )
                        LinkIcon(
                            label = "X",
                            icon = SimpleIcons.X,
                            url = "https://x.com/mihonapp",
                        )
                    }
                }
            }
        }
    }

    /**
     * Checks version and shows a user prompt if an update is available.
     */
    private suspend fun checkVersion(
        context: Context,
    ) {
        context.appGraph.updateChecker.checkForUpdate(forceCheck = true)
    }

    fun getVersionName(withBuildDate: Boolean): String {
        return if (withBuildDate) "Stable" else "Selura"
    }
}
"""
    )


class SeluraFirstPartyUiTests(unittest.TestCase):
    def test_logo_uses_app_drawable_not_upstream_icon(self):
        output = ui.patch_logo(LOGO)
        self.assertIn("R.drawable.selura_manga_icon", output)
        self.assertNotIn("R.drawable.ic_mihon", output)
        with self.assertRaises(ui.SeluraUiPatchError):
            ui.patch_logo(output)

    def test_more_removes_help_and_donation_without_breaking_navigation(self):
        output = ui.patch_more(MORE)
        self.assertNotIn("MR.strings.label_support_us", output)
        self.assertNotIn("Constants.URL_HELP", output)
        self.assertNotIn("LocalUriHandler", output)
        self.assertIn("MR.strings.label_settings", output)
        self.assertIn("MR.strings.pref_category_about", output)
        self.assertIn("onClickSupport: () -> Unit", output)
        with self.assertRaises(ui.SeluraUiPatchError):
            ui.patch_more(output)

    def test_about_preserves_licenses_version_and_selura_releases(self):
        output = ui.patch_about(about_fixture())
        self.assertIn("navigator.push(OpenSourceLicensesScreen())", output)
        self.assertIn("fun getVersionName(withBuildDate: Boolean)", output)
        self.assertIn("context.appGraph.crashLogUtil", output)
        self.assertIn("import mihon.app.di.appGraph", output)
        self.assertIn(ui.SELURA_RELEASES, output)
        self.assertNotIn("uriHandler.openUri(RELEASE_URL)", output)
        self.assertNotIn("context.appGraph.updateChecker", output)
        for unwanted in ("mihon.app/privacy", "facebook.com/mihonapp", "x.com/mihonapp",
                         "SimpleIcons.Discord", "SimpleIcons.Facebook", "SimpleIcons.Reddit",
                         "Constants.URL_DISCORD", "check_for_updates"):
            self.assertNotIn(unwanted, output)
        with self.assertRaises(ui.SeluraUiPatchError):
            ui.patch_about(output)

    def test_main_disables_unsolicited_donation_modal_not_selura_update(self):
        result = ui.patch_main(MAIN)
        self.assertNotIn("                    ShowDonationCampaign()", result)
        self.assertIn("SeluraStartupUpdateCheck()", result)
        self.assertIn("ShowOnboarding()", result)

    def test_preflight_rejects_unexpected_upstream_without_partial_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixtures = {ui.MORE: MORE, ui.ABOUT: about_fixture(), ui.LOGO: LOGO,
                        ui.MAIN: MAIN}
            for name, content in fixtures.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            manifest = root / "app/src/main/AndroidManifest.xml"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text('android:icon="@drawable/selura_manga_icon"')
            drawable = root / "app/src/main/res/drawable/selura_manga_icon.xml"
            drawable.parent.mkdir(parents=True, exist_ok=True)
            drawable.write_text("<vector/>")
            (root / "LICENSE").write_text("Apache License")
            # A missing legal license must never permit cosmetic source edits.
            (root / "LICENSE").unlink()
            with self.assertRaises(ui.SeluraUiPatchError):
                ui.patch(root)
            self.assertEqual((root / ui.MORE).read_text(), MORE)
            (root / "LICENSE").write_text("Apache License")
            # Break a downstream patch marker; earlier files remain untouched.
            (root / ui.MAIN).write_text("unexpected source")
            with self.assertRaises(ui.SeluraUiPatchError):
                ui.patch(root)
            self.assertEqual((root / ui.MORE).read_text(), MORE)
            (root / ui.MAIN).write_text(MAIN)
            ui.patch(root)
            self.assertIn("R.drawable.selura_manga_icon", (root / ui.LOGO).read_text())
            self.assertIn(ui.SELURA_RELEASES, (root / ui.ABOUT).read_text())
            with self.assertRaises(ui.SeluraUiPatchError):
                ui.patch(root)


if __name__ == "__main__":
    unittest.main()
