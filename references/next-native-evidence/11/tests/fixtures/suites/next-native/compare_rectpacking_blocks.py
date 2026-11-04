"""PRIVATE_SRC REQUEST ORACLE NEW_REPORT: new Block/Stack operations only."""
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    source, request, oracle, report = map(Path, sys.argv[1:5])
    source = source.resolve()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {p.resolve(): sha(p) for p in source.rglob('*.py')}
    sys.path.insert(0, str(source))
    from pyelk.algorithms.rectpacking import Block, BlockStack, RectRow
    from pyelk.execution.json_transfer import JsonLayoutSession
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    original = json.loads(oracle.read_bytes())
    spec = json.loads(request.read_bytes())
    assert original['workerSha256'] == '275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86'
    assert original['requestSha256'] == sha(request)
    assert original['probeSha256'] == sha(request.with_name('rectpacking-block-probe.cjs'))
    def number(value):
        if math.isnan(value): return 'NaN'
        if math.isinf(value): return 'Infinity' if value > 0 else '-Infinity'
        if value == 0 and math.copysign(1, value) < 0: return '-0'
        return value
    def run(s):
        state = JsonLayoutSession(dict(id='block-root', children=s['rects']))
        nodes = state.graph['children']
        names = {id(p): item['id'] for p, item in zip(nodes, s['rects'])}
        parent = RectRow(s['y'], s['spacing'])
        blocks, initial_lists = [], []
        def make(x, y):
            b = Block(state, x, y, parent, s['spacing'])
            blocks.append(b)
            initial_lists.append((b.children, b.rows))
            parent.add_block(b)
            return b
        block = make(s['x'], s['y'])
        def rect(value):
            values = [value.get(k, 0) for k in ('x', 'y', 'width', 'height')] if type(value) is dict else [value.x, value.y, value.width, value.height]
            return [number(v) for v in values]
        def view(b):
            index = next(i for i, item in enumerate(blocks) if item is b)
            return dict(dimensions=rect(b), limits=[number(v) for v in (b.min_width, b.min_height,
                b.max_height, b.smallest_rect_width, b.smallest_rect_height, b.average_height)],
                children=[names[id(p)] for p in b.children],
                rows=[dict(dimensions=rect(row), rects=[names[id(p)] for p in row.rects]) for row in b.rows],
                sameChildren=b.children is initial_lists[index][0], sameRows=b.rows is initial_lists[index][1])
        def snap():
            return dict(blocks=[view(b) for b in blocks], nodes=[rect(p) for p in nodes],
                parent=[number(parent.width), number(parent.height)])
        steps, returned = [snap()], []
        if s['operation'] == 'stack':
            for p in nodes[:2]: block.add_child(p)
            other = make(s['x'], s['y'] + 11)
            for p in nodes[2:]: other.add_child(p)
            stack = BlockStack(s['x'], s['y'], s['spacing'])
            old_list = stack.blocks
            stack.add_block(block)
            stack.add_block(other)
            def ss():
                return dict(geometry=rect(stack), sameList=stack.blocks is old_list,
                    owned=[b.stack is stack for b in blocks], state=snap())
            stack_steps = [ss()]
            returned.append(number(stack.get_width_for_fixed_height(s['targetHeight'])))
            stack_steps.append(ss())
            stack.place_rects_in(s['targetWidth'])
            stack_steps.append(ss())
            stack.set_location(*s['move'])
            stack_steps.append(ss())
            stack.expand(*s['expand'])
            stack_steps.append(ss())
            return dict(id=s['id'], stackSteps=stack_steps, returned=returned, layoutExecuted=False)
        for p in nodes:
            block.add_child(p)
            steps.append(snap())
        if s['operation'] == 'place':
            returned.append(rect(block.place_rects_in(s['targetWidth'], False)))
            steps.append(snap())
            returned.append(number(block.get_width_for_target_height(s['targetHeight'])))
            steps.append(snap())
            returned.append(rect(block.place_rects_in(s['targetWidth'], True)))
            steps.append(snap())
        else:
            block.remove_child(nodes[1 if s['operation'] == 'remove-middle' else 0])
            steps.append(snap())
        return dict(id=s['id'], steps=steps, returned=returned, layoutExecuted=False)
    actual = [run(s) for s in spec['cases']]
    comparison = diff(original['results'], actual)
    imported = {Path(m.__file__).resolve() for name, m in tuple(sys.modules.items())
        if (name == 'pyelk' or name.startswith('pyelk.')) and getattr(m, '__file__', None)}
    unchanged = all(path in before and sha(path) == before[path] for path in imported)
    result = dict(passed=unchanged and comparison['passed'], actual=actual, expected=original['results'],
        comparison=comparison, sourceTreeUnchanged=unchanged,
        importedSourcesSha256={p.relative_to(source).as_posix(): before[p] for p in imported},
        inputsSha256={str(p): sha(p) for p in (Path(__file__), request, oracle)},
        layoutExecuted=False, fullValidation=False,
        scope='New mutable Block add/remove/limits, source simulation/real search, Stack strict height/absolute Y/move/expand and final removal IEEE; no old Drawing/Row reruns or complete packing provider')
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=result['passed'], differences=len(comparison['differences']))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
