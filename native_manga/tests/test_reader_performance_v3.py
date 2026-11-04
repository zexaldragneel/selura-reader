"""Reader Performance 3.0 telemetry contracts."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

v2 = load("reader_perf_v2_for_v3", "reader_performance_v2.py")
v3 = load("reader_perf_v3", "reader_performance_v3.py")
from test_reader_performance_v2 import CURRENT

class ReaderPerformanceV3Tests(unittest.TestCase):
    def test_instrumented_v2_source_and_safety(self):
        source = v3.patch_source(v2.patch_source(CURRENT))
        self.assertIn('Log.d("SeirynReaderPerf"', source)
        self.assertIn('elapsedMs >= 750L', source)
        self.assertIn('origin=$origin', source)
        self.assertIn('logSlowReaderStage("chapter-list"', source)
        self.assertIn('logSlowReaderStage("page-image"', source)
        self.assertIn('MAX_PAGES_AHEAD = 8', source)
        self.assertIn('downloadJobs.putIfAbsent(pageIndex, job)', source)
        self.assertIn('chapterCache.putImageToCache(imageUrl, imageResponse)', source)
        self.assertIn('if (e is CancellationException)', source)
        for sensitive in ('page.url', 'imageUrl=$', 'chapter.title', 'source.name', 'e.message'):
            self.assertNotIn(sensitive, source)
    def test_fail_closed_on_double_apply_or_missing_contract(self):
        source = v2.patch_source(CURRENT)
        with self.assertRaises(v3.TelemetryContractError):
            v3.patch_source(v3.patch_source(source))
        with self.assertRaises(v3.TelemetryContractError):
            v3.patch_source(source.replace("MAX_PAGES_AHEAD = 8", "MAX_PAGES_AHEAD = 9"))

if __name__ == "__main__":
    unittest.main()
