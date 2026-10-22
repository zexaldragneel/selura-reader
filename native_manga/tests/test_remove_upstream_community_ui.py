"""Regression protection for Selura-only public UI while preserving upstream licenses."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "remove_upstream_community_ui.py"
spec = importlib.util.spec_from_file_location("selura_white_label", SCRIPT)
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)

MORE = """fun MoreScreen() {
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
                    icon = MaterialSymbols.Rounded.Info,
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
}"""

ABOUT = """object AboutScreen {
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
                    ) {
                        LinkIcon(label = "Discord", url = Constants.URL_DISCORD)
                        LinkIcon(label = "Facebook", url = "https://facebook.com/mihonapp")
                    }
                }
            }
        }
    }

    /**
     * Checks version
    private fun checkVersion() {}
}"""

LOGO = """fun LogoHeader() {
        Icon(
            painter = painterResource(R.drawable.ic_mihon),
        )
}"""

MAIN = """fun MainActivity() {
                if (!isBenchmarkBuildType) {
                    if (isLaunch) {
                        CheckForUpdates()
                        SeluraStartupUpdateCheck()
                    }
                    ShowOnboarding()
                    ShowDonationCampaign()
                }
}"""

CRASH = """fun CrashScreen() {
        subtitleText = stringResource(MR.strings.crash_screen_description, stringResource(MR.strings.app_name)),
}"""

FILES = {
    patcher.MORE: MORE,
    patcher.ABOUT: ABOUT,
    patcher.LOGO: LOGO,
    patcher.MAIN: MAIN,
    patcher.CRASH: CRASH,
}


class WhiteLabelTests(unittest.TestCase):
    def test_more_keeps_utilities_and_about_but_hides_upstream_social(self):
        value = patcher.more_screen(MORE)
        self.assertIn("onClickAbout", value)
        self.assertNotIn("onClickSupport,", value)
        self.assertNotIn("Constants.URL_HELP)", value)
        self.assertNotIn("label_support_us", value)

    def test_about_keeps_license_and_self_update_releases(self):
        value = patcher.about_screen(ABOUT)
        self.assertIn("OpenSourceLicensesScreen()", value)
        self.assertIn("Developed by Zexal Dragneel", value)
        self.assertIn("Selura Manga", value)
        self.assertIn(patcher.RELEASES, value)
        for old in ("url = Constants.URL_DISCORD", "facebook.com/mihonapp",
                    "mihon.app/privacy/", "title = stringResource(MR.strings.check_for_updates),"):
            self.assertNotIn(old, value)
        self.assertEqual(value.count("OpenSourceLicensesScreen()"), 1)

    def test_logo_is_selura_asset_not_upstream_trademark(self):
        value = patcher.logo_header(LOGO)
        self.assertIn("painterResource(R.drawable.selura_manga_icon)", value)
        self.assertNotIn("R.drawable.ic_mihon", value)

    def test_first_party_update_only_no_mihon_donation_campaign(self):
        value = patcher.main_activity(MAIN)
        self.assertIn("SeluraStartupUpdateCheck()", value)
        self.assertIn("ShowOnboarding()", value)
        self.assertNotIn("CheckForUpdates()", value)
        self.assertNotIn("ShowDonationCampaign()", value)

    def test_crash_instructions_no_upstream_discord(self):
        value = patcher.crash_screen(CRASH)
        self.assertIn("You can export a crash log", value)
        self.assertNotIn("crash_screen_description", value)
        self.assertIn("stringResource(MR.strings.app_name)", value)

    def test_preflight_blocks_any_partial_write_if_source_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "LICENSE").write_text("Apache-2.0 original attribution\n")
            for file, source in FILES.items():
                file_path = root / file
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(source)
            wrong = root / patcher.ABOUT
            wrong.write_text("changed upstream About screen")
            with self.assertRaises(patcher.WhiteLabelPatchError):
                patcher.patch(root)
            self.assertEqual((root / patcher.MORE).read_text(), MORE)
            self.assertEqual((root / "LICENSE").read_text(), "Apache-2.0 original attribution\n")
            wrong.write_text(ABOUT)
            patcher.patch(root)
            self.assertNotIn("Facebook", (root / patcher.ABOUT).read_text())
            self.assertIn("OpenSourceLicensesScreen()", (root / patcher.ABOUT).read_text())
            with self.assertRaises(patcher.WhiteLabelPatchError):
                patcher.patch(root)

    def test_scope_excludes_storage_migrations_source_ids_and_signing(self):
        self.assertEqual(len(patcher.TRANSFORMS), 5)
        self.assertEqual(set(FILES), set(patcher.TRANSFORMS))
        self.assertNotIn("extension", "\n".join(patcher.TRANSFORMS))
        self.assertNotIn("backup", "\n".join(patcher.TRANSFORMS))
        self.assertNotIn("build.gradle", "\n".join(patcher.TRANSFORMS))


if __name__ == "__main__":
    unittest.main()
