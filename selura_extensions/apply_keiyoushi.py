#!/usr/bin/env python3
"""Create an isolated Selura MangaDex module from a pinned Keiyoushi checkout.

Phase 1 uses Keiyoushi as a build-tool dependency. The Selura extension has
its own APK identity and generated source IDs; originals remain untouched.
Keiyoushi is Apache-2.0: copyright and attribution are retained.
"""

import argparse
from pathlib import Path
import re
import shutil
import subprocess

UPSTREAM = "https://github.com/keiyoushi/extensions-source"
PIN = "ff521c17bb3e503c01e658e8fac00b60a95829f3"
SOURCE = Path("src/all/mangadex")
DEST = Path("src/all/seluramangadex")
OLD_PACKAGE = "eu.kanade.tachiyomi.extension.all.mangadex"
NEW_PACKAGE = "eu.kanade.tachiyomi.extension.all.seluramangadex"
SETTINGS_MARKER = "\nloadAllIndividualExtensions()\n"


class ContractError(RuntimeError):
    """The pinned upstream tree differs from the supported baseline."""


def prepare(checkout: Path, version_code: int = 1, verify_git: bool = True) -> Path:
    checkout = checkout.resolve()
    if not (1 <= version_code <= 100000):
        raise ContractError("versionCode must be between 1 and 100000")

    if verify_git:
        commit = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        if commit != PIN:
            raise ContractError(f"Unexpected Keiyoushi revision: {commit}")

    license_file = checkout / "LICENSE"
    if not license_file.is_file() or "Apache License" not in license_file.read_text(encoding="utf-8"):
        raise ContractError("Keiyoushi Apache-2.0 license is missing")

    source = checkout / SOURCE
    destination = checkout / DEST
    gradle = source / "build.gradle.kts"
    settings = checkout / "settings.gradle.kts"
    if destination.exists():
        raise ContractError("Selura destination exists; refusing to overwrite it")
    if not gradle.is_file() or not settings.is_file():
        raise ContractError("Expected Keiyoushi source/build layout is missing")

    spec = gradle.read_text(encoding="utf-8")
    if (spec.count('name = "MangaDex"') != 1 or
        spec.count("versionCode = 0") != 1 or
        spec.count('baseUrl = "https://mangadex.org"') != 1 or
        'libVersion = "1.6"' not in spec):
        raise ContractError("Unexpected MangaDex source configuration")

    marker_count = settings.read_text(encoding="utf-8").count(SETTINGS_MARKER)
    if marker_count != 1:
        raise ContractError("Unexpected Keiyoushi settings.gradle.kts layout")
    original_kt = list(source.rglob("*.kt"))
    if not original_kt or not any(
        OLD_PACKAGE in item.read_text(encoding="utf-8") for item in original_kt
    ):
        raise ContractError("Original MangaDex Kotlin package cannot be identified")

    # Copy, never move or alter the Keiyoushi original module.
    shutil.copytree(source, destination)
    for file in destination.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix in (".kt", ".pro") or file.name == "build.gradle.kts":
            body = file.read_text(encoding="utf-8")
            body = body.replace(OLD_PACKAGE, NEW_PACKAGE)
            if file.name == "build.gradle.kts":
                body = body.replace('name = "MangaDex"', 'name = "Selura MangaDex"')
                body = body.replace("versionCode = 0", f"versionCode = {version_code}")
                # Do not intercept MangaDex links meant for a user's existing extension.
                body, matches = re.subn(
                    r"(?ms)^    deeplink \{\n.*?^    \}\n",
                    "", body,
                )
                if matches != 1:
                    raise ContractError("Unexpected MangaDex deep-link block")
                # The removed deep-link leaves one blank line that Spotless
                # rejects, between the source block and module closing brace.
                before = "    }\n\n}\n\ndependencies {"
                after = "    }\n}\n\ndependencies {"
                if body.count(before) != 1:
                    raise ContractError("Unexpected Keiyoushi format after deep-link removal")
                body = body.replace(before, after)
            if file.suffix == ".kt":
                # The network header must identify the publisher truthfully.
                body = body.replace('"Keiyoushi"', '"Selura"')
            file.write_text(body, encoding="utf-8")

    settings.write_text(
        settings.read_text(encoding="utf-8").replace(
            SETTINGS_MARKER,
            '\nloadIndividualExtension("all", "seluramangadex")\n',
        ),
        encoding="utf-8",
    )
    shutil.copyfile(license_file, destination / "LICENSE")
    (destination / "SELURA_ORIGIN.md").write_text(
        "# Selura MangaDex provenance\n\n"
        f"Derived from {UPSTREAM} at commit `{PIN}`.\n\n"
        "Original project and contributors: Keiyoushi, Tachiyomi and MangaDex "
        "source contributors. See the original LICENSE, retained alongside "
        "this extension.\n\n"
        "Selura changes: copied into a separate module; changed package, "
        "display/source name, versionCode and extension network header; "
        "removed competing deep-link intents. Original module is unchanged.\n",
        encoding="utf-8",
    )
    if 'name = "MangaDex"' not in gradle.read_text(encoding="utf-8"):
        raise ContractError("Original module unexpectedly modified")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--version-code", type=int, default=1)
    args = parser.parse_args()
    module = prepare(args.checkout, args.version_code)
    print(f"Prepared independent Selura module {module}")


if __name__ == "__main__":
    main()
