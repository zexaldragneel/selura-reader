#!/usr/bin/env python3
"""Apply Seiryn visible branding to the tested native Selura APK.

Run LAST, after all pinned native engine, UI and recovery patches. Keep
com.selura.manga, signing, GitHub metadata and all library/source identities.
Artwork is derived from the exact visual selected by the owner (2026-10-24).
"""
import argparse
import hashlib
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
RES = "app/src/main/res/drawable-nodpi"
ASSETS = {
    "seiryn_brand_art.webp": "df66baf66bff143af13df517834b3151f66d8df4973bdf027fa2a0b90c5f8b8a",
    "seiryn_launcher_icon.webp": "02f2b9296ce651cde605279b489b270f2cb55d7354c2dba74ccbace02b39fbd9",
}
I18N = "i18n/src/commonMain/moko-resources/base/strings.xml"
MANIFEST = "app/src/main/AndroidManifest.xml"
ABOUT = "app/src/main/java/eu/kanade/presentation/more/settings/screen/about/AboutScreen.kt"
LOGO = "app/src/main/java/eu/kanade/presentation/more/LogoHeader.kt"
BROWSE = "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt"
UPDATER = "app/src/main/java/eu/kanade/tachiyomi/ui/main/SeluraStartupUpdateCheck.kt"
GRADLE = "settings.gradle.kts"


class SeirynBrandError(RuntimeError):
    """Out-of-contract native source; stop rather than partially rebrand."""


def one(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SeirynBrandError(f"{label}: expected 1 marker, found {n}")
    return text.replace(old, new, 1)


def updated_files(before: dict[str, str]) -> dict[str, str]:
    after = dict(before)
    s = after[I18N]
    after[I18N] = one(s, '<string name="app_name" translatable="false">Selura Manga</string>',
                      '<string name="app_name" translatable="false">Seiryn</string>', I18N)

    s = after[MANIFEST]
    s = one(s, 'android:icon="@drawable/selura_manga_icon"',
            'android:icon="@drawable/seiryn_launcher_icon"', MANIFEST)
    s = one(s, 'android:roundIcon="@drawable/selura_manga_icon"',
            'android:roundIcon="@drawable/seiryn_launcher_icon"', MANIFEST)
    after[MANIFEST] = s

    s = after[LOGO]
    s = one(s, "import androidx.compose.material3.Icon\n",
            "import androidx.compose.foundation.Image\n", LOGO)
    s = one(s, "import androidx.compose.material3.MaterialTheme\n",
            "import androidx.compose.ui.layout.ContentScale\n", LOGO)
    s = one(s, """        Icon(
            painter = painterResource(R.drawable.selura_manga_icon),
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier
                .padding(iconPadding)
                .size(64.dp),
        )""",
            """        Image(
            painter = painterResource(R.drawable.seiryn_brand_art),
            contentDescription = "Seiryn",
            contentScale = ContentScale.Fit,
            modifier = Modifier
                .padding(iconPadding)
                .size(216.dp),
        )""", LOGO)
    after[LOGO] = s

    s = after[ABOUT]
    after[ABOUT] = one(s, 'title = "Selura Manga",\n                        subtitle = "Developed by Zexal Dragneel",',
                           'title = "Seiryn",\n                        subtitle = "Developed by Zexal Dragneel",', ABOUT)

    s = after[BROWSE]
    s = one(s, 'title = "Add Selura extensions",', 'title = "Add Seiryn extensions",', BROWSE)
    after[BROWSE] = one(s, 'subtitle = "Review and add the Selura extension store",',
                            'subtitle = "Review and add the Seiryn extension store",', BROWSE)

    s = after[UPDATER]
    for old, new in (
        ('"Selura Manga update available"', '"Seiryn update available"'),
        ('"Allow installs from Selura in Android Settings, then return and tap Install."',
         '"Allow installs from Seiryn in Android Settings, then return and tap Install."'),
        ('"Allow installs from Selura in Settings, then return and tap Install."',
         '"Allow installs from Seiryn in Settings, then return and tap Install."'),
        ('"Download and verify the APK inside Selura. "',
         '"Download and verify the APK inside Seiryn. "'),
    ):
        s = one(s, old, new, UPDATER)
    after[UPDATER] = s

    after[GRADLE] = one(after[GRADLE],
                        'rootProject.name = "SeluraManga" // Selura customization',
                        'rootProject.name = "Seiryn" // visible branding only; app ID unchanged', GRADLE)
    return after


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise SeirynBrandError("Pinned native engine and upstream license required")
    app_build = (root / "app/build.gradle.kts").read_text(encoding="utf-8")
    if 'applicationId = "com.selura.manga"' not in app_build:
        raise SeirynBrandError("Existing com.selura.manga upgrade identity must remain")
    pending = {}
    for rel in (I18N, MANIFEST, ABOUT, LOGO, BROWSE, UPDATER, GRADLE):
        f = root / rel
        if not f.is_file():
            raise SeirynBrandError(f"Missing pinned native branding path: {rel}")
        pending[rel] = f.read_text(encoding="utf-8")
    after = updated_files(pending)

    art_dir = HERE / "seiryn_branding"
    files = {}
    for name, digest in ASSETS.items():
        asset = art_dir / name
        target = root / RES / name
        if target.exists() or not asset.is_file():
            raise SeirynBrandError(f"Conflicting/missing owner-approved image: {name}")
        raw = asset.read_bytes()
        if raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
            raise SeirynBrandError(f"Unsupported Seiryn artwork: {name}")
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SeirynBrandError(f"Seiryn owner image digest mismatch: {name}")
        files[target] = asset

    if 'applicationId = "com.selura.manga"' not in app_build:
        raise SeirynBrandError("App ID changed")
    if 'https://raw.githubusercontent.com/zexaldragneel/selura-extensions/repo/repo.json' not in after[BROWSE]:
        raise SeirynBrandError("Original extension catalog URL must remain")
    if '"com.selura.manga"' not in after[UPDATER] or "selura-reader" not in after[UPDATER]:
        raise SeirynBrandError("Update feed identity must remain")
    # Full preflight before any writes; never edit downloads, data, backups or sources.
    for rel, content in after.items():
        (root / rel).write_text(content, encoding="utf-8")
    (root / RES).mkdir(parents=True, exist_ok=True)
    for destination, source in files.items():
        shutil.copyfile(source, destination)
    print("Applied Seiryn name + user-approved art, retained com.selura.manga and signer.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
