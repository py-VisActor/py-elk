"""Exercise changed private NodeContext property parsing in an isolated process."""
from pathlib import Path
import argparse
import asyncio
import copy
import json
import sys


def probe(workspace, case):
    sys.path.insert(0, str(Path(workspace)/'src'))
    import pyelk
    from pyelk.execution.context import create_context
    from pyelk.options.element import parse_mapping, resolve_raw_element_options
    from pyelk._errors import OptionValidationError
    key = 'org.eclipse.elk.'
    graph = {'id': 'root', 'children': [{'id': 'a', 'ports': [{'id': 'p'}]}, {'id': 'b'}]}
    before = copy.deepcopy(graph)
    if case == 'defaults-and-targets':
        context = create_context(graph)
        child = context.working_graph.nodes[1]
        assert context.element_options(child).values[key+'portAlignment.default'] == 'DISTRIBUTED'
        effective = context.element_options(child, algorithm='layered')
        assert effective.values[key+'portAlignment.default'] == 'JUSTIFIED'
        assert effective.origins[key+'portAlignment.default'] == 'algorithm-default'
        context = create_context(graph, constructor={'defaultLayoutOptions': {
            'portAlignment.default': 'CENTER', 'port.side': 'SOUTH', 'nodeSize.options': '[]',
            'nodeLabels.placement': 'V_BOTTOM', 'spacing.labelPortHorizontal': 10000001}})
        child = context.working_graph.nodes[1]; port = child.ports[0]
        result = context.element_options(child, algorithm='layered')
        assert result.values[key+'portAlignment.default'] == 'CENTER'
        assert result.origins[key+'portAlignment.default'] == 'constructor'
        assert result.values[key+'nodeSize.options'] == frozenset()
        assert result.values[key+'spacing.labelPortHorizontal'] == 10000001
        assert key+'port.side' not in result.values
        assert context.element_options(port).values[key+'port.side'] == 'SOUTH'
        label = resolve_raw_element_options({'text': 'label'}, 'label', context)
        assert label.values[key+'nodeLabels.placement'] == frozenset({'V_BOTTOM'})
        assert key+'portAlignment.default' not in label.values
    elif case == 'presence-and-individual':
        graph['layoutOptions'] = {'spacing.individual': 'spacing.labelNode:6;,;spacing.labelLabel:4'}
        graph['individualSpacings'] = {'spacing.labelNode': 2, 'spacing.labelPortHorizontal': '3d'}
        graph['children'][0]['layoutOptions'] = {'nodeSize.constraints': '', 'portAlignment.east': 3.0,
            'portLabels.treatAsGroup': 'FALSE', 'nodeLabels.placement': 'H_CENTER, V_TOP, INSIDE'}
        before = copy.deepcopy(graph)
        context = create_context(graph, constructor={'defaultLayoutOptions': {
            'nodeSize.constraints': '[3,PORTS]', 'nodeSize.minimum': [8,9],
            'spacing.individual': 'spacing.labelPortVertical:99'}})
        root, first, second = context.working_graph.nodes
        result = context.element_options(root)
        individual = result.values[key+'spacing.individual']
        assert individual == {key+'spacing.labelNode': 2, key+'spacing.labelLabel': 4,
                              key+'spacing.labelPortHorizontal': 3}
        assert key+'spacing.labelPortVertical' not in individual
        assert result.origins[key+'spacing.individual'] == 'individualSpacings'
        result = context.element_options(first, algorithm='layered')
        assert result.values[key+'nodeSize.constraints'] == frozenset()
        assert result.values[key+'nodeSize.minimum'].x == 8 and result.values[key+'nodeSize.minimum'].y == 9
        assert result.values[key+'portAlignment.east'] == 'CENTER'
        assert result.values[key+'portLabels.treatAsGroup'] is False
        assert result.values[key+'nodeLabels.placement'] == frozenset({'H_CENTER','V_TOP','INSIDE'})
        assert context.element_options(second).values[key+'nodeSize.constraints'] == frozenset({'PORTS','MINIMUM_SIZE'})
        assert context.element_options(second).values[key+'spacing.individual'] == {key+'spacing.labelPortVertical':99}
    elif case == 'source-tokens':
        values, _ = parse_mapping({'nodeSize.minimum': '[(1d;2f;,)]',
            'nodeLabels.padding': '{left=-1,top=2,ignored=7,}', 'spacing.portPort': '-2.5D',
            'nodeSize.constraints': '[3,0,3,]', 'nodeSize.options': 1.0}, '/local')
        vector = values[key+'nodeSize.minimum']; assert (vector.x,vector.y) == (1,2)
        insets = values[key+'nodeLabels.padding']; assert (insets.top,insets.right,insets.bottom,insets.left) == (2,0,0,-1)
        assert values[key+'spacing.portPort'] == -2.5
        assert values[key+'nodeSize.constraints'] == frozenset({'PORTS','MINIMUM_SIZE'})
        assert values[key+'nodeSize.options'] == frozenset({'MINIMUM_SIZE_ACCOUNTS_FOR_PADDING'})
        values, _ = parse_mapping({'nodeLabels.padding': '{}', 'port.anchor': '1,2,'}, '/local')
        insets = values[key+'nodeLabels.padding']; assert (insets.top,insets.left,insets.bottom,insets.right) == (0,0,0,0)
        assert (values[key+'port.anchor'].x,values[key+'port.anchor'].y) == (1,2)
    elif case == 'source-whitespace':
        values, _ = parse_mapping({'nodeSize.constraints': 'PORTS\ufeffMINIMUM_SIZE',
                                  'spacing.portPort': '\ufeff1.5f\u00a0',
                                  'port.anchor': '\x001,\x012,',
                                  'nodeLabels.padding': '{\x00top\x00=\x001D\x00}'}, '/local')
        assert values[key+'nodeSize.constraints'] == frozenset({'PORTS','MINIMUM_SIZE'})
        assert values[key+'spacing.portPort'] == 1.5
        assert (values[key+'port.anchor'].x,values[key+'port.anchor'].y) == (1,2)
        assert values[key+'nodeLabels.padding'].top == 1
        for mapping in ({'nodeSize.constraints':'PORTS\u0085MINIMUM_SIZE'}, {'spacing.portPort':'\u00851'}):
            try: parse_mapping(mapping, '/local')
            except OptionValidationError: pass
            else: raise AssertionError('Python-only whitespace was accepted')
    elif case == 'bounded-admission':
        from pyelk import ELK, UnsupportedFeatureError
        root = Path(__file__).resolve().parents[2]
        request = json.loads((root/'tests/fixtures/suites/E09/requests/layered-chain.json').read_bytes())
        async def execute():
            engine = ELK(request['constructor'])
            try:
                original = copy.deepcopy(request['graph'])
                result = await engine.layout(request['graph'], request['layoutArguments'])
                assert (result['width'],result['height']) == (204,54)
                assert [n['x'] for n in result['children']] == [12,82,152]
                assert result['business'] == original['business']
                assert request['graph'] == original
                assert len(await engine.knownLayoutOptions()) == 9
                advanced = copy.deepcopy(original)
                advanced['layoutOptions']['portAlignment.default'] = 'CENTER'
                try: await engine.layout(advanced)
                except UnsupportedFeatureError as error: assert error.code == 'UNSUPPORTED_SLICE'
                else: raise AssertionError('Parse-only options widened bounded admission')
            finally:
                engine.terminateWorker()
        asyncio.run(execute())
    elif case == 'invalid-and-raw-preservation':
        bad = [{'nodeSize.constraints': ['PORTS']}, {'nodeSize.options': False},
               {'nodeSize.constraints': '[4]'}, {'nodeLabels.placement': 'inside'},
               {'spacing.labelNode': 'NaN'}, {'spacing.portPort': 'Infinity'},
               {'nodeLabels.padding': '{top=1,other=bad}'},
               {'spacing.individual': 'spacing.labelNode:1;spacing.portPort:2'},
               {'nodeSize.options': '[]', 'elk.nodeSize.options': 'PORTS'}]
        for mapping in bad:
            saved = copy.deepcopy(mapping)
            try: parse_mapping(mapping, '/local')
            except OptionValidationError: pass
            else: raise AssertionError('Invalid native property accepted: '+repr(mapping))
            assert mapping == saved
        raw = {'nodeSize.constraints': '[PORTS,3]', 'nodeLabels.padding': '[top=2]'}
        _, preserved = parse_mapping(raw, '/local')
        assert preserved[key+'nodeSize.constraints'] == '[PORTS,3]'
        assert preserved[key+'nodeLabels.padding'] == '[top=2]'
    else:
        raise ValueError('Unknown NodeContext property probe')
    assert graph == before
    return {'passed': True, 'case': case, 'privateSource': True,
            'modulePath': str(Path(pyelk.__file__).resolve()), 'publicAPIIntegrated': False, 'fullValidation': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.workspace,args.case)))
