# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Mechanical port from elkjs 0.12.1 generated lib/elk-worker.js.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Source/guard maps: references/e05-source-components-B.json,
# phase:LAYER_SWEEP_BARYCENTER and phase:LAYER_SWEEP_GREEDY_SWITCH.
# E06 expanded work guards: references/e06-source-components-R.json; NOTICE-E06.md.
# Exact external Java build is unresolved. See pyelk/_licenses/NOTICE.md.
"""Reviewed flat proper-DAG LayerSweep kernels and source-owned scratch.

No metadata/reference files are read at runtime. The entry validates the direct
work representation; upstream splitting and raw public admission are separate
obligations. Guarded-out in-layer, north/south and hierarchical counter terms
are zero, while their actual default-property writes and live scratch remain.
"""
from functools import cmp_to_key
import math

from ..._errors import UnsupportedFeatureError


def _outside(message):
    raise UnsupportedFeatureError('UNSUPPORTED_PHASE_INPUT', '', message)


def _double_compare(left, right):
    if left < right:
        return -1
    if left > right:
        return 1
    if left == 0 and right == 0:
        a, b = math.copysign(1, left), math.copysign(1, right)
        return (a > b) - (a < b)
    return 0


def _side(node, side):
    return [port for port in node.ports if port.side == side]


def _top_down_ports(node, side):
    ports = _side(node, side)
    return list(reversed(ports)) if side == 'WEST' else ports


def get_successor_constraints(node):
    """Property default ArrayList clone/store, including existing empty lists."""
    value = node.properties.get('IN_LAYER_SUCCESSOR_CONSTRAINTS')
    if value is None:
        value = []
        node.properties['IN_LAYER_SUCCESSOR_CONSTRAINTS'] = value
    return value


def _guard(graph, strategy, *, allow_detached_north=False):
    from .phases import JavaRandom
    if strategy not in ('BARYCENTER', 'TWO_SIDED_GREEDY_SWITCH'):
        _outside('Only the two reviewed default LayerSweep strategies are supported')
    if not isinstance(graph.random, JavaRandom) or graph.layerless_nodes or len(graph.layers) > 8:
        _outside('LayerSweep needs a verified per-call stream and at most eight prepared layers')
    if getattr(graph, 'parent_node', None) is not None or graph.properties.get('HIERARCHY_HANDLING', 'SEPARATE_CHILDREN') == 'INCLUDE_CHILDREN':
        _outside('Hierarchical crossing branches are outside the flat work graph')
    for key, default in [('CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER', False),
                         ('IN_LAYER_SUCCESSOR_CONSTRAINTS_BETWEEN_NON_DUMMIES', False),
                         ('CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE', 0),
                         ('CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE', 0),
                         ('CONSIDER_MODEL_ORDER_STRATEGY', 'NONE'), ('THOROUGHNESS', 7),
                         ('FIRST_TRY_WITH_INITIAL_ORDER', False), ('SECOND_TRY_WITH_INITIAL_ORDER', False)]:
        value = graph.properties.get(key, default)
        if type(value) is not type(default) or value != default:
            _outside('Non-default crossing/model-order options require a separate source review')
    nodes = [node for layer in graph.layers for node in layer.nodes]
    if len(nodes) > 176 or len(set(nodes)) != len(nodes) or sum(node.type == 'NORMAL' for node in nodes) > 8:
        _outside('LayerSweep work graph exceeds the approved node bound')
    if any(not layer.nodes or layer.graph is not graph for layer in graph.layers):
        _outside('Prepared layers must be nonempty and belong to the work graph')
    layer_index = {layer: i for i, layer in enumerate(graph.layers)}
    node_set, ports, edges = set(nodes), set(), set()
    for node in nodes:
        if node.graph is not graph or node.layer not in layer_index or node not in node.layer.nodes or node.type not in ('NORMAL', 'LONG_EDGE'):
            _outside('Layer membership or node type is outside the proper DAG')
        if getattr(node, 'nested_graph', None) is not None:
            _outside('Nested work graphs are outside this LayerSweep source slice')
        constraints = node.properties.get('IN_LAYER_SUCCESSOR_CONSTRAINTS')
        if constraints is not None and (type(constraints) is not list or constraints):
            _outside('Nonempty successor constraints need their own source branch')
        if node.properties.get('IN_LAYER_LAYOUT_UNIT') is not None or node.properties.get('BARYCENTER_ASSOCIATES') is not None:
            _outside('Layout units and barycenter associates require a separate branch')
        early_return = len(graph.layers) == 1 and len(nodes) == 1
        expected = ('FIXED_SIDE', 'FIXED_ORDER') if strategy == 'BARYCENTER' or early_return else ('FIXED_ORDER',)
        if node.properties.get('PORT_CONSTRAINTS') not in (expected if node.type == 'NORMAL' else ('FIXED_POS',)):
            _outside('The real side/sort/preceding crossing processors must prepare port constraints')
        if not allow_detached_north and node.port_sides_cached is not True:
            _outside('Real port-side ranges must be cached before crossing minimization')
        for side in (() if allow_detached_north else ('EAST', 'WEST')):
            indices = [i for i, port in enumerate(node.ports) if port.side == side]
            if indices and (indices != list(range(indices[0], indices[-1] + 1)) or node.port_side_indices.get(side) != (indices[0], indices[-1] + 1)):
                _outside('Cached port ranges do not match the ordered side lists')
        for port in node.ports:
            if port in ports or port.owner is not node or port.origin is not None:
                _outside('Only distinct implicit flow-side ports are admitted')
            ports.add(port)
            if allow_detached_north and port.side == 'NORTH':
                if port.incoming_edges or port.outgoing_edges:
                    _outside('Restored NORTH loop ports must retain empty adjacency')
                continue
            if port.side not in ('EAST', 'WEST'):
                _outside('Only live flow-side ports are admitted during crossing')
            if len(port.incoming_edges) + len(port.outgoing_edges) != 1:
                _outside('Every private port must have exactly one segment')
            if port.side == 'EAST':
                if port.incoming_edges or not port.outgoing_edges:
                    _outside('EAST ports must be outgoing')
                edge = port.outgoing_edges[0]
                if edge in edges or edge.source is not port or edge.target is None or edge.target.owner not in node_set:
                    _outside('Outgoing segment adjacency is inconsistent')
                if edge.target not in edge.target.owner.ports or edge.target.incoming_edges != [edge]:
                    _outside('Target private-port adjacency is inconsistent')
                if edge.target.side != 'WEST' or edge.target.owner.layer not in layer_index or layer_index[edge.target.owner.layer] != layer_index[node.layer] + 1:
                    _outside('All segments must be proper forward adjacent-layer edges')
                edges.add(edge)
            else:
                if port.outgoing_edges or not port.incoming_edges:
                    _outside('WEST ports must be incoming')
                edge = port.incoming_edges[0]
                if edge.target is not port or edge.source is None or edge.source.owner not in node_set or edge.source.outgoing_edges != [edge]:
                    _outside('Incoming segment adjacency is inconsistent')
    if len(ports) > 392 or len(edges) > 196:
        _outside('Crossing counters exceed the reviewed proper-segment bound')
    adjacent = {node: [] for node in nodes}
    for edge in edges:
        adjacent[edge.source.owner].append(edge.target.owner)
        adjacent[edge.target.owner].append(edge.source.owner)
    pending, connected = nodes[:1], set()
    while pending:
        node = pending.pop()
        if node not in connected:
            connected.add(node)
            pending.extend(neighbor for neighbor in adjacent[node] if neighbor not in connected)
    if len(connected) != len(nodes) and graph.options.values['org.eclipse.elk.separateConnectedComponents'] is not False:
        _outside('The approved proper work graph must be connected')
    return nodes


class _Fenwick:
    """Worker BinaryIndexedTree, bounded integer indices and counts."""
    def __init__(self, maximum):
        self.sums = [0] * (maximum + 1)
        self.counts = [0] * maximum
        self.size = 0

    def add(self, index):
        self.size += 1
        self.counts[index] += 1
        index += 1
        while index < len(self.sums):
            self.sums[index] += 1
            index += index & -index

    def rank(self, index):
        result = 0
        while index > 0:
            result += self.sums[index]
            index -= index & -index
        return result

    def remove_all(self, index):
        count = self.counts[index]
        if not count:
            return
        self.counts[index] = 0
        self.size -= count
        index += 1
        while index < len(self.sums):
            self.sums[index] -= count
            index += index & -index


def _count_between(left, right):
    # Source counterclockwise order, not both layers in top-down order.
    ports = [port for node in left for port in _side(node, 'EAST')]
    ports += [port for node in reversed(right) for port in _side(node, 'WEST')]
    positions = {port: index for index, port in enumerate(ports)}
    tree, crossings = _Fenwick(len(ports)), 0
    for port in ports:
        tree.remove_all(positions[port])
        ends = []
        for edge in [*port.incoming_edges, *port.outgoing_edges]:
            end = positions[edge.target if edge.source is port else edge.source]
            if end > positions[port]:
                crossings += tree.rank(end)
                ends.insert(0, end)
        for end in ends:
            tree.add(end)
    return crossings


def _count_all(order):
    # Direct guard excludes hyperedges, in-layer/N-S ports and compound terms.
    return sum(_count_between(left, right) for left, right in zip(order, order[1:]))


class _PortDistributor:
    def __init__(self, node_relative):
        self.node_relative = node_relative
        self.ranks = {}
        self.barycenters = {}
        self.node_positions = {}
        self.min_barycenter = self.max_barycenter = 0

    def calculate_ranks(self, layer, inputs):
        consumed = 0
        for node in layer:
            ports = [port for port in node.ports if port.incoming_edges] if inputs else [port for port in node.ports if port.outgoing_edges]
            count = len(ports)
            increment = 1 / (count + 1) if self.node_relative else 1
            position = consumed + 1 - increment if inputs and self.node_relative else consumed + count if inputs else consumed + increment
            for port in ports:
                self.ranks[port] = position
                position += -increment if inputs else increment
            consumed += 1 if self.node_relative else count

    def _compare(self, left, right):
        if left.side != right.side:
            return -1 if left.side == 'EAST' else 1
        a, b = self.barycenters[left], self.barycenters[right]
        return 0 if a == 0 and b == 0 else -1 if a == 0 else 1 if b == 0 else _double_compare(a, b)

    def distribute(self, node, side):
        if node.properties['PORT_CONSTRAINTS'] in ('FIXED_ORDER', 'FIXED_POS'):
            return
        self.min_barycenter = self.max_barycenter = 0
        for port in _side(node, side):
            value = 0
            for edge in port.outgoing_edges:
                value += self.ranks[edge.target]
            for edge in port.incoming_edges:
                value -= self.ranks[edge.source]
            self.barycenters[port] = value / (len(port.incoming_edges) + len(port.outgoing_edges))
            self.min_barycenter = min(self.min_barycenter, self.barycenters[port])
            self.max_barycenter = max(self.max_barycenter, self.barycenters[port])
        node.ports.sort(key=cmp_to_key(self._compare))

    def sweep(self, order, index, forward):
        free = order[index]
        for position, node in enumerate(free):
            self.node_positions[node] = position
        side = 'WEST' if forward else 'EAST'
        if (forward and index != 0) or (not forward and index != len(order) - 1):
            fixed = order[index - 1 if forward else index + 1]
            self.calculate_ranks(fixed, not forward)
            for node in free:
                self.distribute(node, side)
            self.calculate_ranks(free, forward)
            for node in fixed:
                self.distribute(node, 'EAST' if forward else 'WEST')
        else:
            for node in free:
                self.distribute(node, side)
        return False


class _Barycenter:
    def __init__(self, random, distributor, nodes):
        self.random, self.distributor = random, distributor
        self.states = {node: {'degree': 0, 'summed_weight': 0, 'barycenter': None, 'visited': False} for node in nodes}
        self.constraint_groups = {node: [node] for node in nodes}

    def _finish(self, layer):
        layer.sort(key=cmp_to_key(lambda a, b: _double_compare(self.states[a]['barycenter'], self.states[b]['barycenter'])))
        if len(layer) > 1:
            # Guarded empty Forster graph: keep source mutable-default reads,
            # group construction/flattening and existing sorted order.
            groups = [self.constraint_groups[node] for node in layer]
            for group in groups:
                get_successor_constraints(group[0])
            layer[:] = [node for group in groups for node in group]

    def first(self, order, forward):
        layer = order[0 if forward else -1]
        for node in layer:
            value = self.random.next_double()
            self.states[node].update(barycenter=value, summed_weight=value, degree=1)
        self._finish(layer)
        return False

    def minimize(self, order, index, forward, first_sweep):
        self.distributor.calculate_ranks(order[index - 1 if forward else index + 1], not forward)
        layer = order[index]
        for node in layer:
            state = self.states[node]
            state.update(degree=0, summed_weight=0, barycenter=None, visited=True)
            for port in node.ports:
                edges = port.incoming_edges if forward else port.outgoing_edges
                for edge in edges:
                    fixed = edge.source if forward else edge.target
                    state['summed_weight'] += self.distributor.ranks[fixed]
                    state['degree'] += 1
            if state['degree'] > 0:
                state['summed_weight'] += self.random.next(24) * (2 ** -24) * 0.07000000029802322 - 0.03500000014901161
                state['barycenter'] = state['summed_weight'] / state['degree']
        if not first_sweep:
            previous = -1
            for i, node in enumerate(layer):
                state = self.states[node]
                if state['barycenter'] is None:
                    following = previous + 1
                    for later in layer[i+1:]:
                        if self.states[later]['barycenter'] is not None:
                            following = self.states[later]['barycenter']
                            break
                    value = (previous + following) / 2
                    state.update(barycenter=value, summed_weight=value, degree=1)
                previous = state['barycenter']
        else:
            maximum = max([0, *[self.states[node]['barycenter'] for node in layer if self.states[node]['barycenter'] is not None]]) + 2
            for node in layer:
                state = self.states[node]
                if state['barycenter'] is None:
                    value = self.random.next(24) * (2 ** -24) * maximum - 1
                    state.update(barycenter=value, summed_weight=value, degree=1)
        self._finish(layer)
        return False


class _InLayerCounter:
    """Source init/notify scratch; proper-DAG in-layer contributions are zero."""
    def __init__(self, layer, side):
        ports = [port for node in layer for port in _top_down_ports(node, side)]
        self.positions = {port: i for i, port in enumerate(ports)}
        self.cardinalities = {node: len(_side(node, side)) for node in layer}
        self.side = side
        self.tree = _Fenwick(len(ports))

    def notify(self, upper, lower):
        for port in _top_down_ports(upper, self.side):
            self.positions[port] += self.cardinalities[lower]
        for port in _top_down_ports(lower, self.side):
            self.positions[port] -= self.cardinalities[upper]


class _Adjacency:
    def __init__(self, positions):
        self.groups = []
        for position in positions:
            if self.groups and self.groups[-1][0] == position:
                self.groups[-1][1] += 1
            else:
                self.groups.append([position, 1])
        self.groups.sort(key=lambda item: item[0])
        self.size = len(positions)
        self.reset()

    def reset(self):
        self.index, self.remaining = 0, self.size
        self.cardinality = self.groups[0][1] if self.groups else 0

    def remove(self):
        if self.cardinality == 1:
            self.index += 1
            if self.index < len(self.groups):
                self.cardinality = self.groups[self.index][1]
        else:
            self.cardinality -= 1
        self.remaining -= 1


class _PairCounter:
    def __init__(self, order, index):
        self.order, self.index = order, index
        self.positions, self.adjacencies, self.matrix = {}, {}, {}
        for neighbor, side in [(index - 1, 'EAST'), (index + 1, 'WEST')]:
            if 0 <= neighbor < len(order):
                ports = [port for node in order[neighbor] for port in _top_down_ports(node, side)]
                self.positions.update({port: i for i, port in enumerate(ports)})

    def _adjacent(self, node, side):
        key = node, side
        if key not in self.adjacencies:
            # Source populates the entire side lazily on the first read.
            for current in self.order[self.index]:
                values = []
                for port in _top_down_ports(current, side):
                    for edge in port.incoming_edges if side == 'WEST' else port.outgoing_edges:
                        values.append(self.positions[edge.source if side == 'WEST' else edge.target])
                self.adjacencies[current, side] = _Adjacency(values)
        value = self.adjacencies[key]
        value.reset()
        return value

    def counts(self, upper, lower):
        key = upper.id, lower.id
        if key not in self.matrix:
            ul = lu = 0
            for side in ('WEST', 'EAST'):
                a, b = self._adjacent(upper, side), self._adjacent(lower, side)
                while a.remaining and b.remaining:
                    av, bv = a.groups[a.index][0], b.groups[b.index][0]
                    if av > bv:
                        ul += a.remaining
                        b.remove()
                    elif bv > av:
                        lu += b.remaining
                        a.remove()
                    else:
                        ul += a.remaining - a.cardinality
                        lu += b.remaining - b.cardinality
                        a.remove()
                        b.remove()
            self.matrix[key] = ul
            self.matrix[lower.id, upper.id] = lu
        return self.matrix[key], self.matrix[lower.id, upper.id]


class _GreedySwitch:
    def __init__(self):
        self.current = None

    def _setup(self, order, index):
        self.current = order[index]
        self.pairs = _PairCounter(order, index)
        self.left = _InLayerCounter(self.current, 'WEST')
        self.right = _InLayerCounter(self.current, 'EAST')
        self.north_south_positions = {}  # Guard excludes every N/S port.

    def _downward(self):
        improved = False
        for index in range(len(self.current) - 1):
            upper, lower = self.current[index:index+2]
            get_successor_constraints(upper)  # Real short-circuit property read.
            ul, lu = self.pairs.counts(upper, lower)
            if ul > lu:
                self.left.notify(upper, lower)
                self.right.notify(upper, lower)
                self.current[index], self.current[index+1] = lower, upper
                improved = True
        return improved

    def first(self, order, forward):
        self._setup(order, 0 if forward else len(order)-1)
        return self._downward()

    def minimize(self, order, index, forward, first_sweep):
        self._setup(order, index)
        improved = False
        while self._downward():
            improved = True
        return improved


def _snapshot(order):
    return [list(layer) for layer in order], {node: list(node.ports) for layer in order for node in layer}


def layer_sweep(graph, *, strategy):
    """Actual shared-RNG initialization, sweep drivers and saved-order writeback."""
    nodes = _guard(graph, strategy)
    if not nodes or (len(graph.layers) == 1 and len(nodes) == 1):
        return
    graph.id = 0
    random = graph.random
    saved_seed = random.next_long()
    distributor = _PortDistributor(random.next(1) != 0) if strategy == 'BARYCENTER' else None
    port_index = 0
    for index, layer in enumerate(graph.layers):
        layer.id = index
        for node_index, node in enumerate(layer.nodes):
            node.id = node_index
            for port in node.ports:
                port.id = port_index
                port_index += 1
    order = [list(layer.nodes) for layer in graph.layers]
    if distributor is not None:
        distributor.ranks = {port: 0 for node in nodes for port in node.ports}
        distributor.barycenters = {port: 0 for node in nodes for port in node.ports}
    minimizer = _Barycenter(random, distributor, nodes) if distributor is not None else _GreedySwitch()
    # The holder parent-port array and type-decider influence records are dead
    # under hasParent=false; the generic counter's hyperedge/N-S records are
    # dead under the proper one-edge-per-port guard. Their private contents are
    # projected out, not represented by fictitious all-zero mirror arrays.
    # Actual graph IDs, barycenter state, constraints and live counters remain.

    def distribute(index, forward):
        if distributor is not None:
            return distributor.sweep(order, index, forward)
        # Source GreedyPortDistributor initializes a private positions/tree
        # counter, then every fixed-order/fixed-pos node continues before its
        # only consumer (port switching). The next call replaces this scratch;
        # it has no graph writes or RNG calls. Project out that dead counter,
        # retaining the actual visits/skip prerequisite and live node swaps.
        for node in order[index]:
            if node.properties['PORT_CONSTRAINTS'] in ('FIXED_ORDER', 'FIXED_POS'):
                continue
            _outside('A free port reached the unapproved greedy port-switch branch')
        return False

    def sweep(forward, first):
        improved = distribute(0 if forward else len(order)-1, forward)
        for index in range(1, len(order)) if forward else range(len(order)-2, -1, -1):
            improved = bool(minimizer.minimize(order, index, forward, first) | improved)
            improved = bool(distribute(index, forward) | improved)
        return improved

    if strategy == 'BARYCENTER':
        random.set_seed(saved_seed)
        best_crossings, chosen = (1 << 31)-1, None
        for _ in range(7):
            forward = random.next(1) != 0
            initial_crossings = _count_all(order)
            minimizer.first(order, forward)
            sweep(forward, True)
            crossings = _count_all(order)
            while True:
                current_best = _snapshot(order)
                if crossings == 0:
                    returned_crossings = 0
                    break
                forward = not forward
                old = crossings
                sweep(forward, False)
                crossings = _count_all(order)
                if old <= crossings:
                    returned_crossings = old
                    break
            if returned_crossings < best_crossings:
                best_crossings = returned_crossings
                chosen = current_best
                if best_crossings == 0:
                    break
    else:
        forward, improved = random.next(1) != 0, True
        while improved:
            improved = minimizer.first(order, forward)
            improved = bool(sweep(forward, False) | improved)
            forward = not forward
        chosen = _snapshot(order)
    chosen_order, chosen_ports = chosen
    for layer, ordered in zip(graph.layers, chosen_order):
        layer.nodes[:] = ordered
        for index, node in enumerate(ordered):
            node.id = index
            node.ports[:] = chosen_ports[node]
            if node.properties['PORT_CONSTRAINTS'] not in ('FIXED_ORDER', 'FIXED_POS'):
                node.properties['PORT_CONSTRAINTS'] = 'FIXED_ORDER'
