"""Tests for Android externally installed extension refresh recovery."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extension_local_rescan", ROOT / "extension_local_rescan.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ORIGINAL = """class ExtensionManager {
    private suspend fun loadExtensions() = loadMutex.withLock {
        try {
            val extensions = ExtensionLoader.loadExtensions(context, loadedExtensionMapFlow.value)
            refreshStatuses()
        } catch (e: Throwable) {
        }
    }

    suspend fun findAvailableExtensions() {
        val extensions: List<Extension.Available> = try {
            fetchExtensions()
        } catch (e: Exception) {
            return
        }
        setAvailableExtensions(extensions)
    }

    private fun refreshStatuses() {
    }
}
"""


class ExtensionLocalRescanTests(unittest.TestCase):
    def test_pull_refresh_rescans_android_installed_packages_first(self):
        result = mod.transform(ORIGINAL)
        self.assertIn("loadExtensions()", result)
        self.assertEqual(result.count("ExtensionLoader.loadExtensions(context, loadedExtensionMapFlow.value)"), 1)
        self.assertIn("suspend fun findAvailableExtensions() {\n", result)
        self.assertIn("        loadExtensions()\n        val extensions: List<Extension.Available> = try {", result)
        self.assertLess(
            result.index("        loadExtensions()\n        val extensions: List<Extension.Available> = try {"),
            result.index("            fetchExtensions()"),
        )
        self.assertIn("setAvailableExtensions(extensions)", result)
        self.assertIn("private fun refreshStatuses()", result)
        self.assertNotIn("uninstallExtension(", result)
        self.assertNotIn("PackageManager.QUERY_ALL_PACKAGES", result)
        self.assertNotIn("untrust(", result)
        self.assertNotIn("clearData(", result)

    def test_patch_applies_once_and_fails_closed_when_upstream_changes(self):
        result = mod.transform(ORIGINAL)
        with self.assertRaises(mod.ExtensionLocalRescanPatchError):
            mod.transform(result)
        for part in (
            "suspend fun findAvailableExtensions()",
            "private suspend fun loadExtensions() = loadMutex.withLock",
            "ExtensionLoader.loadExtensions(context, loadedExtensionMapFlow.value)",
            "private fun refreshStatuses()",
        ):
            with self.subTest(part=part):
                with self.assertRaises(mod.ExtensionLocalRescanPatchError):
                    mod.transform(ORIGINAL.replace(part, "unknown"))

    def test_file_patch_preserves_unchanged_contents_on_failed_second_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / mod.MANAGER
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(ORIGINAL, encoding="utf-8")
            mod.patch(Path(tmp))
            after = target.read_text(encoding="utf-8")
            self.assertIn("Re-enumerate local packages", after)
            with self.assertRaises(mod.ExtensionLocalRescanPatchError):
                mod.patch(Path(tmp))
            self.assertEqual(target.read_text(encoding="utf-8"), after)


if __name__ == "__main__":
    unittest.main()
