#!/usr/bin/env python3
"""Prepare 18 isolated Selura-maintained orphaned manga-source extensions.

Copies audited module paths from an exact Keiyoushi Apache-2.0 snapshot.
Original modules and existing installed source IDs are never modified.
New packages and generated/manual source IDs are deterministic and distinct.
"""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess

PIN = "ff521c17bb3e503c01e658e8fac00b60a95829f3"
UPSTREAM = "https://github.com/keiyoushi/extensions-source"
SETTINGS_MARKER = "\nloadAllIndividualExtensions()\n"
SOURCE_VERSION_ID = 7301  # immutable for this new source family; do not change after publication

# language, actual upstream module, isolated internal module, exact visible name
SOURCES = (
    ("all", "hentai3", "selurahentai3", "3Hentai"),
    ("en", "allporncomic", "seluraallporncomic", "AllPornComic"),
    ("en", "asurascans", "seluraasurascans", "Asura Scans"),
    ("en", "doujins", "seluradoujins", "Doujins"),
    ("en", "flamecomics", "seluraflamecomics", "Flame Comics"),
    ("all", "hdoujin", "selurahdoujin", "HDoujin"),
    ("en", "hentai4free", "selurahentai4free", "Hentai4Free"),
    ("all", "hentaihand", "selurahentaihand", "HentaiHand"),
    ("en", "hentairead", "selurahentairead", "HentaiRead"),
    ("en", "hiperdex", "selurahiperdex", "Hiperdex"),
    ("en", "hivescans", "selurahivescans", "Hive Scans"),
    ("en", "mangarawclub", "seluramangageko", "MangaGeko"),
    ("en", "mangakakalot", "seluramangakakalot", "Mangakakalot"),
    ("en", "mgreadio", "seluramgreadio", "Mgread.io"),
    ("en", "toongod", "seluratoongod", "ToonGod"),
    ("en", "toonily", "seluratoonily", "Toonily"),
    ("en", "vortexscans", "seluravortexscans", "Vortex Scans"),
    ("en", "webtoonxyz", "selurawebtoonxyz", "WebtoonXYZ"),
)


class SourceContractError(RuntimeError):
    """Refuse an unsafe or unsupported source-tree change."""


def alternate_id(module: str, old_id: str) -> int:
    # Stable positive 63-bit ID; changing the seed after release would orphan books.
    seed = ("selura-orphaned-v1:" + module + ":" + old_id).encode("utf-8")
    return (int.from_bytes(hashlib.sha256(seed).digest()[:8], "big") & ((1 << 63) - 1)) or 1


def rewrite_gradle(source: str, language: str, upstream: str, isolated: str,
                   display: str, version_code: int) -> str:
    expected = 'name = "' + display + '"'
    if source.count(expected) != 1 or source.count('libVersion = "1.6"') != 1:
        raise SourceContractError("Unexpected pinned Gradle metadata: " + upstream)
    if len(re.findall(r"(?m)^\s*versionCode\s*=\s*\d+\s*$", source)) != 1:
        raise SourceContractError("Unsupported versionCode declaration: " + upstream)
    if not re.search(r"(?m)^\s*source\s*\{\s*$", source):
        raise SourceContractError("No source declarations: " + upstream)

    # Explicit historical source IDs must not claim the IDs of installed extensions.
    source = re.sub(
        r"\bid\s*=\s*(\d+)L?\b",
        lambda m: "id = " + str(alternate_id(isolated, m.group(1))) + "L",
        source,
    )
    # Also replace pre-existing generated-ID version markers, including v2.
    source = re.sub(r"(?m)^\s*versionId\s*=\s*\d+\s*\n", "", source)
    source = re.sub(
        r"(?m)^(\s*)source\s*\{\s*\n",
        lambda m: m.group(0) + m.group(1) + "    versionId = " + str(SOURCE_VERSION_ID) + "\n",
        source,
    )
    # Remove only first-level deeplink declarations to avoid duplicate URL handling.
    source = re.sub(r"(?ms)^    deeplink \{\n.*?^    \}\n", "", source)
    if "deeplink {" in source:
        raise SourceContractError("Unsupported deep-link block in " + upstream)
    own_pkg = language + "." + isolated
    if re.search(r"(?m)^\s*pkgName\s*=", source):
        source = re.sub(r'(?m)^(\s*)pkgName\s*=\s*"[^"]+"\s*$',
                        lambda m: m.group(1) + 'pkgName = "' + own_pkg + '"', source)
    else:
        source = source.replace(expected, expected + '\n    pkgName = "' + own_pkg + '"', 1)
    source = re.sub(r"(?m)^(\s*)versionCode\s*=\s*\d+\s*$",
                    lambda m: m.group(1) + "versionCode = " + str(version_code), source)
    # Keep the exact upstream display names: never prepend 'Selura '.
    source = re.sub(r"\n{3,}", "\n\n", source)
    if source.count('pkgName = "' + own_pkg + '"') != 1:
        raise SourceContractError("Failed unique package identity: " + upstream)
    return source


def prepare(checkout: Path, version_code: int, verify_git: bool = True) -> list[str]:
    checkout = checkout.resolve()
    if not 1000 <= version_code <= 1000000:
        raise SourceContractError("versionCode must be 1000..1000000")
    if verify_git:
        head = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != PIN:
            raise SourceContractError("Upstream revision differs from approved pin: " + head)
    license_file = checkout / "LICENSE"
    settings_file = checkout / "settings.gradle.kts"
    if not license_file.is_file() or "Apache License" not in license_file.read_text(encoding="utf-8"):
        raise SourceContractError("The Apache-2.0 license is missing")
    if not settings_file.is_file() or settings_file.read_text(encoding="utf-8").count(SETTINGS_MARKER) != 1:
        raise SourceContractError("Unexpected settings.gradle.kts structure")

    # Preflight all 18 before creating anything, so one missing source cannot
    # silently turn the release into a misleading partial catalogue.
    rewrites = {}
    for language, upstream, isolated, display in SOURCES:
        source = checkout / "src" / language / upstream
        dest = checkout / "src" / language / isolated
        if not (source / "build.gradle.kts").is_file() or dest.exists():
            raise SourceContractError("Missing source or destination already exists: " + str(source))
        original = (source / "build.gradle.kts").read_text(encoding="utf-8")
        rewrites[(language, isolated)] = rewrite_gradle(
            original, language, upstream, isolated, display, version_code
        )

    tasks = []
    for language, upstream, isolated, display in SOURCES:
        source = checkout / "src" / language / upstream
        dest = checkout / "src" / language / isolated
        shutil.copytree(source, dest)
        original_pkg = "eu.kanade.tachiyomi.extension." + language + "." + upstream
        new_pkg = "eu.kanade.tachiyomi.extension." + language + "." + isolated
        for file in dest.rglob("*"):
            if file.is_file() and file.suffix in (".kt", ".java", ".kts", ".xml", ".pro"):
                body = file.read_text(encoding="utf-8").replace(original_pkg, new_pkg)
                if file.name == "build.gradle.kts" and file.parent == dest:
                    body = rewrites[(language, isolated)]
                file.write_text(body, encoding="utf-8")
        shutil.copyfile(license_file, dest / "LICENSE")
        (dest / "SELURA_ORIGIN.md").write_text(
            "# " + display + " — independent Selura build\n\n"
            "Original source: " + UPSTREAM + " at " + PIN + "\n"
            "Original module: src/" + language + "/" + upstream + "\n"
            "License: Apache-2.0, preserved verbatim in LICENSE.\n"
            "Separate APK package: " + new_pkg + "\n"
            "Source versionId: " + str(SOURCE_VERSION_ID) + "\n"
            "Historical explicit IDs remapped deterministically; upstream data untouched.\n"
            "Content provider and real-time website availability are outside Selura control.\n",
            encoding="utf-8",
        )
        tasks.extend((
            ":src:" + language + ":" + isolated + ":assembleRelease",
            ":src:" + language + ":" + isolated + ":lintRelease",
        ))
    updated = settings_file.read_text(encoding="utf-8").replace(
        SETTINGS_MARKER,
        "\n" + "".join(
            'loadIndividualExtension("' + language + '", "' + isolated + '")\n'
            for language, _, isolated, _ in SOURCES
        ),
    )
    settings_file.write_text(updated, encoding="utf-8")
    return tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--task-file", type=Path)
    parser.add_argument("--shard", type=int, choices=(0, 1, 2), default=0)
    args = parser.parse_args()
    tasks = prepare(args.checkout, args.version_code)
    shard_tasks = [t for index in range(len(SOURCES))
                   if index % 3 == args.shard for t in tasks[index * 2:index * 2 + 2]]
    if args.task_file:
        args.task_file.write_text("\n".join(shard_tasks) + "\n", encoding="utf-8")
    print("\n".join(shard_tasks))


if __name__ == "__main__":
    main()
