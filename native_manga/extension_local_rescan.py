#!/usr/bin/env python3
"""Rescan system-installed extension APKs on Browse -> Extensions pull refresh.

The pinned Mihon v0.21.2 ExtensionManager currently initializes installed
packages at app startup and relies on PACKAGE_REPLACED broadcasts afterward.
Android package installer events can be missed while the app is alive.
Its refresh UI merely fetches the remote repository index, not installed apps.

This patch deliberately changes no package visibility permission, signer/trust
policy, extension library ABI, source ID, store format or migration behavior.
"""
import argparse
from pathlib import Path

MANAGER = Path("app/src/main/java/eu/kanade/tachiyomi/extension/ExtensionManager.kt")


class ExtensionLocalRescanPatchError(RuntimeError):
    pass


OLD = """    suspend fun findAvailableExtensions() {
        val extensions: List<Extension.Available> = try {"""

NEW = """    suspend fun findAvailableExtensions() {
        // A manual APK update performed by Android's package installer may
        // not deliver an extension installation broadcast to Seiryn.
        // Re-enumerate local packages before refreshing the remote store.
        // This reuses the existing signature/trust/source validation and
        // does not install, uninstall or rewrite any extension.
        loadExtensions()
        val extensions: List<Extension.Available> = try {"""


def transform(source: str) -> str:
    required = (
        "private suspend fun loadExtensions() = loadMutex.withLock",
        "ExtensionLoader.loadExtensions(context, loadedExtensionMapFlow.value)",
        "suspend fun findAvailableExtensions()",
        "val extensions: List<Extension.Available> = try {",
        "private fun refreshStatuses()",
    )
    for contract in required:
        if contract not in source:
            raise ExtensionLocalRescanPatchError("Pinned extension manager drift: " + contract)
    if source.count(OLD) != 1:
        raise ExtensionLocalRescanPatchError(
            f"Expected one refresh anchor; found {source.count(OLD)}"
        )
    return source.replace(OLD, NEW, 1)


def patch(root: Path) -> None:
    target = root.resolve() / MANAGER
    if not target.is_file():
        raise ExtensionLocalRescanPatchError("Pinned ExtensionManager.kt not found")
    before = target.read_text(encoding="utf-8")
    after = transform(before)
    target.write_text(after, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    patch(parser.parse_args().checkout)
