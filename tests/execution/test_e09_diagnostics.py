"""Fixed generated monitor behavior; real kernel hooks have separate coverage."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import asyncio
import copy
import itertools

ROOT = Path(__file__).resolve().parents[2]
if not sys.flags.isolated:
    sys.path.insert(0, str(ROOT / "src"))

from pyelk.execution.diagnostics import BasicProgressMonitor
from pyelk import ELK


def _graph(*, disconnected=False, separate=True, direction='RIGHT', loops=False):
    return {'id': 'root', 'business': {'logging': {'executionTime': 33}}, 'executionTime': 17,
            'layoutOptions': {'elk.algorithm': 'layered', 'elk.randomSeed': '7',
                              'elk.direction': direction, 'elk.separateConnectedComponents': separate},
            'children': [{'id': key, 'width': 40, 'height': 30, 'logging': {'executionTime': 19}}
                         for key in ('a', 'b', 'c')],
            'edges': [{'id': 'e', 'sources': ['a'], 'targets': ['a' if loops else 'b'],
                       'logging': {'executionTime': 23}}] + ([] if disconnected else
                       [{'id': 'f', 'sources': ['b'], 'targets': ['c']}])}


def _monitors(value):
    yield value
    for child in value.get('children', []):
        yield from _monitors(child)


class KernelMonitorTests(unittest.TestCase):
    def _execute(self, graph, *, logging=True, timing=False, trace=None):
        from pyelk.execution.context import create_context
        from pyelk.algorithms.layered.pipeline import layout_context
        context = create_context(graph)
        ticks = itertools.count(1000)
        monitor = BasicProgressMonitor(logging, timing, lambda: next(ticks))
        result = layout_context(context, trace=trace, monitor=monitor)
        return result, monitor.collect()

    def test_single_component_actual_phase_tree_and_live_bk_logs(self):
        trace = []
        result, tree = self._execute(_graph(), trace=trace)
        self.assertEqual(tree['name'], 'Recursive Graph Layout')
        layered = tree['children'][0]
        self.assertEqual(layered['name'], 'Layered layout')
        self.assertEqual(len(trace), 19)
        self.assertEqual(len(list(_monitors(tree))), 22)
        self.assertEqual(layered['logs'][0], 'ELK Layered uses the following 19 modules:')
        self.assertEqual(layered['children'][3], {'name': 'Network simplex layering',
                                               'children': [{'name': 'Network simplex'}]})
        bk = layered['children'][13]
        self.assertEqual(bk['logs'], [name+' size is 30' for name in ('RIGHTDOWN','RIGHTUP','LEFTDOWN','LEFTUP')]
                         + [name+' is feasible: true' for name in ('RIGHTDOWN','RIGHTUP','LEFTDOWN','LEFTUP')]
                         + ['Chosen node placement: RIGHTDOWN',
                            'Blocks: {n_root.a=[n_root.a, n_root.b, n_root.c]}',
                            'Classes: {n_root.a=[n_root.a]}', 'Marked edges: []'])
        self.assertEqual(result['business'], {'logging': {'executionTime': 33}})

    def test_actual_separated_and_combined_components_have_distinct_trees(self):
        _, separated = self._execute(_graph(disconnected=True))
        _, combined = self._execute(_graph(disconnected=True, separate=False))
        self.assertEqual([value['name'] for value in separated['children'][0]['children']],
                         ['Component Layout', 'Component Layout'])
        self.assertEqual(len(list(_monitors(separated))), 44)
        self.assertEqual(len(list(_monitors(combined))), 23)
        ns = [value for value in _monitors(combined) if value['name'] == 'Network simplex layering'][0]
        self.assertEqual(ns['children'], [{'name': 'Network simplex'}, {'name': 'Network simplex'}])

    def test_empty_root_and_direction_loop_dispatch_use_real_chain(self):
        _, empty = self._execute({'id': 'empty'})
        self.assertEqual(empty, {'name': 'Recursive Graph Layout'})
        _, loop = self._execute(_graph(direction='LEFT', loops=True))
        self.assertEqual(len(list(_monitors(loop))), 56)  # root/layered plus two actual25-phase component paths
        first = loop['children'][0]['children'][0]['children']
        self.assertEqual(first[0]['name'], 'Graph transformation (TO_INPUT_DIRECTION)')
        self.assertEqual(first[-1]['name'], 'Graph transformation (TO_INTERNAL_LTR)')

    def test_real_timing_boundaries_and_trace_observation_do_not_choose_tree(self):
        plain, tree = self._execute(_graph(), logging=False, timing=True)
        traced, with_trace = self._execute(_graph(), logging=False, timing=True, trace=[])
        self.assertEqual(plain, traced)
        self.assertEqual(tree, with_trace)
        self.assertEqual(len(list(_monitors(tree))), 22)
        for value in _monitors(tree):
            self.assertNotIn('logs', value)
            self.assertGreater(value['executionTime'], 0)
        self.assertEqual(tree['children'][0]['children'][0]['executionTime'], 0.0000010000000000000002)


class PublicDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_four_real_spawned_flag_combinations_preserve_inputs_and_business_fields(self):
        baseline = None
        for logging, timing in itertools.product((False, True), repeat=2):
            with self.subTest(logging=logging, timing=timing):
                graph = _graph()
                graph['logging'] = {'old': 'reserved root value'}
                before = copy.deepcopy(graph)
                arguments = {'logging': logging, 'measureExecutionTime': timing}
                elk = ELK()
                try:
                    result = await elk.layout(graph, arguments)
                    self.assertEqual(elk._controller.snapshot()['pending'], 0)
                finally:
                    elk.terminateWorker()
                self.assertEqual(graph, before)
                self.assertEqual(arguments, {'logging': logging, 'measureExecutionTime': timing})
                self.assertEqual(result['executionTime'], 17)
                self.assertEqual(result['business'], before['business'])
                self.assertEqual([node['logging'] for node in result['children']],
                                 [node['logging'] for node in before['children']])
                self.assertEqual(result['edges'][0]['logging'], before['edges'][0]['logging'])
                self.assertEqual('logging' in result, logging or timing)
                if logging or timing:
                    tree = result.pop('logging')
                    self.assertEqual(len(list(_monitors(tree))), 22)
                    for item in _monitors(tree):
                        self.assertEqual('executionTime' in item, timing)
                        if not logging:
                            self.assertNotIn('logs', item)
                if baseline is None:
                    baseline = result
                self.assertEqual(result, baseline)


class MonitorPrimitiveTests(unittest.TestCase):
    def test_generated_tick_scale_and_binary_multiplication_order(self):
        ticks = iter((1000, 1002))
        monitor = BasicProgressMonitor(measure_execution_time=True, clock_ms=lambda: next(ticks))
        monitor.begin("measured", 1)
        monitor.done()
        self.assertEqual(monitor.collect(), {"name": "measured", "executionTime": 0.0000020000000000000003})

    def test_wall_clock_zero_and_backwards_deltas_are_not_replaced_or_clamped(self):
        for start, end, expected in ((1000, 1000, 0.0), (2002, 2000, -0.0000020000000000000003)):
            with self.subTest(start=start, end=end):
                ticks = iter((start, end))
                monitor = BasicProgressMonitor(measure_execution_time=True, clock_ms=lambda: next(ticks))
                monitor.begin("clock", 1)
                monitor.done()
                self.assertEqual(monitor.collect()["executionTime"], expected)

    def test_default_clock_uses_integer_wall_milliseconds(self):
        with patch("pyelk.execution.diagnostics.time.time_ns", side_effect=(1_000_999_999, 1_002_000_000)):
            monitor = BasicProgressMonitor(measure_execution_time=True)
            monitor.begin("clock", 1)
            monitor.done()
        self.assertEqual(monitor.collect()["executionTime"], 0.0000020000000000000003)

    def test_logging_only_and_disabled_flags_never_read_clock(self):
        def forbidden():
            raise AssertionError("A disabled clock was read")
        for logging in (False, True):
            with self.subTest(logging=logging):
                root = BasicProgressMonitor(logging=logging, clock_ms=forbidden)
                root.begin("root", 1)
                child = root.sub_task(1)
                child.begin("child", 1)
                child.log("actual message")
                child.done()
                root.done()
                expected = {"name": "root", "children": [{"name": "child"}]}
                if logging:
                    expected["children"][0]["logs"] = ["actual message"]
                self.assertEqual(root.collect(), expected)

    def test_four_flag_combinations_share_true_begin_child_structure(self):
        for logging in (False, True):
            for timing in (False, True):
                with self.subTest(logging=logging, timing=timing):
                    ticks = iter((1000, 1001, 1002, 1003))
                    root = BasicProgressMonitor(logging, timing, clock_ms=lambda: next(ticks))
                    root.begin("root", 1)
                    child = root.sub_task(1)
                    child.begin("child", 1)
                    child.log("one real message")
                    child.done()
                    root.done()
                    actual = root.collect()
                    self.assertEqual(actual["name"], "root")
                    self.assertEqual([value["name"] for value in actual["children"]], ["child"])
                    self.assertEqual("logs" in actual["children"][0], logging)
                    self.assertEqual("executionTime" in actual, timing)
                    self.assertEqual("executionTime" in actual["children"][0], timing)

    def test_running_begin_is_not_renamed_or_restarted_and_done_is_idempotent(self):
        ticks = iter((1000, 1007))
        monitor = BasicProgressMonitor(measure_execution_time=True, clock_ms=lambda: next(ticks))
        self.assertTrue(monitor.begin("original", 1))
        self.assertTrue(monitor.is_running())
        self.assertFalse(monitor.begin("other", 99))
        monitor.done()
        monitor.done()
        self.assertFalse(monitor.is_running())
        self.assertEqual(monitor.task_name, "original")
        self.assertEqual(monitor.collect()["executionTime"], 0.000007000000000000001)
        self.assertIsNone(monitor.sub_task(1))
        with self.assertRaisesRegex(RuntimeError, "already done"):
            monitor.begin("late", 1)

    def test_done_before_begin_and_collect_unnamed_match_source_failure_category(self):
        monitor = BasicProgressMonitor()
        with self.assertRaisesRegex(RuntimeError, "not begun"):
            monitor.done()
        with self.assertRaises(TypeError):
            monitor.collect()

    def test_empty_log_lists_are_absent_and_ordered_children_are_independent(self):
        root = BasicProgressMonitor(logging=True)
        root.begin("root", 2)
        first = root.sub_task(1)
        first.begin("first", 1)
        first.log("one")
        first.log("two")
        first.done()
        second = root.sub_task(1)
        second.begin("second", 1)
        second.done()
        root.done()
        expected = {"name": "root", "children": [{"name": "first", "logs": ["one", "two"]}, {"name": "second"}]}
        returned = root.collect()
        self.assertEqual(returned, expected)
        returned["children"][0]["logs"].append("caller mutation")
        returned["children"].reverse()
        self.assertEqual(root.collect(), expected)

    def test_clock_is_per_monitor_tree_and_not_shared_globally(self):
        one_ticks, two_ticks = iter((10, 12)), iter((20, 27))
        one = BasicProgressMonitor(measure_execution_time=True, clock_ms=lambda: next(one_ticks))
        two = BasicProgressMonitor(measure_execution_time=True, clock_ms=lambda: next(two_ticks))
        one.begin("one", 1)
        two.begin("two", 1)
        two.done()
        one.done()
        self.assertEqual(one.collect()["executionTime"], 0.0000020000000000000003)
        self.assertEqual(two.collect()["executionTime"], 0.000007000000000000001)

    def test_fractional_and_boolean_clock_ticks_are_not_integer_wall_ticks(self):
        for value in (True, 1.25, float("nan")):
            with self.subTest(value=value):
                monitor = BasicProgressMonitor(measure_execution_time=True, clock_ms=lambda: value)
                with self.assertRaises(TypeError):
                    monitor.begin("clock", 1)


if __name__ == "__main__":
    unittest.main()
