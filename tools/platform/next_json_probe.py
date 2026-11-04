"""Targeted private JSON host controls; no installed/public algorithm claim."""
from pathlib import Path
import argparse
import copy
import json
import sys


def probe(workspace, case):
    sys.path.insert(0, str(Path(workspace)/'src'))
    import pyelk
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk._errors import ModelValidationError, OptionValidationError
    graph = {'id': 'root', 'x': 17, 'y': 29, 'business': {'keep': True}, 'children': [
        {'id': 'group', 'x': 20, 'y': 30, 'children': [{'id': 'a', 'x': 5, 'y': 7}],
         'edges': [{'id': 'e', 'sources': ['a'], 'targets': ['b'], 'business': 'edge',
                    'sections': [{'id': 'old', 'business': 'section',
                                  'startPoint': {'x': 1, 'y': 2}, 'endPoint': {'x': 3, 'y': 4},
                                  'bendPoints': []}], 'labels': [{'text': 'label', 'x': 2, 'y': 3}]}]},
        {'id': 'b', 'x': 70, 'y': 80}]}
    if case in ('coordinate-ownership', 'coordinate-ordinals'):
        graph['layoutOptions'] = ({'json.shapeCoords': 'ROOT', 'json.edgeCoords': 'PARENT'}
                                  if case == 'coordinate-ownership' else
                                  {'json.shapeCoords': 2.0, 'json.edgeCoords': '+2'})
        before = copy.deepcopy(graph); state = JsonLayoutSession(graph)
        edge = state.edges[0]; group = state.graph['children'][0]
        assert state.current_containers[id(edge)] is state.graph
        assert state.contained_edges(group) == ()
        assert state.graph['edges'][0] is edge
        result = state.export(); output = result['children'][0]['edges'][0]
        assert result['x'] == 17 and result['y'] == 29
        assert result['children'][0]['x'] == 37 and result['children'][0]['y'] == 59
        assert result['children'][0]['children'][0]['x'] == 42
        assert output['sections'][0]['startPoint'] == {'x': -19, 'y': -28}
        assert output['labels'][0]['x'] == -18 and output['labels'][0]['y'] == -27
        assert 'container' not in output and 'edges' not in result
        assert output['sections'][0]['incomingShape'] == 'a'
        assert output['sections'][0]['outgoingShape'] == 'b'
        assert output['business'] == 'edge' and result['business'] == {'keep': True}
        assert graph == before
        assert state.export() == result, 'Repeated export changed internal coordinates'
        if case == 'coordinate-ordinals':
            for value in (False, 2**31, 'root', '-1'):
                wrong = copy.deepcopy(graph); wrong['layoutOptions']['json.shapeCoords'] = value
                try: JsonLayoutSession(wrong).export()
                except OptionValidationError: pass
                else: raise AssertionError('Bad coordinate mode accepted')
    elif case == 'detached-edge':
        root = Path(__file__).resolve().parents[2]
        request = json.loads((root/'tests/fixtures/suites/next-native/json-detached/root-selfedge.json').read_bytes())
        graph = request['graph']; before = copy.deepcopy(graph)
        state = JsonLayoutSession(graph)
        assert state.current_containers[id(state.edges[0])] is None
        result = state.export()
        assert result['edges'] == before['edges'], 'Detached original edge/label was transferred'
        assert result['x'] == 17 and result['y'] == 29
        assert graph == before
    elif case == 'conditional-section-fields':
        group = graph['children'][0]; edge = group['edges'][0]
        edge['junctionPoints'] = [{'x': 100, 'y': 200}]
        edge['sections'][0]['bendPoints'] = [{'x': 10, 'y': 11}]
        edge['sections'][0]['outgoingSections'] = ['other']
        edge['sections'].append({'id': 'other', 'startPoint': {'x': 3, 'y': 4},
                                 'endPoint': {'x': 6, 'y': 8}, 'incomingShape': 'a'})
        before = copy.deepcopy(graph); state = JsonLayoutSession(graph)
        first, second = state.edges[0]['sections']
        assert second['incomingSections'] == ['old'], 'Source inverse relation missing'
        assert 'outgoingShape' not in second, 'One-sided shape link was synthesized'
        first['bendPoints'] = []; first['outgoingSections'] = []
        result = state.export(); output = result['children'][0]['edges'][0]
        assert output['container'] == 'root'
        assert output['junctionPoints'] == edge['junctionPoints']
        assert output['sections'][0]['bendPoints'] == [{'x': 10, 'y': 11}]
        assert output['sections'][0]['outgoingSections'] == ['other']
        assert output['sections'][1]['incomingSections'] == ['old']
        assert output['sections'][0]['business'] == 'section'
        state.edges[0]['sections'] = []
        assert state.export()['children'][0]['edges'][0]['sections'] == output['sections']
        assert graph == before
    elif case == 'primitive-and-state':
        graph = {'id': 0, 'children': [{'id': 'a', 'ports': [{'id': 'p'}]}, {'id': 1}],
                 'edges': [{'id': 2, 'source': 'a', 'sourcePort': 'missing', 'target': 1,
                            'sourcePoint': {'x': 2, 'y': 3}, 'bendPoints': []}]}
        before = copy.deepcopy(graph); state = JsonLayoutSession(graph)
        edge = state.edges[0]
        assert state.endpoint(edge) is state.graph['children'][0]
        assert state.endpoint(edge, True) is state.graph['children'][1]
        port = state.graph['children'][0]['ports'][0]
        state.computed_options[id(port)] = {'port.side': 'EAST'}
        state.cleared_constraints.add(id(state.graph['children'][0]))
        assert state.option(port, 'port.side') == 'EAST'
        assert state.option(state.graph['children'][0], 'nodeSize.constraints', ['MINIMUM_SIZE']) == []
        result = state.export(); output = result['edges'][0]
        assert output['container'] == '0' and output['target'] == 1
        assert output['sections'][0] == {'id': '2_s0', 'startPoint': {'x': 2, 'y': 3},
                                         'endPoint': {'x': 0, 'y': 0}}
        assert 'sources' not in output and 'targets' not in output
        assert 'incomingShape' not in output['sections'][0]
        assert graph == before
    elif case == 'invalid-imports':
        mutations = []
        value = copy.deepcopy(graph); value['children'][1]['id'] = 'a'; mutations.append(value)
        value = copy.deepcopy(graph); value['children'][0]['edges'][0]['sections'][0].pop('id'); mutations.append(value)
        value = copy.deepcopy(graph); value['children'][0]['edges'][0]['sections'][0].pop('endPoint'); mutations.append(value)
        value = copy.deepcopy(graph); value['children'][0]['edges'][0]['sections'][0]['outgoingSections'] = ['missing']; mutations.append(value)
        value = copy.deepcopy(graph); value['children'][1]['x'] = True; mutations.append(value)
        value = copy.deepcopy(graph); value['children'][0]['edges'][0]['sources'] = ['missing']; mutations.append(value)
        for value in mutations:
            before = copy.deepcopy(value)
            try: JsonLayoutSession(value)
            except ModelValidationError: pass
            else: raise AssertionError('Invalid import accepted')
            assert value == before, 'Rejected import changed caller data'
    else:
        raise ValueError('Unknown JSON transfer control')
    return {'case': case, 'passed': True, 'privateSource': True,
            'modulePath': str(Path(pyelk.__file__).resolve()),
            'publicAPIIntegrated': False, 'fullValidation': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.workspace, args.case)))
