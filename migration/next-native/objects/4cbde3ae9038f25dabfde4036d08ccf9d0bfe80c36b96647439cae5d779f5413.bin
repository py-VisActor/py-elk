# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Fixed elkjs 0.12.1 worker F01-F13, reviewed E18 source closures.
# SHA256 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Exact external Java build identity remains unresolved.
"""Native Force particles and their ordered, source-specific graph.

Only independently reviewed closures are implemented. This model is shared by
Force and Stress; it does not substitute a layered or tree layout backend.
"""
from __future__ import annotations

from .layered.graph import Vec2
from .radial import clip_vector, _first_section, _maximum
from .fixed import _padding, _owner_padding, _resize
from .fixed import _div
from .random import _hierarchical
from .layered.components import _double_compare
from .layered.ports import _source_sort
import math


class _Properties:
    def __init__(self, state=None, origin=None):
        self.state = state
        self.origin = origin
        self.properties = {}
        self.integer_box_identities = {}
        if state is not None and origin is not None and hasattr(state, 'property_snapshot'):
            snapshot = state.property_snapshot(origin)
            self.properties.update(snapshot.values)
            self.integer_box_identities.update(snapshot.integer_boxes)

    def option(self, name, default=None):
        if name in self.properties and self.properties[name] is not None:
            return self.properties[name]
        if name in self.properties:
            return default
        if self.origin is not None:
            return self.state.option(self.origin, name, default)
        return default

    def has_option(self, name):
        return (name in self.properties or
                (self.origin is not None and self.state.has_option(self.origin, name)))


class FParticle(_Properties):
    def __init__(self, state=None, origin=None):
        super().__init__(state, origin)
        self.displacement = Vec2()
        self.position = Vec2()
        self.size = Vec2()


class FNode(FParticle):
    def __init__(self, label='', state=None, origin=None):
        super().__init__(state, origin)
        self.label = label
        self.id = 0

    def __str__(self):
        return 'n_' + (self.label if self.label else str(self.id))


class FEdge(_Properties):
    def __init__(self, state=None, origin=None):
        super().__init__(state, origin)
        self.source = None
        self.target = None
        self.bendpoints = []
        self.labels = []

    def distribute_bendpoints(self):
        count = len(self.bendpoints)
        if count:
            source, target = self.source.position, self.target.position
            # Source scales by the reciprocal, rather than dividing each axis.
            scale = 1 / (count + 1)
            dx, dy = (target.x-source.x)*scale, (target.y-source.y)*scale
            x, y = source.x, source.y
            for bendpoint in self.bendpoints:
                bendpoint.position.x, bendpoint.position.y = x+dx, y+dy
                x += dx
                y += dy

    def source_point(self):
        source, target = self.source.position, self.target.position
        result = clip_vector(Vec2(target.x-source.x, target.y-source.y),
                             self.source.size.x, self.source.size.y)
        result.x += source.x
        result.y += source.y
        return result

    def target_point(self):
        source, target = self.source.position, self.target.position
        result = clip_vector(Vec2(source.x-target.x, source.y-target.y),
                             self.target.size.x, self.target.size.y)
        result.x += target.x
        result.y += target.y
        return result

    def __str__(self):
        return str(self.source) + '->' + str(self.target)


class FBendpoint(FParticle):
    def __init__(self, edge):
        super().__init__(edge.state)
        self.edge = edge
        edge.bendpoints.append(self)


class FLabel(FParticle):
    def __init__(self, edge, text='', origin=None):
        super().__init__(edge.state, origin)
        self.edge = edge
        self.text = text
        edge.labels.append(self)

    def refresh_position(self):
        source, target = self.edge.source.position, self.edge.target.position
        pos = self.position
        if self.option('edgeLabels.inline', False):
            pos.x = source.x + (target.x-source.x)*0.5 - self.size.x*0.5
            pos.y = source.y + (target.y-source.y)*0.5 - self.size.y*0.5
        else:
            spacing = self.edge.option('spacing.edgeLabel', 5)
            if source.x >= target.x:
                pos.x = target.x + (source.x-target.x)/2 + spacing
                if source.y >= target.y:
                    pos.y = target.y + (source.y-target.y)/2 - spacing - self.size.y
                else:
                    pos.y = source.y + (target.y-source.y)/2 + spacing
            else:
                pos.x = source.x + (target.x-source.x)/2 + spacing
                if source.y >= target.y:
                    pos.y = target.y + (source.y-target.y)/2 - spacing - self.size.y
                else:
                    pos.y = source.y + (target.y-source.y)/2 - spacing - self.size.y


class FGraph(_Properties):
    def __init__(self, state=None, origin=None):
        super().__init__(state, origin)
        self.nodes = []
        self.edges = []
        self.labels = []
        self.bend_points = []
        self.adjacency = None

    def particles(self):
        yield from self.nodes
        yield from self.labels
        yield from self.bend_points

    def calc_adjacency(self):
        count = len(self.nodes)
        self.adjacency = [[0 for _ in range(count)] for _ in range(count)]
        for edge in self.edges:
            self.adjacency[edge.source.id][edge.target.id] += edge.option('priority', 1)

    def get_connection(self, first, second):
        if isinstance(first, FNode) and isinstance(second, FNode):
            return self.adjacency[first.id][second.id] + self.adjacency[second.id][first.id]
        if isinstance(first, FBendpoint) and isinstance(second, FBendpoint):
            if first.edge is second.edge:
                return second.edge.option('priority', 1)
        return 0


def import_graph(state, raw):
    """F03 actual centers, node/port encounter order and original filtering."""
    graph = FGraph(state, raw)
    mapped = {}
    for index, child in enumerate(raw.get('children', [])):
        labels = child.get('labels', [])
        node = FNode(labels[0].get('text') if labels else '', state, child)
        node.id = index
        node.position.x = child['x'] + child['width']/2
        node.position.y = child['y'] + child['height']/2
        node.size.x, node.size.y = _maximum(child['width'], 1), _maximum(child['height'], 1)
        graph.nodes.append(node)
        mapped[id(child)] = node
        # The source's UNDEFINED -> FREE local variable is dead, not a setter.
    for child in raw.get('children', []):
        for edge in state.node_edges(child):
            if len(edge.get('sources', [])) > 1 or len(edge.get('targets', [])) > 1:
                raise ValueError('Graph must not contain hyperedges.')
            if _hierarchical(state, edge):
                continue
            target = state.owners[id(state.endpoint(edge, True))]
            if child is target:
                continue
            new_edge = FEdge(state, edge)
            new_edge.source, new_edge.target = mapped[id(child)], mapped[id(target)]
            graph.edges.append(new_edge)
            for label in edge.get('labels', []):
                new_label = FLabel(new_edge, label.get('text'), label)
                new_label.size.x = _maximum(label['width'], 1)
                new_label.size.y = _maximum(label['height'], 1)
                new_label.refresh_position()
                graph.labels.append(new_label)
    return graph


def _minimum(left, right):
    return -_maximum(-left, -right)


def _bounds(nodes):
    minx = miny = 2147483647
    maxx = maxy = -2147483648
    for node in nodes:
        minx = _minimum(minx, node.position.x-node.size.x/2)
        miny = _minimum(miny, node.position.y-node.size.y/2)
        maxx = _maximum(maxx, node.position.x+node.size.x/2)
        maxy = _maximum(maxy, node.position.y+node.size.y/2)
    return Vec2(minx, miny), Vec2(maxx, maxy)


def apply_layout(graph):
    """F03 transfer bounds exclude labels and use original, unclamped node WH."""
    state, raw = graph.state, graph.origin
    if raw is None:
        raise ValueError('The Force graph has no original layout graph')
    upper, lower = _bounds([*graph.nodes, *graph.bend_points])
    padding = _owner_padding(state, raw, 50)
    dx, dy = padding['left']-upper.x, padding['top']-upper.y
    for node in graph.nodes:
        if node.origin is not None:
            node.origin['x'] = node.position.x+dx-node.origin['width']/2
            node.origin['y'] = node.position.y+dy-node.origin['height']/2
    for edge in graph.edges:
        section = _first_section(edge.origin)
        source, target = edge.source_point(), edge.target_point()
        section['startPoint'] = {'x': source.x+dx, 'y': source.y+dy}
        section['endPoint'] = {'x': target.x+dx, 'y': target.y+dy}
        section['bendPoints'] = [{'x': bend.position.x+dx, 'y': bend.position.y+dy}
                                for bend in edge.bendpoints]
    for label in graph.labels:
        label.origin['x'], label.origin['y'] = label.position.x+dx, label.position.y+dy
    width = lower.x-upper.x + (padding['left']+padding['right'])
    height = lower.y-upper.y + (padding['top']+padding['bottom'])
    if not state.option(raw, 'nodeSize.fixedGraphSize', False):
        _resize(state, raw, width, height, False, True)
    state.computed_options.setdefault(id(raw), {}).update(
        childAreaWidth=width-(padding['left']+padding['right']),
        childAreaHeight=height-(padding['top']+padding['bottom']))


def split_components(graph):
    """F04 iterative transcription of the source-specific last-node DFS."""
    if graph.option('separateConnectedComponents', True) is False:
        return [graph]
    visited = [False for _ in graph.nodes]
    incidence = [[] for _ in graph.nodes]
    for edge in graph.edges:
        incidence[edge.source.id].append(edge)
        incidence[edge.target.id].append(edge)
    components = []
    for initial in graph.nodes:
        if visited[initial.id]:
            continue
        component = FGraph(graph.state, graph.origin)
        component.properties.update(graph.properties)  # RANDOM remains shared.
        work = [('visit', initial, None)]
        while work:
            action, value, last = work.pop()
            if action == 'append':
                component.edges.append(value)
                component.labels.extend(value.labels)
            elif action == 'edge':
                edge, node = value, last[0]
                previous = last[1]
                if edge.target is previous or edge.source is previous:
                    continue
                work.append(('append', edge, None))
                if edge.target is not node:
                    work.append(('visit', edge.target, node))
                if edge.source is not node:
                    work.append(('visit', edge.source, node))
            elif not visited[value.id]:
                visited[value.id] = True
                component.nodes.append(value)
                for edge in reversed(incidence[value.id]):
                    work.append(('edge', edge, (value, last)))
        components.append(component)
    if len(components) > 1:
        for component in components:
            for index, node in enumerate(component.nodes):
                node.id = index
    return components


def _move_graph(destination, source, x, y):
    upper = source.properties['BB_UPLEFT']
    dx, dy = x-upper.x, y-upper.y
    for node in source.nodes:
        node.position.x += dx
        node.position.y += dy
        destination.nodes.append(node)
    for edge in source.edges:
        for bendpoint in edge.bendpoints:
            bendpoint.position.x += dx
            bendpoint.position.y += dy
        destination.edges.append(edge)
    for label in source.labels:
        label.position.x += dx
        label.position.y += dy
        destination.labels.append(label)
    # Original move does not copy graph.bendPoints, even though it moves edges.


def recombine_components(components):
    if len(components) == 1:
        return components[0]
    if not components:
        return FGraph()
    for graph in components:
        priority = 0
        for node in graph.nodes:
            priority += node.option('priority', 1)
        graph.properties['priority'] = priority
        graph.properties['BB_UPLEFT'], graph.properties['BB_LOWRIGHT'] = _bounds(graph.nodes)

    def size(graph):
        upper, lower = graph.properties['BB_UPLEFT'], graph.properties['BB_LOWRIGHT']
        return Vec2(lower.x-upper.x, lower.y-upper.y)

    def compare(first, second):
        priority = second.option('priority', 1)-first.option('priority', 1)
        if priority == 0:
            one, two = size(first), size(second)
            return _double_compare(one.x*one.y, two.x*two.y)
        return priority

    _source_sort(components, compare)
    first = components[0]
    result = FGraph(first.state, first.origin)
    result.properties.update(first.properties)
    max_row_width = total_area = 0
    for graph in components:
        extent = size(graph)
        max_row_width = _maximum(max_row_width, extent.x)
        total_area += extent.x*extent.y
    square_root = math.sqrt(total_area) if total_area >= 0 else math.nan
    max_row_width = _maximum(max_row_width, square_root*result.option('aspectRatio', 1.600000023841858))
    spacing = result.option('spacing.nodeNode', 80)
    xpos = ypos = highest = 0
    for graph in components:
        extent = size(graph)
        if xpos+extent.x > max_row_width:
            xpos = 0
            ypos += highest+spacing
            highest = 0
        _move_graph(result, graph, xpos, ypos)
        highest = _maximum(highest, extent.y)
        xpos += extent.x+spacing
    return result


def _length(vector):
    return math.sqrt(vector.x*vector.x + vector.y*vector.y)


def _log(value):
    # Original host adapter for JS Math.log's zero/domain behavior.
    if value == 0:
        return -math.inf
    if value < 0:
        return math.nan
    return math.log(value)


def avoid_same_position(random, first, second):
    """F11 source mutates real positions here, during pair accumulation."""
    pu, pv = first.position, second.position
    while pu.x-pv.x == 0 and pu.y-pv.y == 0:
        tried_for_bendpoints = False
        if isinstance(first, FBendpoint) and isinstance(second, FBendpoint) and not tried_for_bendpoints:
            edge = first.edge
            target, source = edge.target_point(), edge.source_point()
            uv = Vec2(target.x-source.x, target.y-source.y)
            length = _length(uv)
            pu.x += _div(uv.x, length)*2
            pu.y += _div(-uv.y, length)*2
            edge = second.edge
            target, source = edge.target_point(), edge.source_point()
            vv = Vec2(target.x-source.x, target.y-source.y)
            scale = -2 if uv is vv else 2  # Fresh source vectors use identity.
            length = _length(vv)
            pu.x += _div(vv.x, length)*scale
            pu.y += -_div(vv.y, length)*scale
            tried_for_bendpoints = True
        else:
            pu.x += random.next_double()-0.5
            pu.y += random.next_double()-0.5
            pv.x += random.next_double()-0.5
            pv.y += random.next_double()-0.5


class AbstractForceModel:
    def initialize(self, graph):
        self.graph = graph
        self.random = graph.properties['RANDOM']
        graph.calc_adjacency()
        self.displacement_bound = max(len(graph.nodes)*16+len(graph.edges), 256)
        if not graph.option('interactive', False):
            scale = len(graph.nodes)
            for node in graph.nodes:
                node.position.x = self.random.next_double()*scale
                node.position.y = self.random.next_double()*scale
        for edge in graph.edges:
            count = edge.option('force.repulsivePower', 0)
            if count > 0:
                for _ in range(count):
                    graph.bend_points.append(FBendpoint(edge))
                edge.distribute_bendpoints()

    def iteration_done(self):
        for edge in self.graph.edges:
            for label in edge.labels:
                label.refresh_position()
            edge.distribute_bendpoints()

    def layout(self, graph, monitor=None):
        if monitor is not None:
            monitor.begin('Component Layout', 1)
        self.initialize(graph)
        iterations = 0
        while self.more_iterations(iterations):
            canceled = getattr(monitor, 'is_canceled', None)
            if canceled is not None and canceled():
                break
            self.iteration_done()
            for forcee in graph.particles():
                for forcer in graph.particles():
                    if forcer is not forcee:
                        displacement = self.calc_displacement(forcer, forcee)
                        if displacement is not None:
                            forcee.displacement.x += displacement.x
                            forcee.displacement.y += displacement.y
            for particle in graph.particles():
                delta = particle.displacement
                low, high = -self.displacement_bound, self.displacement_bound
                if delta.x < low: delta.x = low
                elif delta.x > high: delta.x = high
                if delta.y < low: delta.y = low
                elif delta.y > high: delta.y = high
                particle.position.x += delta.x
                particle.position.y += delta.y
                delta.x = delta.y = 0
            iterations += 1
        if monitor is not None:
            monitor.done()


class EadesModel(AbstractForceModel):
    def initialize(self, graph):
        super().initialize(graph)
        self.max_iterations = graph.option('force.iterations', 300)
        self.spring_length = graph.option('spacing.nodeNode', 80)
        self.repulsion_factor = graph.option('force.repulsion', 5)

    def calc_displacement(self, forcer, forcee):
        avoid_same_position(self.random, forcer, forcee)
        displacement = Vec2(forcee.position.x-forcer.position.x, forcee.position.y-forcer.position.y)
        length = _length(displacement)
        distance = _maximum(0, length-_length(forcer.size)/2-_length(forcee.size)/2)
        connection = self.graph.get_connection(forcer, forcee)
        if connection > 0:
            attractive = _log(_div(distance, self.spring_length)) if distance > 0 else -100
            force = -attractive*connection
        else:
            force = (_div(self.repulsion_factor, distance*distance) if distance > 0
                     else self.repulsion_factor*100)*forcer.option('priority', 1)
        scale = _div(force, length)
        displacement.x *= scale
        displacement.y *= scale
        return displacement

    def more_iterations(self, count):
        return count < self.max_iterations


class FruchtermanReingoldModel(AbstractForceModel):
    def initialize(self, graph):
        super().initialize(graph)
        self.temperature = graph.option('force.temperature', 0.001)
        self.threshold = _div(self.temperature, graph.option('force.iterations', 300))
        total_width = total_height = 0
        for node in graph.nodes:
            total_width += node.size.x
            total_height += node.size.y
        area = total_width*total_height
        scale = graph.option('spacing.nodeNode', 80)*0.01
        ratio = _div(area, 2*len(graph.nodes))
        self.k = (math.sqrt(ratio) if ratio >= 0 else math.nan)*scale

    def iteration_done(self):
        super().iteration_done()
        self.temperature -= self.threshold

    def calc_displacement(self, forcer, forcee):
        avoid_same_position(self.random, forcer, forcee)
        displacement = Vec2(forcee.position.x-forcer.position.x, forcee.position.y-forcer.position.y)
        length = _length(displacement)
        distance = _maximum(0, length-_length(forcer.size)/2-_length(forcee.size)/2)
        force = (_div(self.k*self.k, distance) if distance > 0 else self.k*self.k*100)*forcer.option('priority', 1)
        connection = self.graph.get_connection(forcer, forcee)
        if connection > 0:
            force -= _div(distance*distance, self.k)*connection
        scale = _div(force*self.temperature, length)
        displacement.x *= scale
        displacement.y *= scale
        return displacement

    def more_iterations(self, count):
        return self.temperature > 0


def _layout(state, node, monitor=None):
    """F05 real Force provider on the caller's persistent native session."""
    if monitor is not None:
        monitor.begin('ELK Force', 1)
    if not state.option(node, 'omitNodeMicroLayout', False):
        state.node_micro_layout(node)
    graph = import_graph(state, node)
    # Approved shared native Random implementation and process seed-zero path;
    # these retain their separate Apache attribution, not a second seedcounter.
    from .layered.phases import JavaRandom
    from .random import _unseeded_random
    seed = graph.option('randomSeed', 1)
    graph.properties['RANDOM'] = (_unseeded_random() if seed == 0
                                  else JavaRandom(1 if seed is None else seed))
    strategy = graph.option('force.model', 'FRUCHTERMAN_REINGOLD')
    if strategy == 'EADES':
        model = EadesModel()
    elif strategy == 'FRUCHTERMAN_REINGOLD':
        model = FruchtermanReingoldModel()
    else:
        raise ValueError('Unknown Force model: '+str(strategy))
    components = split_components(graph)
    for component in components:
        child = monitor.sub_task(1/len(components)) if monitor is not None else None
        model.layout(component, child)
    apply_layout(recombine_components(components))
    if monitor is not None:
        monitor.done()


def layout_force(graph, options=None, *, monitor=None):
    from ..execution.json_transfer import JsonLayoutSession
    state = JsonLayoutSession(graph, options)
    _layout(state, state.graph, monitor)
    return state.export()
