#!/usr/bin/env python3
"""Prepare separate Selura-owned, Keiyoushi-derived manga extensions.

Only six selected source modules are copied from a pinned Apache-2.0
snapshot. Unselected modules are excluded from the build.
"""

from pathlib import Path
import argparse
import re
import shutil
import subprocess

PIN = "ff521c17bb3e503c01e658e8fac00b60a95829f3"
UPSTREAM = "https://github.com/keiyoushi/extensions-source"
EXPECTED_MODULES = (
    ("all", "mangaplus", "seluramangaplus", "MANGA Plus by SHUEISHA"),
    ("all", "webtoons", "selurawebtoons", "Webtoons.com"),
    ("all", "mangafire", "seluramangafire", "MangaFire"),
    ("en", "mangapill", "seluramangapill", "MangaPill"),
    ("en", "mangakatana", "seluramangakatana", "MangaKatana"),
    ("en", "mangabat", "seluramangabat", "Mangabat"),
)
SETTINGS_MARKER = "\nloadAllIndividualExtensions()\n"


class ImportErrorContract(RuntimeError):
    """Pinned source is missing or has changed unexpectedly."""


def prepare(checkout: Path, version_code: int, verify_git: bool = True) -> list[str]:
    checkout = checkout.resolve()
    if not 100 <= version_code <= 100000:
        raise ImportErrorContract("Version code must be between 100 and 100000")
    if verify_git:
        head = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        if head != PIN:
            raise ImportErrorContract(f"Unexpected Keiyoushi revision: {head}")

    license_path = checkout / "LICENSE"
    if not license_path.is_file() or "Apache License" not in license_path.read_text(encoding="utf-8"):
        raise ImportErrorContract("Upstream Apache-2.0 license must be retained")
    settings = checkout / "settings.gradle.kts"
    if not settings.is_file() or settings.read_text(encoding="utf-8").count(SETTINGS_MARKER) != 1:
        raise ImportErrorContract("Unsupported upstream settings.gradle.kts layout")

    for language, upstream, selura, display_name in EXPECTED_MODULES:
        src = checkout / "src" / language / upstream
        dst = checkout / "src" / language / selura
        gradle = src / "build.gradle.kts"
        if dst.exists():
            raise ImportErrorContract(f"Refusing to overwrite existing extension: {dst}")
        if not gradle.is_file():
            raise ImportErrorContract(f"Missing upstream module: {src}")
        body = gradle.read_text(encoding="utf-8")
        if body.count(f'name = "{display_name}"') != 1 or 'libVersion = "1.6"' not in body:
            raise ImportErrorContract(f"Unexpected upstream module configuration: {src}")
        if not any((src / "src").rglob("*.kt")):
            raise ImportErrorContract(f"Missing Kotlin code: {src}")

    tasks = []
    for language, upstream, selura, display_name in EXPECTED_MODULES:
        src = checkout / "src" / language / upstream
        dst = checkout / "src" / language / selura
        shutil.copytree(src, dst)
        from_pkg = f"eu.kanade.tachiyomi.extension.{language}.{upstream}"
        to_pkg = f"eu.kanade.tachiyomi.extension.{language}.{selura}"
        for file in dst.rglob("*"):
            if not file.is_file():
                continue
            if file.suffix in (".kt", ".java", ".kts", ".pro", ".xml"):
                content = file.read_text(encoding="utf-8")
                content = content.replace(from_pkg, to_pkg)
                if file.name == "build.gradle.kts":
                    if "pkgName =" in content:
                        raise ImportErrorContract(f"Unexpected custom package for {upstream}")
                    # Avoid competing with original extension deep-link intents.
                    content = re.sub(r"(?ms)^    deeplink \{\n.*?^    \}\n", "", content)
                    # VersionId 2 gives new source IDs with natural display names.
                    # Two Webtoons locales carried explicit historical IDs.
                    # Remap them without emptying the Kotlin DSL when{} branches.
                    if upstream == "webtoons":
                        old_ids = {
                            "8749627068478740298": "2440516289140843419",
                            "2959982438613576472": "4442238007005333330",
                        }
                        for previous, current in old_ids.items():
                            expected = f"id = {previous}"
                            if content.count(expected) != 1:
                                raise ImportErrorContract(f"Missing Webtoons ID {previous}")
                            content = content.replace(expected, f"id = {current}L")
                    content = re.sub(
                        r"(?m)^([ \t]*)source \{\n",
                        lambda match: match.group(0) + match.group(1) + "    versionId = 2\n",
                        content,
                    )
                    content = content.replace(
                        f'name = "{display_name}"',
                        f'name = "{display_name}"\n    pkgName = "{language}.{selura}"',
                    )
                    content = re.sub(
                        r"(?m)^([ \t]*)versionCode = \d+[ \t]*$",
                        rf"\g<1>versionCode = {version_code}",
                        content,
                    )
                    content = re.sub(r"\n{3,}", "\n\n", content)
                file.write_text(content, encoding="utf-8")
        shutil.copyfile(license_path, dst / "LICENSE")
        (dst / "SELURA_ORIGIN.md").write_text(
            f"# {display_name} — Selura derivative\n\n"
            f"Original: {UPSTREAM} revision {PIN}, src/{language}/{upstream}.\n"
            "Apache-2.0 license and contributor notices retained.\n"
            f"Separate APK package {to_pkg}; source ID versionId = 2.\n"
            "Original module untouched. Provider service availability is external.\n",
            encoding="utf-8",
        )
        tasks.extend([f":src:{language}:{selura}:assembleRelease", f":src:{language}:{selura}:lintRelease"])
    settings.write_text(
        settings.read_text(encoding="utf-8").replace(
            SETTINGS_MARKER,
            "\n" + "".join(
                f'loadIndividualExtension("{language}", "{selura}")\n'
                for language, _, selura, _ in EXPECTED_MODULES
            ),
        ),
        encoding="utf-8",
    )
    return tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--task-file", type=Path, default=None)
    args = parser.parse_args()
    tasks = prepare(args.checkout, args.version_code)
    if args.task_file is not None:
        args.task_file.write_text("\n".join(tasks) + "\n", encoding="utf-8")
    print("\n".join(tasks))


if __name__ == "__main__":
    main()
