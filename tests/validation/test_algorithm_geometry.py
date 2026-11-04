"""Saved-data quality predicates and one-coordinate fault controls, no layouts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from algorithm_geometry import assess, audit_archive, key, topology

ARCHIVE = ROOT/'references/full-native-closure/options.zip'


def saved(identifier):
    with zipfile.ZipFile(ARCHIVE) as archive:
        raw = archive.read('tests/fixtures/suites/full-option-effects-nonlayered/requests/' + identifier + '.json')
        observation = json.loads(archive.read('test-runs/full-native-closure/B/nonlayered-effects-reference-01/' + identifier + '.json'))
    assert observation['requestSha256'] == hashlib.sha256(raw).hexdigest()
    return json.loads(raw), observation


class AlgorithmGeometryTests(unittest.TestCase):
    def break_pair(self, identifier, predicate, components_only=False):
        request, observation = saved(identifier)
        self.assertEqual(assess(request, observation)['status'], 'PASS')
        mutated = copy.deepcopy(observation)
        nodes = mutated['result']['children']
        _, _, _, components = topology(request['graph'])
        memberships = {node: index for index, group in enumerate(components) for node in group}
        for index, first in enumerate(nodes):
            for second in nodes[index+1:]:
                if components_only and memberships[key(first['id'])] == memberships[key(second['id'])]:
                    continue
                if min(first['y']+first['height'], second['y']+second['height']) > max(first['y'], second['y']) + 1e-6:
                    second['x'] = first['x']
                    result = assess(request, mutated)
                    self.assertEqual(result['status'], 'FAIL')
                    self.assertTrue(any(row['predicate'] == predicate for row in result['failures']))
                    return
        self.fail('Saved fixture has no vertically overlapping eligible pair')

    def test_saved_source_and_native_same_predicates(self):
        report = audit_archive(ARCHIVE)
        self.assertTrue(report['passed'])
        self.assertEqual(report['counts'], {role: {'PASS': 10, 'FAIL': 0, 'NOT_ASSESSED': 4}
                                           for role in ('source', 'native')})
        self.assertEqual((report['sourceExecutions'], report['nativeExecutions']), (0, 0))

    def test_mrtree_one_y_breaks_parent_child_depth_band(self):
        request, observation = saved('mrtree-tree-base')
        self.assertEqual(assess(request, observation)['status'], 'PASS')
        observation['result']['children'][1]['y'] = observation['result']['children'][0]['y']
        result = assess(request, observation)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['failures'][0]['predicate'], 'directional-parent-child-depth-bands')

    def test_radial_one_x_breaks_same_depth_radius(self):
        request, observation = saved('radial-base')
        self.assertEqual(assess(request, observation)['status'], 'PASS')
        observation['result']['children'][1]['x'] += 3
        result = assess(request, observation)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any(row.get('reason') == 'Unequal center radii' for row in result['failures']))

    def test_box_one_x_breaks_packing(self):
        self.break_pair('box-simple-base', 'node-rectangle-nonoverlap')

    def test_rectpacking_one_x_breaks_packing(self):
        self.break_pair('rectpacking-base', 'node-rectangle-nonoverlap')

    def test_spore_overlap_one_x_breaks_separation(self):
        self.break_pair('spore-overlap-base', 'node-rectangle-nonoverlap')

    def test_disco_only_distinct_components_must_be_separate(self):
        self.break_pair('disco-base', 'different-component-node-rectangle-separation', True)
        request = {'constructor': {}, 'graph': {
            'id': 'r', 'layoutOptions': {'algorithm': 'disco'},
            'children': [{'id': str(i), 'width': 10, 'height': 10} for i in range(3)],
            'edges': [{'id': 'e', 'sources': ['0'], 'targets': ['1']}]}}
        result = copy.deepcopy(request['graph'])
        for index, node in enumerate(result['children']):
            node.update(x=100 if index == 2 else 0, y=0)
        self.assertEqual(assess(request, {'outcome': 'returned', 'result': result})['status'], 'PASS')

    def test_single_extent_fault_breaks_containment(self):
        request, observation = saved('rectpacking-base')
        observation['result']['children'][0]['width'] = observation['result']['width'] + 1
        result = assess(request, observation)
        self.assertTrue(any(row['predicate'] == 'node-rectangles-contained-in-container'
                            for row in result['failures']))

    def test_nonapplicable_options_and_dag_are_not_passes(self):
        for identifier in ('mrtree-compaction', 'mrtree-cycle-dfs', 'radial-compactor', 'spore-overlap-scanline'):
            request, observation = saved(identifier)
            result = assess(request, observation)
            self.assertEqual(result['status'], 'NOT_ASSESSED')
            self.assertFalse(result['checks'])
        request, observation = saved('radial-base')
        request['graph']['layoutOptions']['org.eclipse.elk.radial.rotate'] = True
        self.assertEqual(assess(request, observation)['status'], 'NOT_ASSESSED')


if __name__ == '__main__':
    unittest.main()
