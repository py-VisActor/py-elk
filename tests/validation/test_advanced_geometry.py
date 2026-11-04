"""Independent constraints over saved real geometry, with single-fact mutants."""
import copy
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from advanced_geometry import validate, validate_label_stack


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

    def effect_sample(self, name, report_name='option-effects-corrected-observables.json'):
        folder = ROOT / 'references/full-native-closure'
        manifest = json.loads((folder / 'options.manifest.json').read_bytes())
        archive_path = folder / 'options.zip'
        self.assertEqual(hashlib.sha256(archive_path.read_bytes()).hexdigest(), manifest['archive']['sha256'])
        entries = {row['path']: row for row in manifest['files']}
        with zipfile.ZipFile(archive_path) as archive:
            def raw(path):
                value = archive.read(path) if entries[path]['storage'] == 'archive' else (ROOT / path).read_bytes()
                self.assertEqual(hashlib.sha256(value).hexdigest(), entries[path]['sha256'])
                return json.loads(value)
            report = raw('test-runs/full-native-closure/A/' + report_name)
            row = next(row for row in report['rows'] if row['id'] == name)
            def bound(key):
                item = row[key]
                path = PureWindowsPath(item['path']).relative_to(PureWindowsPath(manifest['originalExecutionRoot'])).as_posix()
                self.assertEqual(item['sha256'], entries[path]['sha256'])
                return raw(path)
            request = bound('request')
            original, native = bound('reference')['result'], bound('native')['result']
        for result in (original, native):
            checked = validate(request, result)
            self.assertTrue(checked['assessedPredicatesPassed'], checked['errors'])
        return request, original

    def contract_sample(self, name):
        folder = ROOT / 'tests/fixtures/suites/full-option-effects/geometry-contracts'
        manifest = json.loads((folder / 'manifest.json').read_bytes())
        row = next(row for row in manifest['cases'] if row['id'] == name)
        case = folder / name
        for filename, item in row['files'].items():
            self.assertEqual(hashlib.sha256((case / filename).read_bytes()).hexdigest(), item['sha256'])
        request = json.loads((case / 'request.json').read_bytes())
        original, native = [json.loads((case / key).read_bytes())['result'] for key in ('reference.json', 'candidate.json')]
        for result in (original, native):
            report = validate(request, result)
            self.assertTrue(report['assessedPredicatesPassed'], report['errors'])
        return request, original

    def shift_source_port(self, graph, port_id, axis, delta):
        node = next(n for n in graph['children'] if any(p['id'] == port_id for p in n.get('ports', [])))
        port = next(p for p in node['ports'] if p['id'] == port_id)
        port[axis] += delta
        for edge in graph['edges']:
            if edge.get('sources') != [port_id]:
                continue
            section = edge['sections'][0]
            original = section['startPoint'][axis]
            # Move the attached endpoint and its axis-aligned prefix together:
            # a new tangent/order predicate must reject this semantic change,
            # even though the old port-anchor attachment remains valid.
            for point in [section['startPoint'], *section.get('bendPoints', [])]:
                if point[axis] != original:
                    break
                point[axis] += delta

    def test_fixed_position_tangent_with_attached_endpoint_mutant(self):
        request, graph = self.effect_sample('port-position-base')
        self.assertIn('fixed_port_tangential_position', {p['predicate'] for p in validate(request, graph)['checked']})
        self.shift_source_port(graph, 'p0_0', 'x', 1)
        codes = self.codes(request, graph)
        self.assertIn('fixed_port_tangent', codes)
        self.assertNotIn('port_anchor_attachment', codes)

    def test_ratio_uses_rect_origin_and_resized_owner_not_anchor(self):
        request, graph = self.effect_sample('port-ratio')
        given, placed = request['graph']['children'][0], graph['children'][0]
        self.assertEqual((given['width'], given['height']), (120, 90))
        self.assertEqual((placed['width'], placed['height']), (180, 140))
        self.assertIn('fixed_port_tangential_ratio', {p['predicate'] for p in validate(request, graph)['checked']})
        port = next(p for p in placed['ports'] if p['id'] == 'p0_0')
        supplied = next(p for p in given['ports'] if p['id'] == 'p0_0')
        self.shift_source_port(graph, 'p0_0', 'x', supplied['x'] - port['x'])
        codes = self.codes(request, graph)
        self.assertIn('fixed_port_ratio', codes)
        self.assertNotIn('port_anchor_attachment', codes)

    def test_same_side_order_with_connected_ports_swapped(self):
        for name in ('port-order-base', 'port-index'):
            request, graph = self.effect_sample(name)
            predicates = [p for p in validate(request, graph)['checked'] if p['predicate'] == 'same_side_fixed_order_clockwise_geometry']
            self.assertEqual(len(predicates), 4)
            if name == 'port-order-base':
                self.shift_source_port(graph, 'p0_0', 'x', 14)
                self.shift_source_port(graph, 'p0_1', 'x', -14)
                codes = self.codes(request, graph)
                self.assertIn('fixed_port_clockwise_order', codes)
                self.assertNotIn('port_anchor_attachment', codes)

    def test_explicit_minimum_bound_catches_smaller_box(self):
        request, graph = self.sample('direction-right')
        self.assertIn('explicit_leaf_minimum_size_bound', {p['predicate'] for p in validate(request, graph)['checked']})
        node = next(n for n in graph['children'] if n['id'] == 'c')
        node['width'] = 44
        self.assertIn('explicit_minimum_size_violated', self.codes(request, graph))

    def test_conservative_spline_net_control_deletion_is_rejected(self):
        request, graph = self.effect_sample('spline-conservative', 'option-effects-third-local-port-corrected.json')
        predicates = {p['predicate'] for p in validate(request, graph)['checked']}
        self.assertIn('complete_piecewise_cubic_control_net', predicates)
        self.assertIn('spline_curve_endpoints_attached_in_global_frame', predicates)
        section = next(e['sections'][0] for e in graph['edges'] if e['sections'][0].get('bendPoints'))
        section['bendPoints'].pop(0)
        self.assertIn('incomplete_spline_cubic_control_net', self.codes(request, graph))

    def test_spline_curve_endpoint_must_stay_attached(self):
        request, graph = self.effect_sample('spline-conservative', 'option-effects-third-local-port-corrected.json')
        graph['edges'][0]['sections'][0]['endPoint']['x'] += 1
        self.assertIn('port_anchor_attachment', self.codes(request, graph))

    def test_real_missing_label_dimensions_default_to_zero(self):
        request, graph = self.contract_sample('missing-label-sizes')
        report = validate(request, graph)
        self.assertEqual(sum(row['predicate'] == 'missing_label_dimension_defaults_to_zero' for row in report['checked']), 10)
        # Nonempty text is not a font-measurement request.
        graph['children'][0]['labels'][0]['width'] = 1
        self.assertIn('missing_label_dimension_not_zero', self.codes(request, graph))

    def test_real_two_section_connection_and_disconnection(self):
        request, graph = self.contract_sample('fixed-two-sections')
        self.assertEqual(len(graph['edges'][0]['sections']), 2)
        self.assertIn('section_chain_connectivity', {row['predicate'] for row in validate(request, graph)['checked']})
        graph['edges'][0]['sections'][1]['startPoint']['x'] += 1
        self.assertIn('section_chain_disconnected', self.codes(request, graph))

    def test_real_section_reference_must_be_reciprocal(self):
        request, graph = self.contract_sample('fixed-two-sections')
        graph['edges'][0]['sections'][1]['incomingSections'] = []
        self.assertIn('section_reference_not_reciprocal', self.codes(request, graph))

    def test_selected_label_stack_gap_independent_of_source_coordinates(self):
        folder = ROOT / 'tests/fixtures/suites/full-option-effects/geometry-contracts'
        entry = next(row for row in json.loads((folder / 'manifest.json').read_bytes())['cases'] if row['id'] == 'label-cell-stacks')
        case = folder / entry['id']
        for name, item in entry['files'].items():
            self.assertEqual(hashlib.sha256((case / name).read_bytes()).hexdigest(), item['sha256'])
        request = json.loads((case / 'request.json').read_bytes())
        reference = json.loads((case / 'reference.json').read_bytes())
        native = json.loads((case / 'candidate.json').read_bytes())
        for item in request['cases']:
            cell = item['cell']
            if cell['kind'] != 'label':
                continue
            # The actual selected LabelCell constructor contract names the
            # stack mode. The predicate only uses axis/gap and rectangle gaps.
            axis = 1 if cell['horizontalMode'] else 0
            source_boxes = next(row['value']['labels'] for row in reference['results'] if row['id'] == item['id'])
            native_boxes = next(row['actual']['labels'] for row in native['rows'] if row['id'] == item['id'])
            for boxes in (source_boxes, native_boxes):
                self.assertTrue(validate_label_stack(boxes, axis, cell['gap'])['passed'])
                bad = copy.deepcopy(boxes)
                bad[1][axis] = bad[0][axis] + bad[0][axis + 2] + cell['gap'] - 1
                self.assertIn('label_stack_gap', {row['code'] for row in validate_label_stack(bad, axis, cell['gap'])['errors']})
        self.assertEqual(validate_label_stack([], 1, 3)['status'], 'NOT_ASSESSED')

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
