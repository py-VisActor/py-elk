"""Compare new Spore import/cost/update/transfer with explicit translations.

Usage: python compare_spore_import.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
One collision fixture supplies entropy draws; no V8 trajectory or layout claim.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms.spore import SporeImporter, TEdge, Vec2
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name(original.get('probeFile', 'spore-import-probe.cjs')))
    rows = []
    def scalar(value):
        if not math.isfinite(value): return {'nonfinite': 'NaN' if math.isnan(value) else '+Infinity' if value > 0 else '-Infinity'}
        return dict(value=value, negativeZero=value == 0 and math.copysign(1, value) < 0)
    xy = lambda value: [value.x, value.y]
    bounds = lambda value: [value.x, value.y, value.width, value.height]
    def shape(value):
        return dict(id=value['id'], pos=[value['x'], value['y']], size=[value['width'], value['height']],
                    labels=[dict(pos=[l['x'], l['y']], size=[l['width'], l['height']]) for l in value.get('labels', [])])
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        if selected and selected != s['id']: continue
        saved = copy.deepcopy(s['graph']); state = JsonLayoutSession(s['graph']); draws = []
        if 'draws' in s:
            values = iter(s['draws'])
            def random_unit():
                value = next(values); draws.append(value); return value
            state.random_unit = random_unit
        importer = SporeImporter(); graph = importer.import_graph(state, state.graph)
        def imported():
            return [dict(id=importer.node_map.get(n.original_vertex)[1]['id'], original=xy(n.original_vertex),
                         working=xy(n.vertex), rectangle=bounds(n.rect)) for n in graph.vertices]
        def costs():
            edge = TEdge(graph.vertices[0].original_vertex, graph.vertices[1].original_vertex)
            return [scalar(f(edge)) for f in (importer.center_distance, importer.minimum_root_distance,
                    importer.circle_underlap, importer.rectangle_underlap, importer.inverted_overlap)]
        original_refs = [n.original_vertex for n in graph.vertices]; working_refs = [n.vertex for n in graph.vertices]
        value = dict(before=imported(), beforeCosts=costs(), direction=scalar(graph.vertices[0].directional_distance(graph.vertices[1], Vec2(*s['direction']))),
                     preferredRoot=importer.node_map.get(graph.preferred_root.original_vertex)[1]['id'] if getattr(graph, 'preferred_root', None) is not None else None)
        for node, translation in zip(graph.vertices, s['translations'], strict=True): node.translate(Vec2(*translation))
        graph.tree = graph.t_edges = object(); importer.update_graph(graph)
        value.update(updated=imported(), afterCosts=costs(), workingIdentity=[n.vertex is working_refs[i] for i, n in enumerate(graph.vertices)],
                     originalIdentityReplaced=[n.original_vertex is not original_refs[i] for i, n in enumerate(graph.vertices)],
                     treeCleared=graph.tree is None, edgesCleared=graph.t_edges is None)
        importer.apply_positions(graph)
        children = []
        for node in state.graph.get('children', []):
            margin = state.option(node, 'margins')
            children.append(dict(shape=shape(node), ports=[shape(p) for p in node.get('ports', [])],
                                 margin=[margin[k] for k in ('top', 'right', 'bottom', 'left')]))
        edges = [dict(id=edge['id'], sections=[dict(start=[sec['startPoint']['x'], sec['startPoint']['y']],
                    end=[sec['endPoint']['x'], sec['endPoint']['y']], bends=[[p['x'], p['y']] for p in sec.get('bendPoints', [])])
                    for sec in edge.get('sections', [])]) for edge in state.contained_edges(state.graph)]
        value.update(root=shape(state.graph), children=children, edgeGeometry=edges, draws=draws, instrumentedEntropy='draws' in s,
                     inputPreserved=diff(saved, s['graph'])['passed'], inputBeforeJSON=saved, inputAfterJSON=copy.deepcopy(s['graph']),
                     intermediateTranslationsSupplied=True, fullLayoutValidated=False)
        # Source wrappers may mutate their JSON input. Native ownership is a
        # separate, stronger declared policy, not expected upstream mutation.
        # Keep raw facts/differences; only these protocol diagnostics leave the
        # semantic geometry/cost comparison, never arbitrary business fields.
        assert value['inputPreserved'] is True
        diagnostics = {'inputPreserved', 'inputAfterJSON'}
        expected_view = {k: v for k, v in expected['value'].items() if k not in diagnostics}
        actual_view = {k: v for k, v in value.items() if k not in diagnostics}
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'],
                         strictRawDifferences=diff(expected['value'], value)['differences'],
                         differences=diff(expected_view, actual_view)['differences']))
    assert rows and (not selected or len(rows) == 1)
    imported_paths = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                      if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported_paths)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported_paths},
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, fullLayoutValidated=False,
                  nativeOwnedInputPreservedRequired=True, sourceMutationParityClaimed=False,
                  scope='Only source importer/cost/update/transfer with supplied intermediate translations and explicitly instrumented collision; no provider layout')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[row['id'] for row in rows if row['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
