#!/usr/bin/env python3
"""White-label Selura's user-facing navigation while preserving upstream licenses.

Apply to the pinned Mihon checkout after all other Selura native patches.
Never change source IDs, backup/extension APIs, app ID, update signing,
stored data, or upstream Apache-2.0 licensing/attribution files.
"""
import argparse
from pathlib import Path

BASE = "app/src/main/java/"
MORE = BASE + "eu/kanade/presentation/more/MoreScreen.kt"
ABOUT = BASE + "eu/kanade/presentation/more/settings/screen/about/AboutScreen.kt"
LOGO = BASE + "eu/kanade/presentation/more/LogoHeader.kt"
MAIN = BASE + "eu/kanade/tachiyomi/ui/main/MainActivity.kt"
CRASH = BASE + "eu/kanade/presentation/crash/CrashScreen.kt"
RELEASES = "https://github.com/zexaldragneel/selura-reader/releases"


class WhiteLabelPatchError(RuntimeError):
    pass


def replace_exact(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise WhiteLabelPatchError(f"{label}: expected 1 audited anchor, found {count}")
    return source.replace(old, new, 1)


def more_screen(source):
    source = replace_exact(
        source,
        """            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_support_us),
                    icon = MaterialSymbols.RoundedFilled.VolunteerActivism,
                    onPreferenceClick = onClickSupport,
                )
            }
""",
        "",
        "remove upstream donation/support menu",
    )
    source = replace_exact(
        source,
        """            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.label_help),
                    icon = MaterialSymbols.AutoMirroredRounded.Help,
                    onPreferenceClick = { uriHandler.openUri(Constants.URL_HELP) },
                )
            }
""",
        "",
        "remove upstream Mihon Help website",
    )
    return source


def about_screen(source):
    start = """                if (updaterEnabled) {
                    item {
                        TextPreferenceWidget(
                            title = stringResource(MR.strings.check_for_updates),"""
    end = """                if (!BuildConfig.DEBUG) {
                    item {
                        TextPreferenceWidget(
                            title = stringResource(MR.strings.whats_new),"""
    if source.count(start) != 1 or source.count(end) != 1:
        raise WhiteLabelPatchError("audited upstream manual updater block not found uniquely")
    a = source.index(start)
    b = source.index(end)
    if a >= b or b - a > 3100:
        raise WhiteLabelPatchError("About update section moved unexpectedly")
    # Selura's first-party startup updater (with verified feed & in-app
    # installer) remains untouched. Remove misleading old manual Mihon check.
    source = source[:a] + source[b:]
    source = replace_exact(
        source,
        "onPreferenceClick = { uriHandler.openUri(RELEASE_URL) },",
        f'onPreferenceClick = {{ uriHandler.openUri("{RELEASES}") }},',
        "first-party Selura release notes",
    )
    source = replace_exact(
        source,
        """                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.privacy_policy),
                        onPreferenceClick = { uriHandler.openUri("https://mihon.app/privacy/") },
                    )
                }

""",
        "",
        "remove incorrect upstream privacy policy",
    )
    social_start = """                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 8.dp),"""
    social_end = """                }
            }
        }
    }

    /**
     * Checks version"""
    if source.count(social_start) != 1 or source.count(social_end) != 1:
        raise WhiteLabelPatchError("audited About social footer changed unexpectedly")
    a, b = source.index(social_start), source.index(social_end)
    if a >= b or b-a > 2100:
        raise WhiteLabelPatchError("unexpected About social footer size")
    # Keep enclosing LazyColumn braces; replace only the final social item.
    source = source[:a] + source[b:].replace("                }\n", "", 1)
    source = replace_exact(
        source,
        """                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.version),""",
        """                item {
                    TextPreferenceWidget(
                        title = "Selura Manga",
                        subtitle = "Developed by Zexal Dragneel",
                    )
                }
                item {
                    TextPreferenceWidget(
                        title = stringResource(MR.strings.version),""",
        "original developer info",
    )
    return source


def logo_header(source):
    return replace_exact(
        source, "painterResource(R.drawable.ic_mihon)",
        "painterResource(R.drawable.selura_manga_icon)",
        "Selura logo on More and About",
    )


def main_activity(source):
    return replace_exact(
        source,
        """                    if (isLaunch) {
                        CheckForUpdates()
                        SeluraStartupUpdateCheck()
                    }
                    ShowOnboarding()
                    ShowDonationCampaign()""",
        """                    if (isLaunch) {
                        SeluraStartupUpdateCheck()
                    }
                    ShowOnboarding()""",
        "disable old Mihon update/donation prompts, keep native Selura updater",
    )


def crash_screen(source):
    return replace_exact(
        source,
        "subtitleText = stringResource(MR.strings.crash_screen_description, stringResource(MR.strings.app_name)),",
        """subtitleText = stringResource(MR.strings.app_name) + " encountered an error. You can export a crash log to help diagnose it.",""",
        "remove Discord crash report instruction",
    )


TRANSFORMS = {
    MORE: more_screen,
    ABOUT: about_screen,
    LOGO: logo_header,
    MAIN: main_activity,
    CRASH: crash_screen,
}


def patch(root: Path):
    root = root.resolve()
    if not (root / "LICENSE").is_file():
        raise WhiteLabelPatchError("Upstream open-source license must remain intact")
    pending = {}
    for rel, operation in TRANSFORMS.items():
        dest = root / rel
        if not dest.is_file():
            raise WhiteLabelPatchError(f"Missing audited source: {rel}")
        content = dest.read_text(encoding="utf-8")
        revised = operation(content)
        if revised == content:
            raise WhiteLabelPatchError(f"Patch had no effect: {rel}")
        pending[dest] = revised
    for dest, revised in pending.items():
        dest.write_text(revised, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
