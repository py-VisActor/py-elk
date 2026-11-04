"""Independent constraints over saved real geometry, with single-fact mutants."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from advanced_geometry import validate


class AdvancedGeometryTests(unittest.TestCase):
    def sample(self, name):
        saved = ROOT / 'tests/fixtures/suites/full-option-effects/geometry-saved'
        folder = saved / name
        manifest = json.loads((saved / 'manifest.json').read_bytes())
        entry = next(row for row in manifest['cases'] if row['id'] == name)
        for filename, binding in entry['files'].items():
            self.assertEqual(hashlib.sha256((folder / filename).read_bytes()).hexdigest(), binding['sha256'])
        request = json.loads((folder / 'request.json').read_bytes())
        original = json.loads((folder / 'reference.json').read_bytes())['result']
        native = json.loads((folder / 'candidate.json').read_bytes())['result']
        for result in (original, native):
            self.assertTrue(validate(request, result)['assessedPredicatesPassed'])
        return request, original

    def codes(self, request, graph):
        return {e['code'] for e in validate(request, graph)['errors']}

    def test_real_port_side_mutation_is_rejected(self):
        request, graph = self.sample('ports-fixed-side')
        graph['children'][0]['ports'][0]['y'] += 1
        self.assertIn('fixed_port_side_or_offset', self.codes(request, graph))

    def test_real_anchor_attachment_mutation_is_rejected(self):
        request, graph = self.sample('ports-fixed-pos')
        graph['edges'][0]['sections'][0]['startPoint']['x'] += 1
        self.assertIn('port_anchor_attachment', self.codes(request, graph))

    def test_missing_anchor_on_fixed_cardinal_leaf_ports(self):
        request, graph = self.sample('p4-default-leaf-anchors')
        report = validate(request, graph)
        self.assertIn('default_fixed_leaf_port_anchor_attachment', {row['predicate'] for row in report['checked']})
        graph['edges'][0]['sections'][0]['startPoint']['y'] += 1
        self.assertIn('port_anchor_attachment', self.codes(request, graph))

    def test_given_label_size_mutation_is_rejected(self):
        request, graph = self.sample('end-labels-head-tail')
        edge = next(e for e in graph['edges'] if e.get('labels'))
        edge['labels'][0]['width'] += 1
        self.assertIn('given_label_size_changed', self.codes(request, graph))

    def test_explicit_inside_label_outside_owner_is_rejected(self):
        request, graph = self.sample('direction-right')
        node = next(n for n in graph['children'] if n.get('labels'))
        node['labels'][0]['x'] = node['width'] + 1
        self.assertIn('inside_node_label_outside_owner', self.codes(request, graph))

    def test_nested_frame_translation_is_rejected(self):
        request, graph = self.sample('compound-cross-hierarchy')
        parent = graph['children'][0]
        child = parent['children'][0]
        child['x'] += parent['x']
        child['y'] += parent['y']
        self.assertIn('node_endpoint_off_border', self.codes(request, graph))

    def test_parent_containment_mutation_is_rejected(self):
        request, graph = self.sample('compound-cross-hierarchy')
        parent = graph['children'][0]
        parent['children'][0]['x'] = parent['width'] + 1
        self.assertIn('child_outside_parent', self.codes(request, graph))

    def test_four_real_coordinate_modes_and_wrong_root_translation(self):
        folder = ROOT / 'tests/fixtures/suites/full-option-effects/geometry-frames'
        manifest = json.loads((folder / 'manifest.json').read_bytes())
        self.assertEqual(len(manifest['cases']), 4)
        for row in manifest['cases']:
            case = folder / row['id']
            for name, binding in row['files'].items():
                self.assertEqual(hashlib.sha256((case / name).read_bytes()).hexdigest(), binding['sha256'])
            request = json.loads((case / 'request.json').read_bytes())
            graph = json.loads((case / 'candidate-record.json').read_bytes())['actual']
            report = validate(request, graph)
            self.assertTrue(report['assessedPredicatesPassed'], report['errors'])
            self.assertIn('fixed_input_position_in_declared_export_frame', {p['predicate'] for p in report['checked']})
            graph['children'][0]['children'][0]['x'] += 1
            self.assertIn('fixed_shape_coordinate_frame', self.codes(request, graph))

    def test_section_chain_single_disconnection_is_rejected(self):
        request, graph = self.sample('ports-fixed-side')
        edge = graph['edges'][0]
        first = copy.deepcopy(edge['sections'][0])
        second = copy.deepcopy(first)
        joint = first['bendPoints'][0]
        first['endPoint'] = copy.deepcopy(joint)
        first['bendPoints'] = []
        first.pop('outgoingShape', None)
        first['outgoingSections'] = [str(first['id']) + '_next']
        second['id'] = first['outgoingSections'][0]
        second['startPoint'] = copy.deepcopy(joint)
        second['bendPoints'] = second['bendPoints'][1:]
        second.pop('incomingShape', None)
        second['incomingSections'] = [first['id']]
        edge['sections'] = [first, second]
        self.assertTrue(validate(request, graph)['assessedPredicatesPassed'])
        second['startPoint']['x'] += 1
        self.assertIn('section_chain_disconnected', self.codes(request, graph))

    def test_not_assessed_does_not_become_a_full_pass(self):
        request, graph = self.sample('ports-fixed-side')
        report = validate(request, graph)
        self.assertTrue(report['assessedPredicatesPassed'])
        self.assertTrue(report['not_assessed'])
        self.assertEqual(report['status'], 'PARTIAL')
        self.assertFalse(report['passed'])


if __name__ == '__main__':
    unittest.main()
