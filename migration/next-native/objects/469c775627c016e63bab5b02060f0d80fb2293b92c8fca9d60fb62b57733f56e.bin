# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Guava fuzzy comparison: Copyright (C) 2011 The Guava Authors, Apache-2.0.
# Fixed caller adaptation, not the entire Guava class or GWT runtime. See the
# private NOTICE-Guava-DoubleMath.md; exact external build remains unresolved.
# Fixed elkjs0.12.1 worker approved R01/R03/R04/R08/R12/R14/R15 from
# references/e17-tree-sources.json. Worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# External Java build identity remains unresolved.
"""Native radial topology, Eades placement, compaction, rotation and routing."""
from __future__ import annotations
import math
from .fixed import _div, _vector, _padding, _owner_padding, _State
from .layered.graph import Vec2
from .layered.ports import _source_sort
from ..execution.identity import identity_hash as _host_identity_hash


def _maximum(left, right):
    if math.isnan(left) or math.isnan(right): return math.nan
    if left == right == 0:
        return 0.0 if math.copysign(1.0, left) > 0 or math.copysign(1.0, right) > 0 else -0.0
    return max(left, right)


def find_root(state, graph):
    """First zero-incoming child, not an invented blanket topology validator."""
    for child in graph.get('children', []):
        if not state.node_edges(child, True): return child
    return None


def find_largest_node_in_graph(graph):
    """Original largest descendant diagonal; the given container is excluded."""
    frames = [{'node': graph, 'index': 0, 'largest': 0.0}]
    while frames:
        frame = frames[-1]; children = frame['node'].get('children', [])
        if frame['index'] == len(children):
            result = frame['largest']; frames.pop()
            if frames: frames[-1]['largest'] = _maximum(result, frames[-1]['largest'])
            else: return result
        else:
            child = children[frame['index']]; frame['index'] += 1
            width, height = child['width'], child['height']
            frame['largest'] = _maximum(math.sqrt(width*width+height*height), frame['largest'])
            frames.append({'node': child, 'index': 0, 'largest': 0.0})


def successors(state, node):
    """R03 actual ordered ArrayList, including parallel duplicate targets."""
    contained = IdentitySet(state, node.get('children', [])); result = []
    for edge in state.node_edges(node):
        source = state.endpoint(edge)
        if state.owners[id(source)] is not source: continue  # Actual source port exclusion.
        target = state.owners[id(state.endpoint(edge, True))]
        if not contained.contains(target): result.append(target)
    return result


def next_level_nodes(state, nodes):
    return [child for node in nodes for child in successors(state, node)]


def tree_parent(state, node):
    edges = state.node_edges(node, True)
    return state.owners[id(state.endpoint(edges[0]))] if edges else None


def find_root_of_node(state, node):
    while True:
        parent = tree_parent(state, node)
        if parent is None: return node
        node = parent


def number_of_leaves(state, node):
    """R03 recursion represented by frames, not a new Python depth cap."""
    work = [('visit', node)]; values = []
    while work:
        operation, value = work.pop()
        if operation == 'sum':
            result = 0
            for leaf_count in values[-value:]: result += leaf_count
            del values[-value:]; values.append(result)
        else:
            children = successors(state, value)
            if not children: values.append(1)
            else:
                work.append(('sum', len(children)))
                for child in reversed(children): work.append(('visit', child))
    return values[0]


def node_space_wedge(state, node):
    """R12 max(sum(child space), own diagonal) with source addition order."""
    work = [('visit', node)]; values = []
    while work:
        operation, value = work.pop()
        if operation == 'merge':
            current, count = value; child_space = 0
            if count:
                for area in values[-count:]: child_space += area
                del values[-count:]
            height, width = current['height'], current['width']
            values.append(_maximum(child_space, math.sqrt(height*height+width*width)))
        else:
            children = successors(state, value); work.append(('merge', (value, len(children))))
            for child in reversed(children): work.append(('visit', child))
    return values[0]


def _acos(value):
    # Source JS intrinsic produces NaN outside its domain instead of raising.
    try: return math.acos(value)
    except ValueError: return math.nan


def _sin(value):
    try: return math.sin(value)
    except ValueError: return math.nan


def _cos(value):
    try: return math.cos(value)
    except ValueError: return math.nan


def clip_vector(vector, width, height):
    """R15 reviewed rectangle clipping, mutating the actual given vector."""
    half_width, half_height = width/2, height/2
    x_scale = y_scale = 1
    if abs(vector.x) > half_width: x_scale = _div(half_width, abs(vector.x))
    if abs(vector.y) > half_height: y_scale = _div(half_height, abs(vector.y))
    scale = -_maximum(-x_scale, -y_scale)
    vector.x *= scale; vector.y *= scale
    return vector


def _log_graph(monitor, graph, tag):
    if monitor is None: return
    observer = getattr(monitor, 'log_graph', None)
    if observer is not None: observer(graph, tag)
    elif getattr(monitor, 'record_logs', False):
        raise TypeError('The supplied logging monitor must provide log_graph')
    # With record_logs=False, original BasicProgressMonitor.logGraph is a noop.


def eades_layout(state, graph, monitor=None, *, sorter=None, optimizer=None):
    """R12 real core, with reviewed strategy objects supplied by their factories.

    Factories use the separately reviewed actual sorter/objective mathematics;
    no strategy is replaced by a fallback or simpler layout.
    """
    if monitor is not None: monitor.begin('Eades radial', 1)
    _log_graph(monitor, graph, 'After')
    root = state.option(graph, 'root')
    if root is None: raise ValueError('The radial root property has not been set')
    radius = state.option(graph, 'radial.radius', 0)
    if sorter is None: sorter = create_sorter(state, state.option(graph, 'radial.sorter', 'NONE'))
    if optimizer is None: optimizer = create_optimizer(state, state.option(graph, 'radial.optimizationCriteria', 'NONE'))
    criterion = state.option(graph, 'radial.wedgeCriteria', 'NODE_SIZE')
    if criterion == 'LEAF_NUMBER': wedge = lambda node: number_of_leaves(state, node)
    elif criterion == 'NODE_SIZE': wedge = lambda node: node_space_wedge(state, node)
    else: raise ValueError('Unknown effective radial wedge criterion: '+str(criterion))

    def position(offset):
        # The source computes the child alpha after every completed recursive
        # child. A frame retains that exact sequential arithmetic and timing.
        work = [('visit', root, 0, 0, 6.283185307179586)]
        while work:
            operation, *arguments = work.pop()
            if operation == 'children':
                children, index, current_radius, alpha, step = arguments
                if index == len(children): continue
                child = children[index]; count = wedge(child); following = alpha+step*count
                work.append(('children', children, index+1, current_radius, following, step))
                work.append(('visit', child, current_radius+radius, alpha, following))
                continue
            node, current_radius, minimum_alpha, maximum_alpha = arguments
            alpha_point = (minimum_alpha+maximum_alpha)/2+offset
            node['x'] = current_radius*_cos(alpha_point)-node['width']/2
            node['y'] = current_radius*_sin(alpha_point)-node['height']/2
            count = wedge(node)
            # Keep the literal original parentheses; do not repair this formula.
            tau = 2*_acos(_div(current_radius, current_radius)+radius)
            if tau < maximum_alpha-minimum_alpha:
                step = _div(tau, count); alpha = (minimum_alpha+maximum_alpha-tau)/2
            else:
                step = _div(maximum_alpha-minimum_alpha, count); alpha = minimum_alpha
            children = successors(state, node)
            if sorter is not None:
                sorter.initialize(root); sorter.sort(children)
            work.append(('children', children, 0, current_radius, alpha, step))

    optimal_offset = 0; optimal_value = 1.7976931348623157e308
    if optimizer is not None:
        for index in range(360):
            offset = index*0.017453292519943295; position(offset)
            value = optimizer.evaluate(root)
            if value < optimal_value: optimal_offset = offset; optimal_value = value
    position(optimal_offset)
    _log_graph(monitor, graph, 'After')


def position_vector(state, node):
    """Decode one mutable vector per source property, preserving later mutation."""
    getter = getattr(state, 'get_native_property', None)
    if getter is not None:
        vector = getter(node, 'position')
        if vector is None: raise TypeError('The radial position property is null')
        return vector
    bag = state.computed_options.setdefault(id(node), {})
    if isinstance(bag.get('position'), Vec2): return bag['position']
    value = state.option(node, 'position')
    if value is None: raise TypeError('The radial position property is null')
    if hasattr(value, 'x') and hasattr(value, 'y'): vector = Vec2(value.x, value.y)
    else: vector = Vec2(*_vector(value))
    bag['position'] = vector
    return vector


def _angle_compare(state, left, right, offset):
    """R04 actual fixed-tolerance Guava fuzzyCompare caller adaptation."""
    a = position_vector(state, left); b = position_vector(state, right)
    first = math.atan2(a.y+0, a.x); second = math.atan2(b.y+0, b.x)
    if first < 0: first += 6.283185307179586
    first += offset
    if first > 6.283185307179586: first -= 6.283185307179586
    if second < 0: second += 6.283185307179586
    second += offset
    if second > 6.283185307179586: second -= 6.283185307179586
    if abs(first-second) <= 1e-10 or first == second or math.isnan(first) and math.isnan(second): return 0
    if first < second: return -1
    if first > second: return 1
    return int(math.isnan(first))-int(math.isnan(second))


class IDSorter:
    def __init__(self, state): self.state = state

    def initialize(self, root): pass

    def sort(self, nodes):
        def compare(a, b):
            first = self.state.option(a, 'radial.orderId', 0); second = self.state.option(b, 'radial.orderId', 0)
            return -1 if first < second else 1 if first > second else 0
        _source_sort(nodes, compare)


class PolarCoordinateSorter:
    def __init__(self, state):
        self.state = state; self.id_sorter = None

    def initialize(self, root):
        self.id_sorter = IDSorter(self.state)
        nodes = successors(self.state, root)
        _source_sort(nodes, lambda a, b: _angle_compare(self.state, a, b, 0))
        # Preserve source idOffset/nextLayerId recursion with explicit frames.
        frames = [{'nodes': nodes, 'index': 0, 'id': 0, 'next': 0}]
        while frames:
            frame = frames[-1]
            if frame['index'] == len(frame['nodes']):
                result = frame['id']; frames.pop()
                if frames: frames[-1]['next'] = result
                continue
            node = frame['nodes'][frame['index']]; frame['index'] += 1
            self.state.computed_options.setdefault(id(node), {})['radial.orderId'] = frame['id']; frame['id'] += 1
            children = successors(self.state, node)
            arc = math.atan2(node['y']+node['height']/2, node['x']+node['width']/2)
            if arc < 0: arc += 6.283185307179586
            offset = None
            if arc < .7853981633974483 or arc > 5.497787143782138: offset = 3.141592653589793
            elif arc <= 5.497787143782138 and arc > 3.9269908169872414: offset = 4.71238898038469
            elif arc <= 3.9269908169872414 and arc > 2.356194490192345: offset = 0
            elif arc <= 2.356194490192345: offset = 1.5707963267948966
            if offset is not None: _source_sort(children, lambda a, b: _angle_compare(self.state, a, b, offset))
            frames.append({'nodes': children, 'index': 0, 'id': frame['next'], 'next': 0})

    def sort(self, nodes):
        if nodes:
            if self.id_sorter is None: self.initialize(find_root_of_node(self.state, nodes[0]))
            self.id_sorter.sort(nodes)


class EdgeLengthOptimization:
    def __init__(self, state): self.state = state

    def evaluate(self, root):
        length = 0
        for edge in self.state.node_edges(root):
            target = self.state.owners[id(self.state.endpoint(edge, True))]
            target_x, target_y = target['x']+target['width']/2, target['y']+target['height']/2
            root_x, root_y = root['x']+root['width']/2, root['y']+root['height']/2
            vector = Vec2(target_x-root_x, target_y-root_y)
            clipped = clip_vector(Vec2(vector.x, vector.y), root['width'], root['height'])
            vector.x -= clipped.x; vector.y -= clipped.y
            root_x = target_x-vector.x; root_y = target_y-vector.y
            clipped = clip_vector(Vec2(vector.x, vector.y), target['width'], target['height'])
            vector.x -= clipped.x; vector.y -= clipped.y
            target_x = root_x+vector.x; target_y = root_y+vector.y
            x, y = target_x-root_x, target_y-root_y
            length += math.sqrt(x*x+y*y)
        return length


class EdgeLengthPositionOptimization:
    def __init__(self, state): self.state = state

    def evaluate(self, root):
        length = 0
        for edge in self.state.node_edges(root):
            target = self.state.owners[id(self.state.endpoint(edge, True))]
            target_x, target_y = target['x']+target['width']/2, target['y']+target['height']/2
            position = position_vector(self.state, target)
            root_x = root['x']+position.x+root['width']/2
            root_y = root['y']+position.y+root['height']  # Source uses full height here.
            x, y = target_x-root_x, target_y-root_y
            length += math.sqrt(x*x+y*y)
        return length


class CrossingMinimizationPosition:
    def __init__(self, state): self.state = state

    def _is_crossing(self, root, a, b):
        root_x = root['x']+root['width']/2
        root_y = root['x']+root['width']/2  # Literal source x/width for both axes.
        x_a, y_a = a['x']+a['width']/2, a['y']+a['height']/2
        position_a = position_vector(self.state, a)
        position_a.x += root_x; position_a.y += root_y
        slope_a = _div(y_a-position_a.y, x_a-position_a.x); intercept_a = y_a-slope_a*x_a
        x_b, y_b = b['x']+b['width']/2, b['y']+b['height']/2
        position_b = position_vector(self.state, b)
        position_b.x += root_x; position_b.y += root_y
        slope_b = _div(y_b-position_b.y, x_b-position_b.x); intercept_b = y_b-slope_b*x_b
        cut_x = _div(intercept_a-intercept_b, slope_b-slope_a)
        if position_a.x < cut_x and x_a < cut_x or cut_x < position_a.x and cut_x < x_a: return False
        if position_b.x < cut_x and x_b < cut_x or cut_x < position_b.x and cut_x < x_b: return False
        return True

    def evaluate(self, root):
        nodes = successors(self.state, root); crossings = 0
        for index, node in enumerate(nodes):
            for other in nodes[index+1:]:
                if self._is_crossing(root, node, other): crossings += 1
        return crossings


def create_sorter(state, strategy):
    if strategy == 'NONE': return None
    if strategy == 'ID': return IDSorter(state)
    if strategy == 'POLAR_COORDINATE': return PolarCoordinateSorter(state)
    raise ValueError('No implementation is available for the layout option '+str(strategy))


def create_optimizer(state, strategy):
    if strategy == 'NONE': return None
    if strategy == 'EDGE_LENGTH': return EdgeLengthOptimization(state)
    if strategy == 'EDGE_LENGTH_BY_POSITION': return EdgeLengthPositionOptimization(state)
    if strategy == 'CROSSING_MINIMIZATION_BY_POSITION': return CrossingMinimizationPosition(state)
    raise ValueError('No implementation is available for the layout option '+str(strategy))


class IdentitySet:
    """Native host mapping of the observed hash buckets and identity equality.

    Bucket first-insertion order and entries within each bucket are distinct.
    Existing signed32 collisions are preserved. Native identity allocation is
    an explicit host policy, not a claim to replay all GWT allocation sites.
    """
    def __init__(self, state, values=()):
        self.state = state; self.buckets = {}
        for value in values: self.add(value)

    def _code(self, value):
        method = getattr(self.state, 'identity_hash', None)
        code = method(value) if method is not None else _host_identity_hash(self.state, value)
        if type(code) is not int: raise TypeError('Native identity hash must be an integer')
        return (code+2147483648) % 4294967296-2147483648

    def add(self, value):
        code = self._code(value); bucket = self.buckets.setdefault(code, [])
        if not any(existing is value for existing in bucket): bucket.append(value)

    def contains(self, value):
        return any(existing is value for existing in self.buckets.get(self._code(value), []))

    def values(self): return [value for bucket in self.buckets.values() for value in bucket]


def successor_set(state, node):
    contained = IdentitySet(state, node.get('children', [])); result = IdentitySet(state)
    for edge in state.node_edges(node):
        source = state.endpoint(edge)
        if state.owners[id(source)] is not source: continue
        target = state.owners[id(state.endpoint(edge, True))]
        if not contained.contains(target): result.add(target)
    return result


def next_level_node_set(state, nodes):
    result = IdentitySet(state)
    for node in nodes:
        for child in successor_set(state, node).values(): result.add(child)
    return result


class RadiusExtension:
    """R07 shared original step motion and literal strict overlap predicates."""
    def __init__(self, state):
        self.state = state; self.root = None; self.step = 1; self.spacing = 0

    def contract_layer(self, nodes, contracting):
        for node in nodes:
            x_position = node['x']+node['width']/2; y_position = node['y']+node['height']/2
            root_x = self.root['x']+self.root['width']/2; root_y = self.root['y']+self.root['height']/2
            x, y = x_position-root_x, y_position-root_y
            length = math.sqrt(x*x+y*y)
            x *= _div(self.step, length); y *= _div(self.step, length)
            if contracting: x_position -= x; y_position -= y
            else: x_position += x; y_position += y
            node['x'] = x_position-node['width']/2; node['y'] = y_position-node['height']/2

    def overlap(self, a, b):
        x1, x2 = a['x']-self.spacing/2, b['x']-self.spacing/2
        y1, y2 = a['y']-self.spacing/2, b['y']-self.spacing/2
        width1, width2 = a['width']+self.spacing, b['width']+self.spacing
        height1, height2 = a['height']+self.spacing, b['height']+self.spacing
        if x1 < x2+width2 and x2 < x1 and y1 < y2+height2 and y2 < y1: return True
        if x2 < x1+width1 and x1 < x2 and y2 < y1+height1 and y1 < y2: return True
        if x1 < x2+width2 and x2 < x1 and y1 < y2 and y2 < y1+height1: return True
        if x2 < x1+width1 and x1 < x2 and y1 < y2+height2 and y2 < y1: return True
        return False

    def overlap_layer(self, nodes):
        if len(nodes) < 2: return False
        overlapping = False
        for index, node in enumerate(nodes):
            # Source uses bitwise-or accumulation: every pair is evaluated.
            overlapping = bool(overlapping | self.overlap(node, nodes[index+1] if index < len(nodes)-1 else nodes[0]))
        return overlapping

    def configure(self, graph):
        self.root = self.state.option(graph, 'root')
        self.sorter = create_sorter(self.state, self.state.option(graph, 'radial.sorter', 'NONE'))
        step = self.state.option(graph, 'radial.compactionStepSize', 1)
        if step is not None: self.step = step
        self.spacing = self.state.option(graph, 'spacing.nodeNode', 20)


class RadialCompaction(RadiusExtension):
    def __init__(self, state):
        super().__init__(state); self.last_radius = 0

    def radius(self, node):
        # Literal top-left positions, not center-based radial distance.
        x, y = node['x']-self.root['x'], node['y']-self.root['y']
        return math.sqrt(x*x+y*y)

    def overlapping(self, nodes):
        if self.overlap_layer(nodes): return True
        for node in nodes:
            if self.overlap(node, tree_parent(self.state, node)): return True
            if self.radius(node)-self.spacing <= self.last_radius: return True
        return False

    def compact(self, graph):
        self.configure(graph); nodes = successors(self.state, self.root)
        if self.sorter is not None: self.sorter.sort(nodes)
        while nodes:
            overlapping = self.overlapping(nodes); contracted = False
            while not overlapping:
                self.contract_layer(nodes, True); contracted = True
                overlapping = self.overlapping(nodes)
            if contracted: self.contract_layer(nodes, False)
            following = next_level_nodes(self.state, nodes)
            if self.sorter is not None: self.sorter.sort(following)
            self.last_radius = self.radius(nodes[0]); nodes = following


class AnnulusWedgeCompaction(RadiusExtension):
    def __init__(self, state):
        super().__init__(state); self.left_contour = {}; self.right_contour = {}

    def _put(self, contour, parent, node):
        self.state.identity_hash(parent) if hasattr(self.state, 'identity_hash') else _host_identity_hash(self.state, parent)
        if id(parent) not in contour: contour[id(parent)] = IdentitySet(self.state)
        contour[id(parent)].add(node)

    def construct_contour(self, nodes):
        for node in nodes:
            self._put(self.left_contour, node, node); self._put(self.right_contour, node, node)
            children = successors(self.state, node)
            if children:
                if self.sorter is not None: self.sorter.sort(children)
                self._put(self.left_contour, node, children[0]); self._put(self.right_contour, node, children[-1])
                while next_level_nodes(self.state, children):
                    children = next_level_nodes(self.state, children)
                    if self.sorter is not None: self.sorter.sort(children)
                    self._put(self.left_contour, node, children[0]); self._put(self.right_contour, node, children[-1])

    def contour_overlap(self, parent, node, left):
        contour = self.left_contour if left else self.right_contour
        for other in contour[id(parent)].values():
            if self.overlap(node, other): return True
        return False

    def overlapping(self, previous, left_parent, right_parent, nodes):
        if self.sorter is not None: self.sorter.sort(nodes)
        if self.contour_overlap(left_parent, nodes[0], False): return True
        if self.contour_overlap(right_parent, nodes[-1], True): return True
        if self.overlap_layer(nodes): return True
        for node in nodes:
            for predecessor in previous:
                if self.overlap(node, predecessor): return True
        return False

    def contract_wedge(self, previous, left_parent, right_parent, nodes):
        while nodes:
            overlapping = self.overlapping(previous, left_parent, right_parent, nodes); contracted = False
            while not overlapping:
                self.contract_layer(nodes, True); contracted = True
                overlapping = self.overlapping(previous, left_parent, right_parent, nodes)
            if contracted: self.contract_layer(nodes, False)
            following = next_level_nodes(self.state, nodes)
            if following and self.sorter is not None: self.sorter.sort(following)
            previous, nodes = nodes, following

    def compact(self, graph):
        self.configure(graph); nodes = successors(self.state, self.root)
        if self.sorter is not None: self.sorter.sort(nodes)
        self.construct_contour(nodes)
        for repeat in range(2):
            for index, node in enumerate(nodes):
                right = nodes[index+1] if index < len(nodes)-1 else nodes[0]
                left = nodes[-1] if index == 0 else nodes[index-1]
                self.contract_wedge([self.root], left, right, [node])


def compact_graph(state, graph, monitor=None):
    if monitor is not None: monitor.begin('General Compactor', 1)
    strategy = state.option(graph, 'radial.compactor', 'NONE')
    if strategy == 'RADIAL_COMPACTION': compactor = RadialCompaction(state)
    elif strategy == 'WEDGE_COMPACTION': compactor = AnnulusWedgeCompaction(state)
    elif strategy == 'NONE': raise TypeError('The radial compactor is null')
    else: raise ValueError('No implementation is available for the layout option '+str(strategy))
    compactor.compact(graph)


def remove_overlaps(state, graph, monitor=None):
    if monitor is not None: monitor.begin('Remove overlaps', 1)
    _log_graph(monitor, graph, 'Before')
    extension = RadiusExtension(state); extension.root = state.option(graph, 'root')
    extension.spacing = state.option(graph, 'spacing.nodeNode', 20)
    sorter = create_sorter(state, state.option(graph, 'radial.sorter', 'NONE'))
    nodes = successors(state, extension.root)
    while nodes:
        old_positions = [(node['x'], node['y']) for node in nodes]
        _log_graph(monitor, graph, 'Before removing overlaps')
        while extension.overlap_layer(nodes): extension.contract_layer(nodes, False)
        _log_graph(monitor, graph, 'After removing overlaps')
        moved_x, moved_y = nodes[0]['x']-old_positions[0][0], nodes[0]['y']-old_positions[0][1]
        distance = math.sqrt(moved_x*moved_x+moved_y*moved_y)
        next_set = next_level_node_set(state, nodes)
        following = next_set.values()
        if following:
            for node in following:
                root_x = extension.root['x']+extension.root['width']/2
                root_y = extension.root['y']+extension.root['height']/2
                x = node['x']+node['width']/2-root_x; y = node['y']+node['height']/2-root_y
                length = math.sqrt(x*x+y*y)
                node['x'] = node['x']+_div(x, length)*distance
                node['y'] = node['y']+_div(y, length)*distance
            _log_graph(monitor, graph, 'Child movement 1')
        # The original sorted copy is discarded. It can still initialize and
        # mutate a real sorter; recursion constructs another list from the set.
        if sorter is not None: sorter.sort(next_set.values())
        nodes = next_set.values()
    _log_graph(monitor, graph, 'After')


def _insets(value, default):
    if value is None: return _padding(default)
    if hasattr(value, 'top') and hasattr(value, 'left'):
        return {name: getattr(value, name) for name in ('top', 'right', 'bottom', 'left')}
    return _padding(value)


def _node_margin(state, node):
    if hasattr(state, 'read_native_property'):
        from .layered.graph import Insets
        value = state.read_native_property(node, 'margins', Insets())
        return _insets(value, 0)
    return _insets(state.option(node, 'margins'), 0)


def calculate_graph_size(state, graph, monitor=None):
    """R05 original margin bounds and literal center-on-root adjustments."""
    if monitor is not None: monitor.begin('Calculate Graph Size', 1)
    _log_graph(monitor, graph, 'Before')
    minimum_x = minimum_y = 1.7976931348623157e308
    maximum_x = maximum_y = 5e-324  # Source positive Double.MIN_VALUE.
    for node in graph.get('children', []):
        margin = _node_margin(state, node)
        minimum_x = -_maximum(-minimum_x, -(node['x']-margin['left']))
        minimum_y = -_maximum(-minimum_y, -(node['y']-margin['top']))
        maximum_x = _maximum(maximum_x, node['x']+node['width']+margin['right'])
        maximum_y = _maximum(maximum_y, node['y']+node['height']+margin['bottom'])
    padding = _owner_padding(state, graph, 12)
    offset_x, offset_y = minimum_x-padding['left'], minimum_y-padding['top']
    width = maximum_x-minimum_x+(padding['left']+padding['right'])
    height = maximum_y-minimum_y+(padding['top']+padding['bottom'])
    if state.option(graph, 'radial.centerOnRoot', False):
        root = state.option(graph, 'root'); margin = _node_margin(state, root)
        root_x = root['x']+root['width']/2+(margin['left']+margin['right'])/2-offset_x
        root_y = root['y']+root['height']/2+(margin['top']+margin['bottom'])/2-offset_y
        dx, dy = width-root_x, height-root_y
        if dx < width/2:
            additional_x = dx-root_x; width += additional_x; offset_x -= additional_x
        else:
            additional_x = root_x-dx; width += additional_x
        if dy < height/2:
            additional_y = dy-root_y; height += additional_y; offset_y -= additional_y
        else:
            additional_y = root_y-dy; height += additional_y
    for node in graph.get('children', []):
        node['x'] = node['x']-offset_x; node['y'] = node['y']-offset_y
    if not state.option(graph, 'nodeSize.fixedGraphSize', False): graph.update(width=width, height=height)
    state.computed_options.setdefault(id(graph), {}).update(
        childAreaWidth=width-(padding['left']+padding['right']), childAreaHeight=height-(padding['top']+padding['bottom']))
    _log_graph(monitor, graph, 'After')


def rotate_graph(state, graph, monitor=None):
    if monitor is not None: monitor.begin("General 'Rotator", 1)
    angle = state.option(graph, 'radial.rotation.targetAngle', 0)
    if state.option(graph, 'radial.rotation.computeAdditionalWedgeSpace', False):
        root = state.option(graph, 'root'); outgoing = state.incidence(root)
        last = state.endpoint(outgoing[-1], True); first = state.endpoint(outgoing[0], True)
        if state.owners[id(first)] is not first or state.owners[id(last)] is not last:
            raise TypeError('The additional-wedge target is not an ElkNode')
        last_x, last_y = last['x']+last['width']/2, last['y']+last['height']/2
        first_x, first_y = first['x']+first['width']/2, first['y']+first['height']/2
        alpha = angle
        if alpha <= 0: alpha += 6.283185307179586
        wedge = _acos(_div(last_x*first_x+last_y*first_y,
                           math.sqrt(last_x*last_x+last_y*last_y)*math.sqrt(first_x*first_x+first_y*first_y)))
        if wedge <= 0: wedge += 6.283185307179586
        alignment = math.atan2(last_y, last_x)
        if alignment <= 0: alignment += 6.283185307179586
        angle = 3.141592653589793-(alignment-alpha+wedge/2)
    for node in graph.get('children', []):
        x, y = node['x']+node['width']/2, node['y']+node['height']/2
        new_x = x*_cos(angle)-y*_sin(angle)
        y = x*_sin(angle)+y*_cos(angle); x = new_x
        node['x'] = x-node['width']/2; node['y'] = y-node['height']/2


def _first_section(edge):
    sections = edge.setdefault('sections', [])
    if not sections: sections.append({})
    section = sections[0]
    section.update(startPoint={'x': 0, 'y': 0}, endPoint={'x': 0, 'y': 0}, bendPoints=[])
    del sections[1:]
    return section


def route_edges(state, graph, monitor=None):
    """R13 actual recursive order, port-source exclusion and both clips."""
    if monitor is not None: monitor.begin('Straight Line Edge Routing', 1)
    _log_graph(monitor, graph, 'Before')
    root = state.option(graph, 'root'); work = [iter(state.node_edges(root))]
    from .random import _hierarchical
    while work:
        try: edge = next(work[-1])
        except StopIteration:
            work.pop(); continue
        source = state.endpoint(edge)
        if state.owners[id(source)] is not source: continue
        target = state.owners[id(state.endpoint(edge, True))]
        if _hierarchical(state, edge): continue
        # The current recursion node can differ from first source for an
        # admitted multi-source edge. Track it alongside the edge iterator.
        current = root if len(work) == 1 else work[-1].node
        source_x, source_y = current['x']+current['width']/2, current['y']+current['height']/2
        target_x, target_y = target['x']+target['width']/2, target['y']+target['height']/2
        vector = Vec2(target_x-source_x, target_y-source_y)
        clipped = clip_vector(Vec2(vector.x, vector.y), current['width'], current['height'])
        vector.x -= clipped.x; vector.y -= clipped.y
        source_x = target_x-vector.x; source_y = target_y-vector.y
        clipped = clip_vector(Vec2(vector.x, vector.y), target['width'], target['height'])
        vector.x -= clipped.x; vector.y -= clipped.y
        target_x = source_x+vector.x; target_y = source_y+vector.y
        section = _first_section(edge)
        section['startPoint'] = {'x': source_x, 'y': source_y}; section['endPoint'] = {'x': target_x, 'y': target_y}
        work.append(_NodeEdgeIterator(target, state.node_edges(target)))
    _log_graph(monitor, graph, 'After')


class _NodeEdgeIterator:
    def __init__(self, node, edges): self.node = node; self.iterator = iter(edges)
    def __iter__(self): return self
    def __next__(self): return next(self.iterator)


def outgoing_edge_angles(state, graph, monitor=None):
    # R06 intentionally has neither monitor begin nor done.
    root = state.option(graph, 'root')
    for edge in state.incidence(root):
        section = edge['sections'][0]
        start, end = section['startPoint'], section['endPoint']
        angle = math.atan2(end['y']-start['y'], end['x']-start['x'])
        target = state.endpoint(edge, True)
        state.computed_options.setdefault(id(target), {})['radial.rotation.targetAngle'] = angle


def _assemble(state, graph):
    processors = [eades_layout, remove_overlaps]
    if state.option(graph, 'radial.compactor', 'NONE') != 'NONE': processors.append(compact_graph)
    if state.option(graph, 'radial.rotate', False): processors.append(rotate_graph)
    processors.extend([calculate_graph_size, route_edges])
    if state.option(graph, 'radial.rotation.outgoingEdgeAngles', False): processors.append(outgoing_edge_angles)
    return processors


def _layout(state, node, monitor=None):
    """Run the full radial pipeline with the shared NodeMicroLayout hook."""
    initial = _assemble(state, node)
    if monitor is not None: monitor.begin('Radial layout', len(initial))
    if not state.option(node, 'omitNodeMicroLayout', False):
        state.node_micro_layout(node)
    root = find_root(state, node)
    if root is not None: state.computed_options.setdefault(id(node), {})['root'] = root
    else:
        state.computed_options.setdefault(id(node), {}).pop('root', None)
        raise ValueError('The given graph is not a tree!')
    radius = state.option(node, 'radial.radius', 0)
    if radius == 0: radius = find_largest_node_in_graph(node)
    state.computed_options.setdefault(id(node), {})['radial.radius'] = radius
    for processor in _assemble(state, node):
        phase_monitor = monitor.sub_task(1) if monitor is not None else None
        processor(state, node, phase_monitor)
    if monitor is not None: monitor.done()
    return node


def layout_radial(graph, options=None, *, monitor=None):
    from ..execution.json_transfer import JsonLayoutSession
    state = JsonLayoutSession(graph, options)
    _layout(state, state.graph, monitor)
    return state.export()
