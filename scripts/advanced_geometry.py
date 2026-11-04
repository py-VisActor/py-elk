"""Independent public-JSON geometry predicates; no pyelk or oracle mathematics.

Checks only declared geometric contracts, not a second layout implementation.
Unknown/unsupported preconditions are recorded as not_assessed. A partial
report never has passed=True. Source results use exactly the same predicates.
"""
from __future__ import annotations

import math
import re

ABS_TOL = 1e-6
REL_TOL = 1e-9


def _number(v):
    return type(v) in (int, float) and math.isfinite(v)


def _close(a, b):
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def _key(v):
    return type(v).__name__, str(v)


def _option(item, name, default=None):
    for key, value in item.get('layoutOptions', {}).items():
        if key in (name, 'elk.' + name, 'org.eclipse.elk.' + name):
            return value
    return default


def _flags(value):
    if isinstance(value, str):
        return set(re.findall(r'[A-Z_]+', value))
    return set(value or ())


def _vector(value):
    if isinstance(value, dict) and all(_number(value.get(k)) for k in ('x', 'y')):
        return value['x'], value['y']
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(_number(v) for v in value):
        return tuple(value)
    if isinstance(value, str):
        values = re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', value)
        if len(values) == 2:
            return tuple(float(v) for v in values)
    return None


def validate(request, result):
    """Return named predicate observations for one actual returned graph."""
    original = request.get('graph', request)
    errors, checked, not_assessed = [], [], []
    nodes, shapes, edges, originals, original_paths = {}, {}, [], {}, {}

    def error(path, code, **facts):
        errors.append(dict(path=path, code=code, **facts))

    def assessed(path, predicate):
        checked.append(dict(path=path, predicate=predicate))

    def skip(path, predicate, reason):
        not_assessed.append(dict(path=path, predicate=predicate, reason=reason))

    stack = [(original, '')]
    while stack:
        item, path = stack.pop()
        original_paths[path] = item
        if 'id' in item:
            originals[_key(item['id'])] = item
        for name in ('children', 'ports', 'labels', 'edges'):
            stack.extend((v, path + '/' + name + '/' + str(i)) for i, v in enumerate(item.get(name, [])))

    fixed_input_global = {}
    initial = [(original, (0, 0), True, 'layered')]
    while initial:
        item, parent_xy, fixed_ancestors, inherited_algorithm = initial.pop()
        algorithm = _option(item, 'algorithm', inherited_algorithm)
        xy = item.get('x', 0) + parent_xy[0], item.get('y', 0) + parent_xy[1]
        fixed = fixed_ancestors and algorithm in ('fixed', 'org.eclipse.elk.fixed')
        if fixed and all(_number(v) for v in xy):
            fixed_input_global[_key(item.get('id'))] = xy
        initial.extend((child, xy, fixed, algorithm) for child in item.get('children', []))

    def rect(item, path):
        vals = [item.get(k, 0) for k in ('x', 'y', 'width', 'height')]
        if not all(_number(v) for v in vals) or any(v < 0 for v in vals[2:]):
            error(path, 'invalid_shape_geometry', values=vals)
            return None
        assessed(path, 'finite_nonnegative_shape_geometry')
        return vals

    def inside(box, parent):
        x, y, w, h = box; px, py, pw, ph = parent
        return (x >= px - ABS_TOL and y >= py - ABS_TOL
                and x + w <= px + pw + ABS_TOL and y + h <= py + ph + ABS_TOL)

    def labels(owner, owner_info, owner_path):
        raw = originals.get(_key(owner.get('id')), {})
        for i, label in enumerate(owner.get('labels', [])):
            path = owner_path + '/labels/' + str(i)
            box = rect(label, path)
            if box is None:
                continue
            given = originals.get(_key(label.get('id')), original_paths.get(path, {}))
            for name in ('width', 'height'):
                if _number(given.get(name)):
                    if not _close(label.get(name, 0), given[name]):
                        error(path + '/' + name, 'given_label_size_changed', expected=given[name], actual=label.get(name, 0))
                    assessed(path, 'given_label_size')
            if owner_info['kind'] == 'node':
                placement = _flags(_option(raw, 'nodeLabels.placement'))
                if (owner_info['algorithm'] in ('layered', 'org.eclipse.elk.layered') and
                        'INSIDE' in placement and box[2] <= owner_info['box'][2] and box[3] <= owner_info['box'][3]):
                    local = box if owner_info['shape_mode'] != 'ROOT' else [box[0] - owner_info['box'][0], box[1] - owner_info['box'][1], *box[2:]]
                    if not inside(local, [0, 0, *owner_info['box'][2:]]):
                        error(path, 'inside_node_label_outside_owner')
                    assessed(path, 'explicit_inside_node_label')
                else:
                    skip(path, 'node_label_placement', 'No explicit fitting INSIDE placement; default/OUTSIDE placement and collision freedom are not assumed')
            else:
                skip(path, 'port_label_placement', 'Given size and finite position checked; OUTSIDE does not imply universal collision freedom')

    pending = [(result, None, '', 'PARENT', 'CONTAINER')]
    while pending:
        node, parent, path, inherited_shape, inherited_edge = pending.pop()
        box = rect(node, path)
        if box is None:
            continue
        raw = originals.get(_key(node.get('id')), {})
        sm = _option(raw, 'json.shapeCoords', 'INHERIT')
        em = _option(raw, 'json.edgeCoords', 'INHERIT')
        sm = inherited_shape if sm == 'INHERIT' else sm
        em = inherited_edge if em == 'INHERIT' else em
        if sm not in ('PARENT', 'ROOT') or em not in ('CONTAINER', 'PARENT', 'ROOT'):
            skip(path, 'coordinate_frames', 'Unrecognized coordinate mode')
            continue
        if parent is not None and parent['shape_mode'] == 'PARENT':
            box[0] += parent['box'][0]; box[1] += parent['box'][1]
        algorithm = _option(raw, 'algorithm', parent['algorithm'] if parent is not None else 'layered')
        info = dict(kind='node', box=box, parent=parent, shape_mode=sm, edge_mode=em,
                    algorithm=algorithm, item=node, path=path)
        nodes[_key(node.get('id'))] = info; shapes[_key(node.get('id'))] = info
        if _key(node.get('id')) in fixed_input_global:
            expected = fixed_input_global[_key(node.get('id'))]
            if not all(_close(a, b) for a, b in zip(box[:2], expected)):
                error(path, 'fixed_shape_coordinate_frame', expected=expected, actual=box[:2])
            assessed(path, 'fixed_input_position_in_declared_export_frame')
        if parent is not None and parent['algorithm'] in ('layered', 'org.eclipse.elk.layered'):
            if not inside(box, parent['box']):
                error(path, 'child_outside_parent', childBox=box, parentBox=parent['box'])
            assessed(path, 'nested_frame_parent_containment')
        elif parent is not None:
            skip(path, 'parent_containment', 'Non-Layered/fixed layouts may deliberately preserve positions outside the parent')
        for i, port in enumerate(node.get('ports', [])):
            pp = path + '/ports/' + str(i); pb = rect(port, pp)
            if pb is None:
                continue
            local = pb[:]
            if sm == 'PARENT':
                pb[0] += box[0]; pb[1] += box[1]
            else:
                local[0] -= box[0]; local[1] -= box[1]
            pi = dict(kind='port', box=pb, parent=info, item=port, path=pp, shape_mode=sm)
            shapes[_key(port.get('id'))] = pi
            rp = originals.get(_key(port.get('id')), {})
            constraint = _option(raw, 'portConstraints', 'UNDEFINED')
            side = _option(rp, 'port.side', 'UNDEFINED')
            offset = _option(rp, 'port.borderOffset')
            # An explicit offset defines the port rectangle's distance from
            # the owner boundary. FREE may deliberately change the input side.
            if constraint in ('FIXED_SIDE', 'FIXED_ORDER', 'FIXED_RATIO', 'FIXED_POS') and side in ('NORTH', 'EAST', 'SOUTH', 'WEST') and _number(offset):
                residual = {'NORTH': local[1] + local[3] + offset,
                            'EAST': local[0] - box[2] - offset,
                            'SOUTH': local[1] - box[3] - offset,
                            'WEST': local[0] + local[2] + offset}[side]
                if not _close(residual, 0):
                    error(pp, 'fixed_port_side_or_offset', side=side, residual=residual)
                assessed(pp, 'explicit_fixed_port_side_and_offset')
            else:
                skip(pp, 'fixed_port_side_and_offset', 'Requires fixed side, explicit cardinal side and explicit finite borderOffset')
            labels(port, pi, pp)
        labels(node, info, path)
        edges.extend((edge, info, path + '/edges/' + str(i)) for i, edge in enumerate(node.get('edges', [])))
        pending.extend((child, info, path + '/children/' + str(i), sm, em) for i, child in enumerate(node.get('children', [])))

    def ancestors(info):
        if info['kind'] == 'port':
            info = info['parent']
        answer = []
        while info is not None:
            answer.append(info); info = info['parent']
        return answer

    def on_border(p, box):
        x, y, w, h = box
        return (x - ABS_TOL <= p[0] <= x + w + ABS_TOL and y - ABS_TOL <= p[1] <= y + h + ABS_TOL
                and any((_close(p[0], x), _close(p[0], x + w), _close(p[1], y), _close(p[1], y + h))))

    for edge, owner, path in edges:
        ends = [shapes.get(_key(v)) for name in ('sources', 'targets') for v in edge.get(name, [])]
        if len(ends) != 2 or any(v is None for v in ends):
            skip(path, 'edge_endpoint_geometry', 'Requires two known simple-edge endpoints')
            continue
        if 'container' in edge:
            container = nodes.get(_key(edge['container']))
            if container is None or any(all(a is not container for a in ancestors(e)) for e in ends):
                error(path, 'invalid_edge_container')
                continue
        else:
            container = next((a for a in ancestors(ends[0]) if any(a is b for b in ancestors(ends[1]))), owner)
        assessed(path, 'edge_container_is_common_ancestor')
        mode = owner['edge_mode']
        frame = [0, 0] if mode == 'ROOT' else (owner['box'][:2] if mode == 'PARENT' else container['box'][:2])
        sections = edge.get('sections', [])
        if not sections:
            skip(path, 'sections', 'No exported sections')
            continue
        by_section = {_key(s.get('id')): s for s in sections}
        if len(by_section) != len(sections):
            error(path, 'duplicate_section_id')
        def point(s, key):
            p = s.get(key, {})
            if not all(_number(p.get(k)) for k in ('x', 'y')):
                raise ValueError('Nonfinite or missing section point')
            return p['x'] + frame[0], p['y'] + frame[1]
        for i, section in enumerate(sections):
            sp = path + '/sections/' + str(i)
            try:
                start, end = point(section, 'startPoint'), point(section, 'endPoint')
                bends = [point({'p': p}, 'p') for p in section.get('bendPoints', [])]
            except ValueError:
                error(sp, 'invalid_section_geometry'); continue
            assessed(sp, 'finite_section_points')
            routing = _option(originals.get(_key(owner['item'].get('id')), {}), 'edgeRouting', 'ORTHOGONAL')
            if routing == 'ORTHOGONAL' and owner['algorithm'] in ('layered', 'org.eclipse.elk.layered'):
                for a, b in zip([start, *bends], [*bends, end]):
                    if not (_close(a[0], b[0]) or _close(a[1], b[1])):
                        error(sp, 'nonorthogonal_section_segment', first=a, second=b)
                assessed(sp, 'orthogonal_section_segments')
            else:
                skip(sp, 'orthogonal_section_segments', 'Only computed Layered ORTHOGONAL sections carry this guarantee; fixed transfer and other routers do not')
            for direction, here, counterpart, endpoint in [('incoming', start, 'endPoint', ends[0]), ('outgoing', end, 'startPoint', ends[1])]:
                references = section.get(direction + 'Sections', [])
                for sid in references:
                    linked = by_section.get(_key(sid))
                    if linked is None:
                        error(sp, 'section_reference_missing', reference=sid)
                    else:
                        try:
                            there = point(linked, counterpart)
                            if not all(_close(a, b) for a, b in zip(here, there)):
                                error(sp, 'section_chain_disconnected', reference=sid)
                        except ValueError:
                            error(sp, 'invalid_section_geometry')
                if references:
                    assessed(sp, 'section_chain_connectivity')
                    continue
                sid = section.get(direction + 'Shape')
                if sid is not None and _key(sid) != _key(endpoint['item'].get('id')):
                    error(sp, 'section_endpoint_identity', direction=direction)
                if len(sections) != 1 and sid is None:
                    skip(sp, 'endpoint_attachment', 'Multi-section boundary lacks a shape reference'); continue
                if endpoint['kind'] == 'port':
                    raw = originals.get(_key(endpoint['item'].get('id')), {})
                    anchor = _vector(_option(raw, 'port.anchor'))
                    anchor_kind = 'explicit_port_anchor_attachment'
                    raw_owner = originals.get(_key(endpoint['parent']['item'].get('id')), {})
                    # For ordinary leaf-node fixed-side ports, a missing anchor
                    # is the side midpoint on the outward port boundary. This
                    # does not describe external compound dummies (whose two
                    # graph views need a separate contract), or FREE ports.
                    if (anchor is None and not raw_owner.get('children')
                            and endpoint['parent']['algorithm'] in ('layered', 'org.eclipse.elk.layered')
                            and _option(raw_owner, 'portConstraints') in ('FIXED_SIDE', 'FIXED_ORDER', 'FIXED_RATIO', 'FIXED_POS')):
                        side = _option(raw, 'port.side')
                        w, h = endpoint['box'][2:]
                        anchor = {'NORTH': (w / 2, 0), 'EAST': (w, h / 2),
                                  'SOUTH': (w / 2, h), 'WEST': (0, h / 2)}.get(side)
                        anchor_kind = 'default_fixed_leaf_port_anchor_attachment'
                    if anchor is not None:
                        wanted = endpoint['box'][0] + anchor[0], endpoint['box'][1] + anchor[1]
                        if not all(_close(a, b) for a, b in zip(here, wanted)):
                            error(sp, 'port_anchor_attachment', direction=direction, expected=wanted, actual=here)
                        assessed(sp, anchor_kind)
                    else:
                        skip(sp, 'port_anchor_attachment', 'Requires an explicit anchor or a fixed cardinal leaf-node port; FREE/external/hierarchical defaults are not inferred')
                elif owner['algorithm'] in ('layered', 'org.eclipse.elk.layered'):
                    if not on_border(here, endpoint['box']):
                        error(sp, 'node_endpoint_off_border', direction=direction, actual=here, box=endpoint['box'])
                    assessed(sp, 'node_endpoint_on_border_in_global_frame')
                else:
                    skip(sp, 'node_endpoint_attachment', 'Non-Layered/fixed geometry may intentionally preserve given endpoints off the node border')
        for i, label in enumerate(edge.get('labels', [])):
            lp = path + '/labels/' + str(i)
            if rect(label, lp) is not None:
                raw = originals.get(_key(label.get('id')), original_paths.get(lp, {}))
                for k in ('width', 'height'):
                    if _number(raw.get(k)) and not _close(label.get(k, 0), raw[k]):
                        error(lp, 'given_label_size_changed', dimension=k)
                assessed(lp, 'given_edge_label_size')
                skip(lp, 'edge_label_clearance', 'No universal nonoverlap/edge-distance constraint is assumed from label placement alone')
    return {'schema': 'py-elk-independent-advanced-geometry/v1',
            'passed': not errors and not not_assessed, 'status': 'FAIL' if errors else ('PARTIAL' if not_assessed else 'PASS'),
            'assessedPredicatesPassed': not errors, 'errors': errors, 'checked': checked,
            'not_assessed': not_assessed, 'coordinateTolerance': {'absolute': ABS_TOL, 'relative': REL_TOL},
            'sourceCoordinatesUsedAsExpectedValues': False, 'layoutMathImported': False}
