"""Native Selura-only UI contracts without touching engine or licenses."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

script=Path(__file__).resolve().parents[1]/"clean_independent_ui.py"
spec=importlib.util.spec_from_file_location("selura_clean_ui",script)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ABOUT="""object AboutScreen : Screen() {
  link https://mihon.app/privacy/
  link https://facebook.com/mihonapp
  url = Constants.URL_DISCORD
  onPreferenceClick = { uriHandler.openUri(RELEASE_URL) }
    fun getVersionName(withBuildDate: Boolean): String { return "Stable" }
    internal fun getFormattedBuildTime(): String { return "now" }
}
"""
MORE="""import androidx.compose.ui.platform.LocalUriHandler
import mihon.icons.materialsymbols.automirroredrounded.Help
import mihon.icons.materialsymbols.roundedfilled.VolunteerActivism
import tachiyomi.core.common.Constants
fun MoreScreen(
    onClickSupport: () -> Unit,
) {
    val uriHandler = LocalUriHandler.current

            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_support_us),
                    icon = MaterialSymbols.RoundedFilled.VolunteerActivism,
                    onPreferenceClick = onClickSupport,
                )
            }
            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_help),
                    icon = MaterialSymbols.AutoMirroredRounded.Help,
                    onPreferenceClick = { uriHandler.openUri(Constants.URL_HELP) },
                )
            }
  val downloadsPreserved = true
}
"""
TAB="""import mihon.feature.support.SupportUsScreen
            onClickSupport = { navigator.push(SupportUsScreen()) },
            onClickSettings = { navigator.push(SettingsScreen()) },
"""
LOGO="""Icon(painter = painterResource(R.drawable.ic_mihon), contentDescription = null)"""
MAIN="""        // Native app uses startup updates
                    ShowOnboarding()
                    ShowDonationCampaign()
    private fun CheckForUpdates() {
        // App updates
        LaunchedEffect(Unit) {
            val result = context.appGraph.updateChecker.checkForUpdate()
        }

        // Extensions updates
        LaunchedEffect(Unit) { extensionManager.checkForUpdates() }
    }
"""
FIXTURES={mod.ABOUT:ABOUT,mod.MORE:MORE,mod.TAB:TAB,mod.LOGO:LOGO,mod.MAIN:MAIN}


class SeluraCleanUiTests(unittest.TestCase):
    def test_about_only_selura_links_with_required_licenses(self):
        s=mod.patch_about(ABOUT)
        self.assertIn("https://github.com/zexaldragneel/selura-reader/releases",s)
        self.assertIn("Developed by Zexal Dragneel",s)
        self.assertIn("navigator.push(OpenSourceLicensesScreen())",s)
        self.assertIn("fun getVersionName(withBuildDate: Boolean)",s)
        self.assertIn("fun getFormattedBuildTime()",s)
        for old in ("mihon.app","facebook.com","Constants.URL_DISCORD","Reddit","SimpleIcons","NewUpdateScreen","RELEASE_URL","checkVersion(", "privacy_policy"):
            self.assertNotIn(old,s)

    def test_more_screen_preserves_core_features_without_help_or_donation(self):
        s=mod.patch_more(MORE)
        self.assertIn("downloadsPreserved",s)
        for old in ("onClickSupport","label_support_us","label_help","Constants.URL_HELP","VolunteerActivism","LocalUriHandler"):
            self.assertNotIn(old,s)

    def test_old_support_navigation_is_not_reachable(self):
        s=mod.patch_tab(TAB)
        self.assertNotIn("SupportUsScreen",s)
        self.assertNotIn("onClickSupport",s)
        self.assertIn("onClickSettings",s)

    def test_logo_uses_original_selura_vector(self):
        s=mod.patch_logo(LOGO)
        self.assertIn("R.drawable.selura_manga_icon",s)
        self.assertNotIn("R.drawable.ic_mihon",s)

    def test_keep_extension_update_checks_and_selura_update_prompt(self):
        s=mod.patch_main(MAIN)
        self.assertIn("extensionManager.checkForUpdates()",s)
        self.assertIn("ShowOnboarding()",s)
        self.assertNotIn("updateChecker.checkForUpdate()",s)
        self.assertNotIn("                    ShowDonationCampaign()",s)
        self.assertIn("SeluraStartupUpdateCheck",s)

    def test_incompatible_source_fails_before_any_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for path,data in FIXTURES.items():
                p=root/path
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(data)
            (root/mod.TAB).write_text("unexpected upstream tab")
            with self.assertRaises(mod.SeluraUiPatchError):
                mod.patch(root)
            self.assertEqual((root/mod.ABOUT).read_text(),ABOUT)
            self.assertEqual((root/mod.MORE).read_text(),MORE)

    def test_all_five_sources_receive_actual_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for path,data in FIXTURES.items():
                p=root/path
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(data)
            mod.patch(root)
            for path,old in FIXTURES.items():
                self.assertNotEqual((root/path).read_text(),old)
            with self.assertRaises(mod.SeluraUiPatchError):
                mod.patch(root)

if __name__=="__main__":
    unittest.main()
