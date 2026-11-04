"""Compare prepared-cell size arithmetic with the fixed original worker.

Usage: python compare_size_math.py PRIVATE_SRC REQUEST ORACLE REPORT
This does not run a public layout or the complete node-size process.
"""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    source, request, oracle, report = map(Path, sys.argv[1:])
    def tree():
        return {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(source.rglob('*.py'))}
    before = tree()
    original = json.loads(oracle.read_bytes())
    assert original['requestSha256'] == hashlib.sha256(request.read_bytes()).hexdigest()
    sys.path.insert(0, str(source.resolve()))
    from pyelk.algorithms.layered.graph import LGraph, LNode, LPort, Vec2, Insets
    from pyelk.algorithms.layered.node_size import NodeContext, PlacementPortContext
    from pyelk.algorithms.layered.cell_layout import AtomicCell, GridContainerCell, LabelCell, BEGIN, CENTER, END
    from pyelk.algorithms.layered import node_size_math as m
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
    from layout_checks import diff
    rows = []
    for s, expected in zip(json.loads(request.read_bytes())['cases'], original['results'], strict=True):
        assert s['id'] == expected['id']
        graph = LGraph(None, None, None)
        graph.properties['NODE_SIZE_FIXED_GRAPH_SIZE'] = s.get('fixedGraph', False)
        # The DTO uses a source vector literal for this one typed property.
        minimum = [float(v) for v in s.get('minimum', '(0,0)').strip('()').split(',')]
        props = dict(NODE_SIZE_MINIMUM=Vec2(*minimum), PORT_CONSTRAINTS=s['constraints'],
                     NODE_SIZE_CONSTRAINTS=set(s.get('sizeConstraints', [])), NODE_SIZE_OPTIONS=set(s.get('options', [])),
                     PORT_LABELS_PLACEMENT=set(s.get('labelPlacement', [])))
        if 'alignment' in s: props['PORT_ALIGNMENT_DEFAULT'] = s['alignment']
        node = LNode(graph, properties=props, size=Vec2(*s.get('nodeSize', [100, 60])))
        ctx = NodeContext(node)
        ctx.port_labels_treat_as_group = s.get('treatAsGroup', True)
        ctx.port_port_spacing = s.get('spacing', 10)
        ctx.surrounding_port_margins = Insets(*s.get('surrounding', [0, 0, 0, 0]))
        ctx.node_container.padding = Insets(3, 4, 5, 6)
        ctx.inside_node_label_container = GridContainerCell(False, False, 0)
        ctx.node_container_middle_row.set_cell(CENTER, ctx.inside_node_label_container)
        ctx.port_contexts = {side: [] for side in ('NORTH', 'EAST', 'SOUTH', 'WEST')}
        ports = []
        for item in s.get('ports', []):
            p = LPort(id=item['id'], side=item['side'], size=Vec2(*item.get('size', [4, 4])), pos=Vec2(*item.get('pos', [0, 0])))
            if 'ratio' in item: p.properties['PORT_RATIO_OR_POSITION'] = item['ratio']
            stage = PlacementPortContext(p, labels_next_to_port=item.get('next', True))
            if 'labels' in item:
                stage.port_label_cell = LabelCell(2, True)
                for size in item['labels']:
                    stage.port_label_cell.add_label(SimpleNamespace(size=Vec2(*size), pos=Vec2()))
            ctx.port_contexts[p.side].append(stage)
            ports.append((p.id, stage))
        for side in ('SOUTH', 'WEST'): ctx.port_contexts[side].reverse()
        for side in ctx.port_contexts:
            cell = AtomicCell()
            spec = s.get('cells', {}).get(side, {})
            cell.minimum_content_area_size = Vec2(*spec.get('minimum', [7, 9]))
            cell.padding = Insets(*spec.get('padding', [1, 2, 3, 4]))
            ctx.inside_port_label_cells[side] = cell
            if side in ('NORTH', 'SOUTH'): ctx.node_container.set_cell(BEGIN if side == 'NORTH' else END, cell)
            else: ctx.node_container_middle_row.set_cell(BEGIN if side == 'WEST' else END, cell)
        m.calculate_horizontal_port_placement_size(ctx)
        m.calculate_vertical_port_placement_size(ctx)
        m.configure_cell_system_size_contributions(ctx)
        minimum_node = m.get_minimum_node_or_client_area_size(ctx)
        m.set_node_width(ctx)
        m.update_vertical_inside_port_label_cell_padding(ctx)
        m.set_node_height(ctx)
        def snapshot(c):
            return dict(minimum=[c.get_minimum_width(), c.get_minimum_height()], content=[c.minimum_content_area_size.x, c.minimum_content_area_size.y],
                        padding=[c.padding.top, c.padding.right, c.padding.bottom, c.padding.left],
                        contributes=[c.contributes_to_minimum_width, c.contributes_to_minimum_height])
        value = dict(minimumNode=[minimum_node.x, minimum_node.y], nodeSize=[ctx.node_size.x, ctx.node_size.y],
                     nodeRectangle=[ctx.node_container.cell_rectangle.width, ctx.node_container.cell_rectangle.height],
                     cells={side: snapshot(cell) for side, cell in ctx.inside_port_label_cells.items()},
                     middleContributes=[ctx.node_container_middle_row.contributes_to_minimum_width, ctx.node_container_middle_row.contributes_to_minimum_height],
                     insideOnlyCenter=ctx.inside_node_label_container.only_center_cell_contributes_to_minimum_size,
                     ports=[dict(id=pid, margin=[p.port_margin.top, p.port_margin.right, p.port_margin.bottom, p.port_margin.left]) for pid, p in ports])
        comparison = diff(expected['value'], value)
        rows.append(dict(id=s['id'], differences=comparison['differences'], actual=value, expected=expected['value']))
    after = tree()
    result = dict(passed=before == after and all(not r['differences'] for r in rows), count=len(rows), rows=rows,
                  sourceTreeSha256=before, sourceTreeUnchanged=before == after,
                  inputsSha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), request, oracle)},
                  scope='Prepared real source cells, supplied label sizes and margins; not a public layout or full size/label process')
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(passed=result['passed'], count=len(rows), failed=[r['id'] for r in rows if r['differences']])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
