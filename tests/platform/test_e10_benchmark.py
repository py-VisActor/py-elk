"""Targeted OS-usage accounting and archive safety, never a layout full run."""
from pathlib import Path
import io
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/platform'))
from benchmark_e10 import usage_metrics
from linux_e10 import extract_asset


class BenchmarkAccountingTests(unittest.TestCase):
    def usage(self, user, system, peak):
        return {'ru_utime': user, 'ru_stime': system, 'ru_maxrss': peak}

    def test_linux_usage_has_separate_cpu_seconds_and_peak_kib_conversion(self):
        metrics = usage_metrics(self.usage(.1, .2, 1000), self.usage(.15, .23, 1200),
                                self.usage(0, 0, 0), self.usage(.5, .1, 2000), 1_000_000_000, 3_000_000_000)
        self.assertEqual(metrics['publicElapsedSeconds'], 2.0)
        self.assertEqual(metrics['workerCpuSeconds'], .6)
        self.assertAlmostEqual(metrics['parentCpuSeconds'], .08)
        self.assertEqual(metrics['workerPeakRssBytes'], 2000*1024)
        self.assertEqual(metrics['parentPeakRssBytes'], 1200*1024)
        self.assertNotEqual(metrics['workerPeakRssBytes'], (2000+1200)*1024)

    def test_reused_driver_cannot_claim_aggregate_child_peak_is_this_worker(self):
        for before in (self.usage(.001, 0, 0), self.usage(0, .001, 0), self.usage(0, 0, 1)):
            with self.subTest(before=before), self.assertRaisesRegex(ValueError, 'fresh driver'):
                usage_metrics(self.usage(0, 0, 1), self.usage(.1, .1, 2), before, self.usage(.2, .1, 3), 1, 2)

    def test_missing_real_worker_usage_and_reversed_clocks_reject(self):
        for children, start, finish in ((self.usage(0, 0, 3), 1, 2), (self.usage(.1, .1, 0), 1, 2),
                                        (self.usage(.1, .1, 3), 2, 1)):
            with self.subTest(children=children), self.assertRaises(ValueError):
                usage_metrics(self.usage(0, 0, 1), self.usage(.1, .1, 2), self.usage(0, 0, 0), children, start, finish)


class ArchiveSafetyTests(unittest.TestCase):
    def test_install_archive_rejects_escape_paths_before_extracting(self):
        for name in ('../outside', '/absolute', 'other/bin/python3.14'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); archive = root/'bad.tar.gz'
                with tarfile.open(archive, 'w:gz') as target:
                    entry = tarfile.TarInfo(name); entry.size = 1; target.addfile(entry, io.BytesIO(b'x'))
                with self.assertRaisesRegex(ValueError, 'escapes'):
                    extract_asset(archive, {'digest': 'sha256:'+'1'*64, 'version': '3.14.10'}, root/'cache')
                self.assertFalse((root/'outside').exists())

    def test_install_archive_rejects_escape_link_and_special_device(self):
        for kind in ('link', 'device'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); archive = root/'bad.tar.gz'
                with tarfile.open(archive, 'w:gz') as target:
                    entry = tarfile.TarInfo('python/bin/bad')
                    entry.type = tarfile.SYMTYPE if kind == 'link' else tarfile.CHRTYPE
                    entry.linkname = '../../../outside'; target.addfile(entry)
                with self.assertRaises(ValueError):
                    extract_asset(archive, {'digest': 'sha256:'+'2'*64, 'version': '3.14.10'}, root/'cache')


if __name__ == '__main__': unittest.main()
