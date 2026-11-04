"""Compare new SPOrE scalar helpers against independent original objects.

Usage: python compare_spore_foundation.py PRIVATE_SRC REQUEST ORACLE REPORT [CASE_ID]
No import, jitter, triangulation, complete provider or layout runs here.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    selected = sys.argv[5] if len(sys.argv) > 5 else None
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.spore import SporeNode, SporeGraph, overlap_factor, Vec2, Rectangle
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('spore-foundation-probe.cjs'))
    rows = []
    xy = lambda v: [v.x, v.y]
    bounds = lambda r: [r.x, r.y, r.width, r.height]
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        if selected and selected != s['id']: continue
        vertex = Vec2(*s['vertex']); rect = Rectangle(*s['rectangle'])
        node = SporeNode(vertex, rect)
        other = SporeNode(Vec2(*s['otherVertex']), Rectangle(*s['other']))
        cost, tree, compaction = object(), object(), object()
        graph = SporeGraph(cost, tree, compaction); graph2 = SporeGraph(cost, tree, compaction)
        first = dict(vertex=xy(node.vertex), rectangle=bounds(node.rect), underlap=node.underlap(other), overlap=overlap_factor(node.rect, other.rect))
        node.translate(Vec2(*s['translate']))
        translated = dict(vertex=xy(node.vertex), rectangle=bounds(node.rect))
        node.set_center_position(Vec2(*s['center']))
        value = dict(before=first, translated=translated, after=dict(vertex=xy(node.vertex), rectangle=bounds(node.rect)),
                     originalVertex=xy(vertex), originalRectangle=bounds(rect), originalVertexReference=node.original_vertex is vertex,
                     workingVertexIndependent=node.vertex is not vertex, workingRectangleIndependent=node.rect is not rect,
                     graph=dict(vertices=graph.vertices, costIdentity=graph.cost_function is cost,
                                treeIdentity=graph.tree_construction_strategy is tree, compactionIdentity=graph.compaction_strategy is compaction,
                                independentVertices=graph.vertices is not graph2.vertices, orthogonalCompaction=graph.orthogonal_compaction), fullLayoutValidated=False)
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    assert rows and (not selected or len(rows) == 1)
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(module, '__file__', None)}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows, sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)}, fullLayoutValidated=False,
                  scope='New source Node/Graph/overlap geometry only; no jitter/import/Delaunay/packing or full provider')
    with report.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[row['id'] for row in rows if row['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
