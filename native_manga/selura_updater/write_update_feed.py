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


def create_manifest(*, version_code: int, tag: str, apk: Path) -> dict:
    if not (1000 < version_code < 2_100_000_000):
        raise ValueError("Invalid Android version code.")
    if not TAG_PATTERN.fullmatch(tag):
        raise ValueError("Only known immutable Selura native APK release tags are supported.")
    if not apk.is_file() or apk.stat().st_size < 100000:
        raise ValueError("Refusing to publish an absent or empty signed native APK.")
    sha256 = hashlib.file_digest(apk.open("rb"), "sha256").hexdigest()
    return {
        "schemaVersion": 1,
        "applicationId": APPLICATION_ID,
        "versionCode": version_code,
        "versionName": f"Selura Manga Build {version_code - 1000}",
        "notes": "Selura Manga improvements and fixes. Review the GitHub release before installing.",
        "releaseUrl": f"https://github.com/{OWNER}/{REPO}/releases/tag/{tag}",
        "sha256": sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = create_manifest(version_code=args.version_code, tag=args.tag, apk=args.apk)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Validated update metadata for build {args.version_code} at {args.output}")


if __name__ == "__main__":
    main()
