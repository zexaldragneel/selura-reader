#!/usr/bin/env python3
"""Install the independently maintained Selura source into a pinned Keiyoushi build checkout.

Only the build framework / shared GalleryAdults implementation comes from the
audited Keiyoushi commit. The provider-specific extension source is stored in
Selura itself; it is compiled as a separately signed, uniquely named APK.

Upstream: keiyoushi/extensions-source ff521c17bb3e503c01e658e8fac00b60a95829f3
License: Apache-2.0. Preserve the full upstream LICENSE in the checkout.
"""

import argparse
import pathlib
import shutil
import subprocess

UPSTREAM_SHA = "ff521c17bb3e503c01e658e8fac00b60a95829f3"
MODULE = "src/all/seluranhentaito"
SOURCE_PACKAGE = "eu.kanade.tachiyomi.extension.all.seluranhentaito"
PACKAGE_ID = "eu.kanade.tachiyomi.extension.all.seluranhentaito"

class UpstreamContractError(RuntimeError):
    pass

def patch(checkout: pathlib.Path, provider: pathlib.Path, verify_git: bool = True):
    checkout = checkout.resolve()
    provider = provider.resolve()

    if verify_git:
        actual = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True,
        ).strip()
        if actual != UPSTREAM_SHA:
            raise UpstreamContractError(f"Unexpected Keiyoushi checkout {actual}")

    if not (checkout / "LICENSE").is_file():
        raise UpstreamContractError("Original Apache-2.0 license is missing.")
    old = checkout / "src/all/nhentaito/build.gradle.kts"
    if not old.is_file():
        raise UpstreamContractError("Expected pinned NHentai.to source module.")
    settings = checkout / "settings.gradle.kts"
    settings_text = settings.read_text(encoding="utf-8")
    needle = "\nloadAllIndividualExtensions()\n"
    if settings_text.count(needle) != 1:
        raise UpstreamContractError("Expected exactly one upstream module loader.")

    source = provider / "NHentaiTo.kt"
    gradle = provider / "build.gradle.kts"
    kotlin = source.read_text(encoding="utf-8")
    definition = gradle.read_text(encoding="utf-8")
    if f"package {SOURCE_PACKAGE}" not in kotlin:
        raise UpstreamContractError("Incorrect Selura source package.")
    for required in (
        "override suspend fun pageListParse",
        "pageListParseAlternative(document)",
        "response.code == 401 || response.code == 403 || response.code == 429",
        "Unable to load image from NHentai.to",
    ):
        if required not in kotlin:
            raise UpstreamContractError(f"Missing safety/repair contract: {required}")
    if 'name = "Selura NHentai.to"' not in definition:
        raise UpstreamContractError("Selura extension name not set.")
    if 'baseUrl = "https://nhentai.to"' not in definition:
        raise UpstreamContractError("Site mismatch.")
    if 'ContentWarning.NSFW' not in definition:
        raise UpstreamContractError("Adult content warning is required.")

    dest = checkout / MODULE
    if dest.exists():
        raise UpstreamContractError(f"Source {MODULE} already exists in build checkout.")

    # Fail closed: leave the original Keiyoushi NHentai.to module untouched.
    # Build only the new module, avoiding 1000s of unrelated source modules.
    target = dest / "src/eu/kanade/tachiyomi/extension/all/seluranhentaito/NHentaiTo.kt"
    target.parent.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, target)
    shutil.copyfile(gradle, dest / "build.gradle.kts")
    settings.write_text(
        settings_text.replace(needle, '\nloadIndividualExtension("all", "seluranhentaito")\n'),
        encoding="utf-8",
    )
    assert old.is_file()
    print(f"Prepared distinct first-party Selura source package {PACKAGE_ID}")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=pathlib.Path)
    parser.add_argument("--provider", type=pathlib.Path,
                        default=pathlib.Path(__file__).parent / "nhentaito")
    args = parser.parse_args()
    patch(args.checkout, args.provider)

if __name__ == "__main__":
    main()
