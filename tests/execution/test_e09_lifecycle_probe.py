"""Real host probe followed by independent single-fact receipt mutations."""
import asyncio
import copy
import importlib.metadata
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if not sys.flags.isolated:
    sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'tools/reference'))
import e09_host_lifecycle_probe as probe


class LifecycleProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='pyelk-e09-lifecycle-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.observation = asyncio.run(probe.capture_observation(Path(cls.directory.name), installed=bool(sys.flags.isolated)))

    def negative(self, mutate):
        self.assertTrue(probe.validate_lifecycle_observation(self.observation)['passed'])
        value = copy.deepcopy(self.observation)
        mutate(value)
        with self.assertRaises((ValueError, TypeError, KeyError)):
            probe.validate_lifecycle_observation(value)
        self.assertTrue(probe.validate_lifecycle_observation(self.observation)['passed'])

    def test_actual_host_capture_includes_true_running_deadline_and_slot_recovery(self):
        result = probe.validate_lifecycle_observation(self.observation)
        self.assertTrue(result['passed'])
        running = self.observation['runningTimeout']
        attempt = running['attempts'][running['qualifiedAttempt']]
        self.assertGreaterEqual(len(attempt['phaseEvents']), 2)
        self.assertTrue(attempt['pidBefore']['alive'])
        self.assertFalse(attempt['pidAfter']['alive'])
        self.assertEqual(running['afterRecovery']['last_submitted_id'], 2)
        self.assertEqual(self.observation['queuedTimeout']['afterQueuedTimeout']['pending'], 1)

    def test_registry_groups_cannot_jointly_advertise_an_invented_capability(self):
        def mutate(value):
            registry = value['registry']
            registry['default']['algorithms'][0]['knownOptions'].append('invented.option')
            for row in registry['aliases']:
                row['queries'] = copy.deepcopy(registry['default'])
        self.negative(mutate)

    def test_actual_cpu_deadline_requires_typed_time_job_and_phase_identity(self):
        def attempt(value):
            running = value['runningTimeout']
            return running['attempts'][running['qualifiedAttempt']]
        for mutation in (lambda v: attempt(v).__setitem__('timeout', True),
                         lambda v: attempt(v)['phaseEvents'][0].__setitem__('observedAt', True),
                         lambda v: attempt(v)['phaseEvents'][0]['snapshot']['jobs'][-1].__setitem__('job_id', True),
                         lambda v: attempt(v)['phaseEvents'][0]['snapshot']['jobs'][-1].__setitem__('pid', 123456789),
                         lambda v: attempt(v)['phaseEvents'][0].__setitem__('cpuSeconds', True),
                         lambda v: attempt(v)['phaseEvents'][-1].__setitem__('cpuSeconds', attempt(v)['phaseEvents'][0]['cpuSeconds'])):
            with self.subTest(mutation=repr(mutation)):
                self.negative(mutation)

    def test_os_pid_flags_cannot_contradict_real_lookup_fields(self):
        def mutate(value):
            running = value['runningTimeout']; attempt = running['attempts'][running['qualifiedAttempt']]
            record = attempt['pidBefore']
            record.clear()
            record.update(method='OpenProcess/GetExitCodeProcess', pid=attempt['after']['jobs'][-1]['pid'], opened=False, error=87, alive=True)
        self.negative(mutate)

    def test_faults_require_actual_bad_messages_error_classification_and_real_recovery(self):
        for mutation in (lambda v: v['faults']['wrongJob']['sentMessages'][0].__setitem__('job_id', 1),
                         lambda v: v['faults']['internalImport']['error'].__setitem__('type', 'UnsupportedFeatureError'),
                         lambda v: v['faults']['spawnFailure']['after']['jobs'][-1].__setitem__('reaped', False),
                         lambda v: v['faults']['badBody']['recoveryResult']['children'][1].__setitem__('x', -1000)):
            with self.subTest(mutation=repr(mutation)):
                self.negative(mutation)

    def test_close_and_queued_deadline_require_original_published_trace_and_resources(self):
        for mutation in (lambda v: v['registry']['closedTrace'].__setitem__('before', []),
                         lambda v: v['registry']['closedTrace'].__setitem__('after', [{'fake': True}]),
                         lambda v: v['crossThreadClose']['threadCall'].__setitem__('threadId', v['crossThreadClose']['mainThreadId']),
                         lambda v: v['queuedTimeout']['afterQueuedTimeout']['jobs'][-1].__setitem__('pid', 123456789)):
            with self.subTest(mutation=repr(mutation)):
                self.negative(mutation)


if __name__ == '__main__':
    unittest.main()
