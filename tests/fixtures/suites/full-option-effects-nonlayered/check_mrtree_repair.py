"""Affected MrTree guard regressions; no layout matrix or Source recapture.

The before module is an immutable native regression baseline, not an upstream
oracle. Existing Source RangeError is bound separately by the repair receipt.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class GeometryWrites(dict):
    def __init__(self, values):
        super().__init__(values)
        self.x_writes = 0

    def __setitem__(self, key, value):
        if key == 'XCOOR':
            self.x_writes += 1
        super().__setitem__(key, value)


def exercise(module, case):
    graph = module.TGraph(None)
    graph.properties.update(direction='DOWN')
    graph.properties['spacing.nodeNode'] = 11
    count = 1500 if case == 'deep-legal-chain' else 4
    for index in range(count):
        node = module.TNode(index, graph)
        node.size = module.Vec2(20, 12)
        node.properties = GeometryWrites({'ROOT': index == 0, 'LEVELHEIGHT': 12})
        graph.nodes.append(node)
    pairs = [(i, i+1) for i in range(count-1)] if count > 4 else [(0, 1), (0, 2), (1, 3), (2, 3)]
    for source, target in pairs:
        edge = module.TEdge(graph.nodes[source], graph.nodes[target])
        edge.source.outgoing_edges.append(edge)
        edge.target.incoming_edges.append(edge)
        graph.edges.append(edge)
    if case == 'shared-child-returned-revisit':
        graph.nodes[1].properties['RIGHTSIBLING'] = graph.nodes[2]
    module.place_nodes(graph)
    result = [{'id': node.id, 'x': node.properties['XCOOR'],
               'y': node.properties['YCOOR'], 'visits': node.properties.x_writes}
              for node in graph.nodes]
    assert all(row['visits'] > 0 for row in result)
    if count > 4:
        assert count > sys.getrecursionlimit()
        assert all(row['visits'] == 1 for row in result)
    else:
        assert result[3]['visits'] == 2
    return {'outcome': 'returned', 'nodeCount': count,
            'recursionLimit': sys.getrecursionlimit(), 'geometry': result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source))
    import pyelk.algorithms.mrtree as candidate
    before = load_module(args.before, 'pyelk.algorithms._mrtree_before_guard')
    args.out.mkdir(parents=True, exist_ok=False)
    cases = []
    for name in ['shared-child-returned-revisit', 'deep-legal-chain']:
        request = {'id': name, 'fixture': 'exercise', 'scriptSha256': digest(__file__)}
        expected = exercise(before, name)
        actual = exercise(candidate, name)
        assert expected == actual
        row = {'request': request, 'reference': expected, 'native': actual,
               'referenceRole': 'immutable-pre-repair-native-regression', 'passed': True}
        (args.out / (name+'.json')).write_text(json.dumps(row, indent=2)+'\n', encoding='utf8')
        cases.append({'id': name, 'passed': True, 'path': str(args.out/(name+'.json')),
                      'sha256': digest(args.out/(name+'.json'))})
    old = ast.parse(args.before.read_text(encoding='utf8'))
    new = ast.parse(Path(candidate.__file__).read_text(encoding='utf8'))
    old_without = [node for node in old.body if not isinstance(node, ast.FunctionDef) or node.name != 'place_nodes']
    new_without = [node for node in new.body if not isinstance(node, ast.FunctionDef) or node.name != 'place_nodes']
    assert ast.dump(ast.Module(body=old_without,type_ignores=[])) == ast.dump(ast.Module(body=new_without,type_ignores=[]))
    record = {'schema': 'pyelk-mrtree-valid-tree-regression/v1', 'passed': True,
              'candidateModuleSha256': digest(candidate.__file__), 'beforeModuleSha256': digest(args.before),
              'checkerSha256': digest(__file__), 'otherModuleAstUnchanged': True,
              'sourceOracleRecaptured': False, 'cases': cases}
    (args.out/'report.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in record.items() if k!='cases'}))


if __name__ == '__main__':
    main()
