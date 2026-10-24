#!/usr/bin/env python3
"""Generate a public-safe update manifest from an already verified signed APK.

No code, authentication material, personal data, or private file contents are
published. The generated JSON still MUST NOT go public without owner approval.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

OWNER = "zexaldragneel"
REPO = "selura-reader"
APPLICATION_ID = "com.selura.manga"
TAG_PATTERN = re.compile(r"^test-native-(?:pr-[0-9]+|dispatch)-run-[0-9]+$")


def load_release_changes(path: Path, tag: str) -> dict:
    """Read human-reviewed notes for THIS PR, never another branch's notes."""
    match = re.fullmatch(r"test-native-pr-([0-9]+)-run-[0-9]+", tag)
    if match is None:
        raise ValueError("PR-scoped release notes require a matching PR release tag.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"prNumber", "added", "improved", "fixed"}:
        raise ValueError("Release note fields must be prNumber, added, improved, fixed.")
    if type(data["prNumber"]) is not int or data["prNumber"] != int(match.group(1)):
        raise ValueError("Release notes belong to another pull request; update them for this PR.")
    result = {}
    for name in ("added", "improved", "fixed"):
        items = data[name]
        if not isinstance(items, list) or len(items) > 5:
            raise ValueError(f"Invalid {name} changelog section")
        if any(
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            or len(item) > 180
            or "\n" in item
            for item in items
        ):
            raise ValueError(f"Invalid {name} changelog entry")
        result[name] = items
    if not 1 <= sum(map(len, result.values())) <= 12:
        raise ValueError("Release changelog must contain 1–12 concise, verified changes.")
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > 2300:
        raise ValueError("Release changelog exceeds the public feed size budget.")
    return result


def create_manifest(*, version_code: int, tag: str, apk: Path, changes: dict | None = None) -> dict:
    if not (1000 < version_code < 2_100_000_000):
        raise ValueError("Invalid Android version code.")
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Only known immutable Selura native APK release tags are supported.")
    if not apk.is_file() or apk.stat().st_size < 100000:
        raise ValueError("Refusing to publish an absent or empty signed native APK.")
    sha256 = hashlib.file_digest(apk.open("rb"), "sha256").hexdigest()
    manifest = {
        "schemaVersion": 1,
        "applicationId": APPLICATION_ID,
        "versionCode": version_code,
        "versionName": f"Seiryn Build {version_code - 1000}",
        "notes": (
            "What's new: " + next(
                (entry for section in ("added", "improved", "fixed")
                 for entry in changes[section]),
                "See the GitHub release for details.",
            )
            if changes is not None else
            "Seiryn improvements and fixes. Review the GitHub release before installing."
        ),
        "releaseUrl": f"https://github.com/{OWNER}/{REPO}/releases/tag/{tag}",
        "sha256": sha256,
    }
    if changes is not None:
        manifest["changes"] = changes
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--changes-file", type=Path,
        help="Human-reviewed PR-scoped release notes; required by PR publication CI",
    )
    args = parser.parse_args()
    changes = load_release_changes(args.changes_file, args.tag) if args.changes_file else None
    data = create_manifest(version_code=args.version_code, tag=args.tag, apk=args.apk, changes=changes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Validated update metadata for build {args.version_code} at {args.output}")


if __name__ == "__main__":
    main()
