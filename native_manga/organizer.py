"""Install independent smart collections and reading queue after Obsidian."""
from pathlib import Path
import argparse

ASSETS = Path(__file__).parent / "organizer"
BASE = "app/src/main/java/eu/kanade/"


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Organizer anchor changed: {old[:80]}")
    return text.replace(old, new, 1)


def apply(root):
    root = Path(root)
    if (root / BASE / "tachiyomi/ui/organizer/OrganizerScreen.kt").exists():
        raise ValueError("Organizer already installed")
    changed = {}
    p = BASE + "tachiyomi/ui/home/SeirynHomeTab.kt"
    s = (root / p).read_text(encoding="utf-8")
    s = once(s, 'OutlinedButton(onClick = { tabs.current = LibraryTab })', '''OutlinedButton(onClick = { navigator.push(eu.kanade.tachiyomi.ui.organizer.OrganizerScreen()) }) { Text(stringResource(R.string.organizer_title)) }
                        OutlinedButton(onClick = { tabs.current = LibraryTab })''')
    changed[p] = s
    p = BASE + "tachiyomi/ui/more/MoreTab.kt"
    s = (root / p).read_text(encoding="utf-8")
    changed[p] = once(s, "            onClickCategories =", "            onClickOrganizer = { navigator.push(eu.kanade.tachiyomi.ui.organizer.OrganizerScreen()) },\n            onClickCategories =")
    p = BASE + "presentation/more/MoreScreen.kt"
    s = (root / p).read_text(encoding="utf-8")
    anchor = "            item {\n                SwitchPreferenceWidget(\n                    title = stringResource(MR.strings.label_downloaded_only),"
    s = once(s, anchor, "            item { eu.kanade.tachiyomi.ui.organizer.SeirynBuildVersion() }\n" + anchor)
    s = once(s, "    onClickCategories: () -> Unit,", "    onClickOrganizer: () -> Unit,\n    onClickCategories: () -> Unit,")
    s = once(s, "            item {\n                TextPreferenceWidget(\n                    title = stringResource(MR.strings.categories)", '''            item {
                TextPreferenceWidget(
                    title = androidx.compose.ui.res.stringResource(eu.kanade.tachiyomi.R.string.organizer_title),
                    icon = MaterialSymbols.AutoMirroredRounded.Label,
                    onPreferenceClick = onClickOrganizer,
                )
            }
            item {
                TextPreferenceWidget(
                    title = stringResource(MR.strings.categories)''')
    changed[p] = s
    for name in ("OrganizerScreen.kt", "OrganizerViewModel.kt", "OrganizerRules.kt", "SeirynBuildVersion.kt"):
        changed[BASE + "tachiyomi/ui/organizer/" + name] = (ASSETS / name).read_text(encoding="utf-8")
    changed["app/src/main/res/values/seiryn_organizer.xml"] = (ASSETS / "strings.xml").read_text(encoding="utf-8")
    changed["app/src/test/java/eu/kanade/tachiyomi/ui/organizer/OrganizerRulesTest.kt"] = (ASSETS / "OrganizerRulesTest.kt").read_text(encoding="utf-8")
    for path, content in changed.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    apply(parser.parse_args().checkout)

