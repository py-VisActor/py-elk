# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Mechanical provider port: elkjs 0.12.1 lib/elk-worker.js, F01-F14 in
# references/e16-basic-sources.json. Worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# The external Java build identity remains unresolved.
"""Real fixed-provider arithmetic, isolated from central engine integration.

The raw-JSON boundary is temporary host adaptation: central option parsing,
recursive scheduling and final ELK JSON import/export remain separate work.
No backend, reference fixture, input identity or graph-size reduction is used.
"""
from __future__ import annotations
import copy
import math
import re


def _div(a, b):
    """Host IEEE754 division adapter, including JS zero-denominator behavior."""
    if b == 0:
        return math.nan if a == 0 or math.isnan(a) else math.copysign(math.inf, a * math.copysign(1.0, b))
    return a / b


def _maximum(left, right):
    """Source Math.max, preserving NaN and the sign of zero."""
    if math.isnan(left) or math.isnan(right): return math.nan
    if left == right == 0:
        return 0.0 if math.copysign(1.0, left) > 0 or math.copysign(1.0, right) > 0 else -0.0
    return left if left > right else right


def _option(element, name, default=None, external=None):
    value = default
    for options in (external or {}, element.get('layoutOptions', {})):
        for key in (name, 'elk.'+name, 'org.eclipse.elk.'+name):
            if key in options:
                value = options[key]
    return value


def _vector(value, default=(0.0, 0.0)):
    if value is None:
        return default
    if hasattr(value, 'x') and hasattr(value, 'y'):
        return float(value.x), float(value.y)
    if isinstance(value, dict):
        return float(value.get('x', 0)), float(value.get('y', 0))
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return float(value[0]), float(value[1])
    values = re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', str(value))
    if len(values) != 2:
        raise ValueError('Invalid vector property')
    return tuple(map(float, values))


def _enum_set(value):
    if value is None:
        return set()
    return set(value) if isinstance(value, (list, tuple, set)) else set(re.findall(r'[A-Z_]+', str(value)))


def _padding(value=None):
    if value is None:
        return dict.fromkeys(('top', 'right', 'bottom', 'left'), 15.0)
    if hasattr(value, 'top') and hasattr(value, 'left'):
        return {key: float(getattr(value, key)) for key in ('top', 'right', 'bottom', 'left')}
    if isinstance(value, dict):
        return {key: float(value.get(key, 0)) for key in ('top', 'right', 'bottom', 'left')}
    if isinstance(value, (int, float)):
        return dict.fromkeys(('top', 'right', 'bottom', 'left'), float(value))
    pairs = dict(re.findall(r'(top|right|bottom|left)\s*=\s*([-+]?[\d.eE+-]+)', value))
    if pairs:
        return {key: float(pairs.get(key, 0)) for key in ('top', 'right', 'bottom', 'left')}
    raise ValueError('Invalid padding property')


def _owner_padding(state, node, default=15):
    """Read this provider's Property default on the actual mutable holder."""
    if hasattr(state, 'read_native_property'):
        from .layered.graph import Insets
        value = state.read_native_property(node, 'padding', Insets(default, default, default, default))
        return {side: float(getattr(value, side)) for side in ('top', 'right', 'bottom', 'left')}
    return _padding(state.option(node, 'padding', default))


def _native_option(state, element, name, default=None):
    """Use the actual Core Property getter for structured/shared defaults."""
    getter = getattr(state, 'get_native_property', None)
    return getter(element, name) if getter is not None else state.option(element, name, default)


class _State:
    """Transient imported relations; never written into caller business data."""
    def __init__(self, graph, options=None):
        self.graph = copy.deepcopy(graph)
        self.options = options or {}
        self.shapes = {}; self.owners = {}; self.parents = {}; self.edges = []
        self.cleared_constraints = set()
        self.computed_options = {}
        self._index(self.graph, None)

    def _index(self, node, parent):
        self.parents[id(node)] = parent
        self._shape(node, node)
        for port in node.get('ports', []):
            self._shape(port, node)
        self.edges.extend(node.get('edges', []))
        for child in node.get('children', []):
            self._index(child, node)

    def _shape(self, shape, owner):
        key = (type(shape.get('id')), shape.get('id'))
        if key in self.shapes:
            raise ValueError('Duplicate shape identifier')
        self.shapes[key] = shape; self.owners[id(shape)] = owner
        for field in ('x', 'y', 'width', 'height'):
            shape.setdefault(field, 0)
        for label in shape.get('labels', []):
            for field in ('x', 'y', 'width', 'height'):
                label.setdefault(field, 0)

    def endpoint(self, edge, incoming=False):
        identifiers = edge.get('targets' if incoming else 'sources', [])
        if not identifiers:
            raise ValueError('Edge endpoint is empty')
        return self.shapes[(type(identifiers[0]), identifiers[0])]

    def incidence(self, shape, incoming=False):
        key = 'targets' if incoming else 'sources'
        return [edge for edge in self.edges if any(type(value) is type(shape['id']) and value == shape['id'] for value in edge.get(key, []))]

    def node_edges(self, node, incoming=False):
        return [edge for shape in (node, *node.get('ports', [])) for edge in self.incidence(shape, incoming)]

    def option(self, element, name, default=None):
        if name == 'nodeSize.constraints' and id(element) in self.cleared_constraints:
            return []
        if name in self.computed_options.get(id(element), {}):
            return self.computed_options[id(element)][name]
        return _option(element, name, default, self.options)


def _minimum(state, node):
    native = getattr(state, 'get_native_property', None)
    constraints = native(node, 'nodeSize.constraints') if native is not None else state.option(node, 'nodeSize.constraints', [])
    if 'MINIMUM_SIZE' not in _enum_set(constraints):
        return 0.0, 0.0
    # Source reads options before minimum, then clones the retrieved vector.
    options = native(node, 'nodeSize.options') if native is not None else state.option(node, 'nodeSize.options', ['DEFAULT_MINIMUM_SIZE'])
    minimum = native(node, 'nodeSize.minimum') if native is not None else state.option(node, 'nodeSize.minimum')
    x, y = _vector(minimum)
    if 'DEFAULT_MINIMUM_SIZE' in _enum_set(options):
        x = 20.0 if x <= 0 else x; y = 20.0 if y <= 0 else y
    return x, y


def _port_side(port, node, direction):
    width, height = node['width'], node['height']
    if width <= 0 and height <= 0:
        return 'UNDEFINED'
    x, y = port['x'], port['y']
    if direction in ('LEFT', 'RIGHT'):
        if x < 0: return 'WEST'
        if x+port['width'] > width: return 'EAST'
    elif direction in ('UP', 'DOWN'):
        if y < 0: return 'NORTH'
        if y+port['height'] > height: return 'SOUTH'
    w = _div(x+port['width']/2, width); h = _div(y+port['height']/2, height)
    return ('WEST' if w+h <= 1 and w-h <= 0 else
            'EAST' if w+h >= 1 and w-h >= 0 else 'NORTH' if h < .5 else 'SOUTH')


def _resize(state, node, width, height, move_ports, move_labels):
    minimum = _minimum(state, node)
    width, height = _maximum(minimum[0], width), _maximum(minimum[1], height)
    old_width, old_height = node['width'], node['height']
    wr, hr = _div(width, old_width), _div(height, old_height)
    wd, hd = width-old_width, height-old_height
    if move_ports:
        parent = state.parents[id(node)]
        direction = state.option(parent if parent is not None else node, 'direction', 'UNDEFINED')
        fixed = state.option(node, 'portConstraints', 'UNDEFINED') == 'FIXED_POS'
        for port in node.get('ports', []):
            side = state.option(port, 'port.side', 'UNDEFINED')
            if side == 'UNDEFINED':
                side = _port_side(port, node, direction)
                state.computed_options.setdefault(id(port), {})['port.side'] = side
            if side in ('NORTH', 'SOUTH') and not fixed: port['x'] *= wr
            if side == 'EAST': port['x'] += wd
            if side in ('EAST', 'WEST') and not fixed: port['y'] *= hr
            if side == 'SOUTH': port['y'] += hd
    node['width'], node['height'] = width, height
    if move_labels:
        for label in node.get('labels', []):
            mx = label['x']+label['width']/2; my = label['y']+label['height']/2
            wp, hp = _div(mx, old_width), _div(my, old_height)
            if wp+hp >= 1:
                if wp-hp > 0 and my >= 0:
                    label['x'] += wd; label['y'] += hd*hp
                elif wp-hp < 0 and mx >= 0:
                    label['x'] += wd*wp; label['y'] += hd
    state.computed_options.setdefault(id(node), {})['nodeSize.constraints'] = set()
    state.cleared_constraints.add(id(node))
    return wr, hr


def _set_position(state, shape):
    position = _native_option(state, shape, 'position')
    if position is not None:
        shape['x'], shape['y'] = _vector(position)
    return position is not None


def _apply_chain(edge, chain):
    if not isinstance(chain, (list, tuple)):
        pairs = re.findall(r'\([^()]*\)', chain)
        chain = [_vector(pair) for pair in pairs]
    else:
        chain = [_vector(pair) for pair in chain]
    if len(chain) < 2:
        raise ValueError('The vector chain must contain at least a source and a target point.')
    sections = edge.setdefault('sections', [])
    if len(sections) > 1:
        # F04 calls iterator.remove before next; do not silently repair it.
        raise ValueError('IllegalStateException')
    if not sections:
        sections.append({})
    section = sections[0]
    section['startPoint'] = dict(zip(('x', 'y'), chain[0]))
    section['endPoint'] = dict(zip(('x', 'y'), chain[-1]))
    section['bendPoints'] = [dict(zip(('x', 'y'), p)) for p in chain[1:-1]]


def _process_edge(state, edge):
    source, target = state.endpoint(edge), state.endpoint(edge, True)
    same = state.parents[id(state.owners[id(source)])] is state.parents[id(state.owners[id(target)])]
    bends = state.option(edge, 'bendPoints')
    if bends is not None:
        # The provider ignores a vector-chain with fewer than two points.
        parsed = bends if isinstance(bends, (list, tuple)) else re.findall(r'\([^()]*\)', bends)
        if len(parsed) >= 2: _apply_chain(edge, parsed)
    mx, my = 0.0, 0.0
    if same:
        for section in edge.get('sections', []):
            for point in section.get('bendPoints', []):
                mx = _maximum(mx, point['x']); my = _maximum(my, point['y'])
    for label in edge.get('labels', []):
        for field in ('x', 'y', 'width', 'height'): label.setdefault(field, 0)
        _set_position(state, label)
        if same:
            mx = _maximum(mx, label['x']+label['width']); my = _maximum(my, label['y']+label['height'])
    return mx, my


def _points(section):
    points = [section['startPoint'], *section.get('bendPoints', []), section['endPoint']]
    i = 1
    while i < len(points)-1:
        a, b, c = points[i-1:i+2]
        if a['x'] == b['x'] == c['x'] or a['y'] == b['y'] == c['y']: points.pop(i)
        else: i += 1
    return points


def _one_section(edge):
    sections = edge.get('sections', [])
    if len(sections) != 1:
        raise ValueError('The edge needs to have exactly one edge section. Found: '+str(len(sections)))
    return sections[0]


def _junctions_at(state, edge, port, reverse):
    points = _points(_one_section(edge)); others = []
    for other in (*state.incidence(port, True), *state.incidence(port)):
        # F08 tests current edge, not other; a missing other section fails at get.
        _one_section(edge)
        if other is edge: continue
        other_points = _points(other.get('sections', [])[0])
        a = points[-1 if reverse else 0]; b = other_points[-1 if reverse else 0]
        others.append((other_points, a['x']-b['x'], a['y']-b['y']))
    result = []; p1 = points[-1 if reverse else 0]
    sign = lambda x: 0 if x == 0 else 1 if x > 0 else -1
    for i in range(1, len(points)):
        p2 = points[-1-i if reverse else i]
        remaining = []
        for other_points, ox, oy in others:
            if len(other_points) <= i: continue
            p3 = other_points[-1-i if reverse else i]
            x3, y3 = p3['x']+ox, p3['y']+oy
            if p2['x'] != x3 or p2['y'] != y3:
                dx2, dy2 = p2['x']-p1['x'], p2['y']-p1['y']
                dx3, dy3 = x3-p1['x'], y3-p1['y']
                if dx3*dy2 == dy3*dx2 and sign(dx2) == sign(dx3) and sign(dy2) == sign(dy3):
                    if abs(dx2) < abs(dx3) or abs(dy2) < abs(dy3): result.append(dict(p2))
                elif i > 1: result.append(dict(p1))
            else: remaining.append((other_points, ox, oy))
        others = remaining; p1 = p2
    return result


def _layout(state, node, monitor=None):
    if monitor is not None: monitor.begin('Fixed Layout', 1)
    mx, my = 0.0, 0.0
    for child in node.get('children', []):
        if _set_position(state, child) and 'MINIMUM_SIZE' in _enum_set(_native_option(state, child, 'nodeSize.constraints', [])):
            width, height = _vector(_native_option(state, child, 'nodeSize.minimum'))
            if width > 0 and height > 0: _resize(state, child, width, height, True, True)
        mx = _maximum(mx, child['x']+child['width']); my = _maximum(my, child['y']+child['height'])
        for label in child.get('labels', []):
            _set_position(state, label)
            mx = _maximum(mx, child['x']+label['x']+label['width']); my = _maximum(my, child['y']+label['y']+label['height'])
        for port in child.get('ports', []):
            _set_position(state, port); px, py = child['x']+port['x'], child['y']+port['y']
            mx = _maximum(mx, px+port['width']); my = _maximum(my, py+port['height'])
            for label in port.get('labels', []):
                _set_position(state, label)
                mx = _maximum(mx, px+label['x']+label['width']); my = _maximum(my, py+label['y']+label['height'])
        for edge in state.node_edges(child):
            ex, ey = _process_edge(state, edge); mx, my = _maximum(mx, ex), _maximum(my, ey)
        for edge in state.node_edges(child, True):
            if len(edge.get('sources', [])) != 1 or len(edge.get('targets', [])) != 1:
                raise ValueError("Passed edge is not 'simple'.")
            if state.parents[id(state.owners[id(state.endpoint(edge))])] is not node:
                ex, ey = _process_edge(state, edge); mx, my = _maximum(mx, ex), _maximum(my, ey)
    if state.option(node, 'edgeRouting', 'UNDEFINED') == 'ORTHOGONAL':
        for child in node.get('children', []):
            for edge in state.node_edges(child):
                _one_section(edge); points = []
                for reverse in (False, True):
                    shape = state.endpoint(edge, reverse)
                    if state.owners[id(shape)] is not shape: points.extend(_junctions_at(state, edge, shape, reverse))
                if hasattr(state,'set_generated_junction_points'):
                    state.set_generated_junction_points(edge,points)
                elif points: edge['junctionPoints'] = points
                else: edge.pop('junctionPoints', None)
    if not state.option(node, 'nodeSize.fixedGraphSize', False):
        padding = _owner_padding(state, node)
        _resize(state, node, mx+padding['left']+padding['right'], my+padding['top']+padding['bottom'], True, True)
    if monitor is not None: monitor.done()


def layout_fixed(graph, options=None, *, monitor=None):
    """Apply one fixed-provider call through the shared typed JSON boundary."""
    from ..execution.json_transfer import JsonLayoutSession
    state = JsonLayoutSession(graph, options)
    _layout(state, state.graph, monitor)
    return state.export()
