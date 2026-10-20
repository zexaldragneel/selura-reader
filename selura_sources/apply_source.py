#!/usr/bin/env python3
"""Prepare a separate first-party Selura NHentai.net extension from pinned Yuzono build tools.

Original NHentai v1.4.62: https://github.com/yuzono/cursed-manga-extensions
Pinned source commit: 5dad5cf65dce98bb05ba8edf1f38770585e032b9
License: Apache-2.0. The original build framework and source stay intact.
"""

import argparse
import pathlib
import shutil
import subprocess

UPSTREAM_SHA = "5dad5cf65dce98bb05ba8edf1f38770585e032b9"
MODULE = "src/all/seluranhentai"
SOURCE_PACKAGE = "eu.kanade.tachiyomi.extension.all.seluranhentai"
PACKAGE_ID = SOURCE_PACKAGE


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
            raise UpstreamContractError(f"Unexpected Yuzono checkout {actual}")

    upstream = checkout / "src/all/nhentai"
    if not (checkout / "LICENSE").is_file():
        raise UpstreamContractError("Original Apache-2.0 license missing.")
    for required in ("build.gradle.kts", "res", "proguard-rules.pro"):
        if not (upstream / required).exists():
            raise UpstreamContractError(f"Original NHentai module missing {required}")
    original = (upstream / "build.gradle.kts").read_text(encoding="utf-8")
    if 'baseUrl = "https://nhentai.net"' not in original:
        raise UpstreamContractError("Pinned Yuzono NHentai domain unexpectedly changed.")

    settings = checkout / "settings.gradle.kts"
    settings_text = settings.read_text(encoding="utf-8")
    marker = "\nloadAllIndividualExtensions()\n"
    if settings_text.count(marker) != 1:
        raise UpstreamContractError("Unexpected Yuzono build project layout.")

    definition = (provider / "build.gradle.kts").read_text(encoding="utf-8")
    source = (provider / "NHentai.kt").read_text(encoding="utf-8")
    if 'name = "Selura NHentai"' not in definition:
        raise UpstreamContractError("Expected first-party source name.")
    if 'baseUrl = "https://nhentai.net"' not in definition:
        raise UpstreamContractError("Expected actual original NHentai.net hostname.")
    if "ContentWarning.NSFW" not in definition:
        raise UpstreamContractError("Missing adult-content warning.")
    if "7309872737163460316" in definition:
        raise UpstreamContractError("Source ID must differ from original to preserve existing library.")
    if f"package {SOURCE_PACKAGE}" not in source:
        raise UpstreamContractError("First-party Kotlin package mismatch.")

    for expected in (
        "data.pages.size != data.numPages",
        "val server = imageServer",
        "NhImageRecoveryInterceptor",
        "response.code == 401 || response.code == 403 || response.code == 429",
        "Regex(\"\"\"^i[0-9]+",
    ):
        if expected not in source:
            raise UpstreamContractError(f"Image reliability safeguard absent: {expected}")

    dest = checkout / MODULE
    if dest.exists():
        raise UpstreamContractError("Selura NHentai module already exists in build checkout.")

    target = dest / "src/eu/kanade/tachiyomi/extension/all/seluranhentai"
    target.mkdir(parents=True)
    for filename in ("NHentai.kt", "NHDto.kt", "NHUtils.kt"):
        content = (provider / filename).read_text(encoding="utf-8")
        if f"package {SOURCE_PACKAGE}" not in content:
            raise UpstreamContractError(f"Incorrect package in {filename}")
        (target / filename).write_text(content, encoding="utf-8")

    shutil.copyfile(provider / "build.gradle.kts", dest / "build.gradle.kts")
    shutil.copytree(upstream / "res", dest / "res")
    rules = (upstream / "proguard-rules.pro").read_text(encoding="utf-8")
    (dest / "proguard-rules.pro").write_text(
        rules.replace(
            "eu.kanade.tachiyomi.extension.all.nhentai",
            SOURCE_PACKAGE,
        ),
        encoding="utf-8",
    )

    # Import only the one first-party module; all source code of original
    # Yuzono packages is unchanged, including original APK identities.
    settings.write_text(
        settings_text.replace(
            marker, '\nloadIndividualExtension("all", "seluranhentai")\n',
        ),
        encoding="utf-8",
    )
    assert (upstream / "build.gradle.kts").read_text(encoding="utf-8") == original
    print(f"Prepared isolated {PACKAGE_ID} from pinned Yuzono build tools.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=pathlib.Path)
    parser.add_argument("--provider", type=pathlib.Path,
                        default=pathlib.Path(__file__).parent / "nhentai")
    args = parser.parse_args()
    patch(args.checkout, args.provider)


if __name__ == "__main__":
    main()
