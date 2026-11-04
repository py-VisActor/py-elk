"""Compare new DisCo cached data/extension helpers with original observations.

Usage: python -I compare_disco_data.py PRIVATE_SRC REQUEST ORACLE REPORT
No importer, polygon predicates, rasterizer or packing provider is executed.
"""
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve(); sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.execution.json_transfer import JsonLayoutSession
    from pyelk.algorithms import disco
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('disco-data-probe.cjs'))
    def number(v):
        if math.isnan(v): return 'NaN'
        if math.isinf(v): return 'Infinity' if v>0 else '-Infinity'
        if v==0 and math.copysign(1,v)<0: return '-0'
        return v
    xy = lambda v:[number(v.x),number(v.y)]
    rect = lambda v:[number(v.x),number(v.y),number(v.width),number(v.height)]
    rows = []
    for case, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert case['id']==expected['id']
        state = JsonLayoutSession({'id':'identity-owner'})
        paths = [[disco.Vec2(*p) for p in points] for points in case['polygons']]
        elements = [disco.DCElement(path) for path in paths]
        extensions = [disco.DCExtension(elements[e['element']],getattr(disco,e['direction']),disco.Vec2(*e['middle']),e['width']) for e in case['extensions']]
        component = disco.DCComponent(state); component.add_elements(elements)
        first, corner, again = component.get_dimensions(), component.get_min_corner(), component.get_dimensions()
        offset = disco.Vec2(*case['offset']); component.set_offset(offset)
        moved, moved_corner = component.get_dimensions(), component.get_min_corner()
        if elements: component.add_elements([elements[0]])
        duplicate = component.get_dimensions()
        old = [rect(e.bounds) for e in elements]
        if paths: paths[0][0].x=case['mutateFirstX']
        new = [rect(e.bounds) for e in elements]
        groups = [[elements[0]], [elements[1],elements[0]] if len(elements)>1 else [elements[0]]] if elements else []
        graph = disco.DCGraph(state,groups)
        index = lambda value:next(i for i,e in enumerate(elements) if e is value)
        shape_order = lambda c:[index(e) for e in c.shapes.values()]
        value = dict(before=old,after=new,shapeReferences=[e.shape is paths[i] for i,e in enumerate(elements)],
                     extensions=[dict(direction=e.direction.name,horizontal=e.direction.horizontal,offset=xy(e.offset),width=e.width) for e in extensions],
                     first=xy(first),corner=xy(corner),sameCachedDimensions=first is again,moved=xy(moved),movedCorner=xy(moved_corner),
                     offsetReference=component.offset is offset,recomputedAfterOffset=first is not moved,
                     recomputedAfterDuplicate=moved is not duplicate if elements else False,shapeOrder=shape_order(component),
                     graphComponentShapes=[shape_order(c) for c in graph.components],
                     reparentedToLast=elements[0].component is graph.components[-1] if elements else None,
                     cellSize=number(disco.compute_cell_size(graph)),layoutExecuted=False)
        rows.append(dict(id=case['id'],actual=value,expected=expected['value'],differences=diff(expected['value'],value)['differences']))
    imported = {Path(module.__file__).resolve() for name,module in tuple(sys.modules.items())
                if (name=='pyelk' or name.startswith('pyelk.')) and getattr(module,'__file__',None)}
    unchanged = all(sha(p)==before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows),rows=rows,sourceTreeUnchanged=unchanged,
                  importedSourcesSha256={p.relative_to(source).as_posix():before[p] for p in imported},
                  inputsSha256={str(p):sha(p) for p in (Path(__file__),request,oracle)},layoutExecuted=False,
                  scope='Only new DisCo data, extensions, caches and source cell recommendation formula; nonfinite empty extrema remain tagged diagnostics')
    with report.open('x',encoding='utf-8') as handle: json.dump(result,handle,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],cases=len(rows))))
    return 0 if result['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
