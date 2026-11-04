"""Collector protocol guards only; the real platform cells are separate evidence."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT/'tools/platform/capture_e10.py'
spec = importlib.util.spec_from_file_location('e10_collector_protocol',COLLECTOR)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class PlatformCaptureProtocolTests(unittest.TestCase):
    def invoke(self, directory, *, isolated=True, bad_path=False, override=False, existing=False, cwd=None):
        output = Path(directory)/'observation.json'
        if existing: output.write_bytes(b'original evidence bytes\n')
        env = {key:value for key,value in os.environ.items() if key.upper() not in collector.OVERRIDES}
        env['PATH'] = 'deliberate-nonempty-path' if bad_path else ''
        if override: env['PYTHONPATH'] = 'deliberate-override'
        argv = [sys.executable,*(['-I'] if isolated else []),str(COLLECTOR),'--wheel','missing.whl',
                '--suite',str(ROOT/'tests/fixtures/suites/E10'),'--out',str(output)]
        process = subprocess.run(argv,cwd=cwd or directory,env=env,capture_output=True,timeout=15)
        return process,output

    def test_isolation_and_clean_environment_are_required_before_package_loading(self):
        for configuration in ({'isolated':False},{'bad_path':True},{'override':True}):
            with self.subTest(configuration=configuration), tempfile.TemporaryDirectory() as directory:
                process,output = self.invoke(directory,**configuration)
                self.assertNotEqual(process.returncode,0)
                self.assertIn(b'Use Python -I, empty PATH and absent override variables',process.stderr)
                self.assertFalse(output.exists())
        with tempfile.TemporaryDirectory() as directory:
            process,output = self.invoke(directory,cwd=ROOT)
            self.assertNotEqual(process.returncode,0)
            self.assertIn(b'working directory must be outside the repository',process.stderr)
            self.assertFalse(output.exists())

    def test_existing_output_is_rejected_and_its_actual_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            process,output = self.invoke(directory,existing=True)
            self.assertNotEqual(process.returncode,0)
            self.assertIn(b'FileExistsError',process.stderr)
            self.assertEqual(output.read_bytes(),b'original evidence bytes\n')

    def test_pid_probe_observes_a_real_owned_child_before_and_after_termination(self):
        process = subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'],
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            before = collector.pid_probe(process.pid)
            self.assertEqual(before['pid'],process.pid)
            self.assertIs(before['alive'],True)
        finally:
            process.terminate();process.communicate(timeout=10)
        after = collector.pid_probe(process.pid)
        self.assertEqual(after['pid'],before['pid'])
        self.assertIs(after['alive'],False)


if __name__ == '__main__':
    unittest.main()
