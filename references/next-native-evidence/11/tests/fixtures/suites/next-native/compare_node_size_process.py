"""Replay saved original standalone node-size process observations.

Usage: python compare_node_size_process.py PRIVATE_SRC REQUEST ORACLE REPORT
Only real LGraph objects are adapted; generic adapter/public layout is separate.
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, Vec2, set_port_owner
    from pyelk.algorithms.layered.import_export import _SIZE_OPTION_PROPERTIES, _native_size_value
    from pyelk.options.element import parse_mapping
    from pyelk.algorithms.layered.node_size_process import process_node_size
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    assert original['requestSha256'] == sha(request)
    keys = dict(_SIZE_OPTION_PROPERTIES, portConstraints='PORT_CONSTRAINTS', direction='DIRECTION', **{'port.borderOffset': 'PORT_BORDER_OFFSET'})
    def props(values):
        parsed, _ = parse_mapping({'org.eclipse.elk.'+k: v for k, v in (values or {}).items()}, '')
        return {keys[k.removeprefix('org.eclipse.elk.')]: _native_size_value(v) for k, v in parsed.items()}
    def label(spec):
        return SimpleNamespace(pos=Vec2(*spec.get('pos', [0, 0])), size=Vec2(*spec['size']), properties=props(spec.get('options')))
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        graph = LGraph(None, None, None, properties=props(s.get('graphOptions')))
        node = LNode(graph, size=Vec2(*s['size']), pos=Vec2(*s.get('pos', [0, 0])), properties=props(s.get('options')))
        node.labels = [label(l) for l in s.get('labels', [])]
        ports = []
        for item in s.get('ports', []):
            p = LPort(side=item['side'], size=Vec2(*item.get('size', [4, 4])), pos=Vec2(*item.get('pos', [0, 0])), properties=props(item.get('options')))
            p.labels = [label(l) for l in item.get('labels', [])]
            set_port_owner(p, node)
            ports.append(p)
        def lv(l): return [l.pos.x, l.pos.y, l.size.x, l.size.y]
        def snapshot():
            return dict(node=dict(pos=[node.pos.x, node.pos.y], size=[node.size.x, node.size.y], padding=[node.padding.top, node.padding.right, node.padding.bottom, node.padding.left], labels=[lv(l) for l in node.labels]),
                        ports=[dict(pos=[p.pos.x, p.pos.y], size=[p.size.x, p.size.y], labels=[lv(l) for l in p.labels]) for p in ports])
        value = dict(before=snapshot())
        staged = process_node_size(graph, node, s.get('apply', True), False)
        value.update(stagedSize=[staged.x, staged.y], after=snapshot())
        rows.append(dict(id=s['id'], actual=value, expected=expected['value'], differences=diff(expected['value'], value)['differences']))
    imported = {Path(module.__file__).resolve() for name, module in tuple(sys.modules.items())
                if name == 'pyelk' or name.startswith('pyelk.') if getattr(module, '__file__', None)}
    hashes = {p.relative_to(source).as_posix(): before[p] for p in imported}
    unchanged = all(sha(p) == before[p] for p in imported)
    result = dict(passed=unchanged and all(not row['differences'] for row in rows), rows=rows,
                  importedSourcesSha256=hashes, sourceTreeUnchanged=unchanged,
                  inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
                  scope='Standalone size process over real LGraph objects; not generic micro-layout or complete layered/public API')
    report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(passed=result['passed'], cases=len(rows), failed=[row['id'] for row in rows if row['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
