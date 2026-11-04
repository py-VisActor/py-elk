# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# Source closure CG01-CG06, HOST15/V/cgraph-source-review-01.json.
"""General one-dimensional rectangle constraints and group compaction.

The connected-component hull/transformer is a separate caller. This module
does not substitute SPOrE tree compaction or read reference/oracle data.
"""
from collections import deque

from .cell_layout import Rectangle, _maximum
from .graph import Vec2
from .ports import double_compare, _source_sort
from ..radial import IdentitySet
from ...execution.identity import identity_hash


def _minimum(a, b):
    return -_maximum(-float(a), -float(b))


class _NodeIdentities:
    @staticmethod
    def identity_hash(node):
        # The cached code belongs to the node, without retaining every CNode
        # in a process-global container. Reuse the one native allocator.
        return identity_hash(node, node)


_NODE_IDENTITIES = _NodeIdentities()


class Quadruplet:
    def __init__(self, left=False, right=False, up=False, down=False):
        self.left, self.right, self.up, self.down = left, right, up, down

    def get(self, direction):
        return {'LEFT': self.left, 'RIGHT': self.right,
                'UP': self.up, 'DOWN': self.down}.get(direction, False)


class CNode:
    def __init__(self, owner, rectangle, individual_spacing=None):
        self.owner = owner
        self.rect = rectangle
        self.hitbox = Rectangle(float(rectangle.x), float(rectangle.y),
                                float(rectangle.width), float(rectangle.height))
        self.constraints = []
        self.group_offset = Vec2()
        self.lock = Quadruplet()
        self.spacing_ignore = Quadruplet()
        self.individual_spacing = individual_spacing
        self.group = None
        self.id = 0
        self.reposition = True
        self.start_pos = -float('inf')


class CGroup:
    def __init__(self, nodes=()):
        self.nodes = {}
        self.incoming_constraints = IdentitySet(_NODE_IDENTITIES)
        self.reference = None
        self.delta = self.delta_normalized = 0.0
        self.out_degree = 0
        self.reposition = True
        self.start_pos = -float('inf')
        for node in nodes:
            if self.reference is None:
                self.reference = node
            self.add_node(node)

    def add_node(self, node):
        _NODE_IDENTITIES.identity_hash(node)
        self.nodes[node] = None
        if node.group is not None:
            raise RuntimeError('CNode belongs to another CGroup.')
        node.group = self

    def remove_node(self, node):
        _NODE_IDENTITIES.identity_hash(node)
        if node not in self.nodes:
            return False
        del self.nodes[node]
        node.group = None
        return True


class CGraph:
    def __init__(self, supported_directions):
        self.nodes = []
        self.groups = []
        self.supported_directions = supported_directions


class _DefaultSpacing:
    @staticmethod
    def spacing(first, second):
        a = first.owner.spacing if first.individual_spacing is None else first.individual_spacing
        b = second.owner.spacing if second.individual_spacing is None else second.individual_spacing
        return _maximum(a, b)

    horizontal = spacing
    vertical = spacing


class ComponentSpacing(_DefaultSpacing):
    @staticmethod
    def spacing(first, second):
        a = first.owner.spacing if first.individual_spacing is None else first.individual_spacing
        b = second.owner.spacing if second.individual_spacing is None else second.individual_spacing
        return _minimum(a, b)

    horizontal = spacing
    vertical = spacing


class _ActiveIntervals:
    """Comparator-unique keys for a sweep whose hitboxes remain unchanged.

    Binary search supplies lower/higher/equivalent lookup; the sorted native
    list keeps the first key representative when an equivalent key arrives.
    """
    def __init__(self):
        self.nodes = []

    @staticmethod
    def compare(a, b):
        return double_compare(a.hitbox.x + a.hitbox.width / 2,
                              b.hitbox.x + b.hitbox.width / 2)

    def _locate(self, node):
        low, high = 0, len(self.nodes)
        while low < high:
            middle = (low + high) // 2
            if self.compare(self.nodes[middle], node) < 0:
                low = middle + 1
            else:
                high = middle
        equal = low < len(self.nodes) and self.compare(self.nodes[low], node) == 0
        return low, equal

    def add(self, node):
        index, equal = self._locate(node)
        if not equal:
            self.nodes.insert(index, node)

    def lower(self, node):
        index, _ = self._locate(node)
        return self.nodes[index - 1] if index else None

    def higher(self, node):
        index, equal = self._locate(node)
        index += int(equal)
        return self.nodes[index] if index < len(self.nodes) else None

    def remove(self, node):
        index, equal = self._locate(node)
        if equal:
            del self.nodes[index]


class _ScanlineConstraints:
    def __init__(self):
        self.compactor = None
        self.intervals = _ActiveIntervals()
        self.candidates = []

    @staticmethod
    def _compare(a, b):
        node_a, low_a = a
        node_b, low_b = b
        y_a, y_b = node_a.hitbox.y, node_b.hitbox.y
        if not low_a:
            y_a += node_a.hitbox.height
        if not low_b:
            y_b += node_b.hitbox.height
        result = double_compare(y_a, y_b)
        if result == 0:
            if not low_a and low_b:
                return -1
            if not low_b and low_a:
                return 1
        return result

    def calculate(self, compactor):
        self.compactor = compactor
        # Both fixed-source expansion/normalization loops use literal spacing
        # zero. Their guarded >0 arithmetic has no effect for this calculator.
        points = [(node, low) for node in compactor.graph.nodes for low in (True, False)]
        self.intervals.nodes.clear()
        self.candidates = [None] * len(compactor.graph.nodes)
        for index, node in enumerate(compactor.graph.nodes):
            node.id = index
        _source_sort(points, self._compare)
        for node, low in points:
            if low:
                self.intervals.add(node)
                self.candidates[node.id] = self.intervals.lower(node)
                right = self.intervals.higher(node)
                if right is not None:
                    self.candidates[right.id] = node
            else:
                left = self.intervals.lower(node)
                if (left is not None and left is self.candidates[node.id]
                        and left.group is not None and left.group is not node.group):
                    left.constraints.append(node)
                right = self.intervals.higher(node)
                if (right is not None and self.candidates[right.id] is node
                        and right.group is not None and right.group is not node.group):
                    node.constraints.append(right)
                self.intervals.remove(node)


_SCANLINE_CONSTRAINTS = _ScanlineConstraints()
_DEFAULT_SPACING = _DefaultSpacing()


class OneDimensionalCompactor:
    def __init__(self, graph):
        self.graph = graph
        self.constraint_algorithm = _SCANLINE_CONSTRAINTS
        self.spacings_handler = _DEFAULT_SPACING
        self.direction = 'UNDEFINED'
        self.finished = False
        self.locking_strategy = lambda pair: pair[0].group.out_degree != 0
        self.calculate_group_offsets()
        for node in graph.nodes:
            if node.group is None:
                graph.groups.append(CGroup((node,)))

    def calculate_group_offsets(self):
        for group in self.graph.groups:
            group.reference = None
            for node in group.nodes:
                node.group_offset.x = node.group_offset.y = 0.0
                if group.reference is None or node.hitbox.x < group.reference.hitbox.x:
                    group.reference = node
            for node in group.nodes:
                node.group_offset.x = node.hitbox.x - group.reference.hitbox.x
                node.group_offset.y = node.hitbox.y - group.reference.hitbox.y
        return self

    def calculate_constraints_for_groups(self):
        for group in self.graph.groups:
            group.out_degree = 0
            group.incoming_constraints.buckets.clear()
        for group in self.graph.groups:
            for node in group.nodes:
                for incoming in node.constraints:
                    if incoming.group is not group:
                        group.incoming_constraints.add(incoming)
                        incoming.group.out_degree += 1

    def calculate_constraints(self):
        for node in self.graph.nodes:
            node.constraints.clear()
        self.constraint_algorithm.calculate(self)
        self.calculate_constraints_for_groups()

    def force_constraints_recalculation(self):
        self.calculate_constraints()
        return self

    def mirror_hitboxes(self):
        for node in self.graph.nodes:
            node.hitbox.x = -node.hitbox.x - node.hitbox.width
        self.calculate_group_offsets()

    def transpose_hitboxes(self):
        for node in self.graph.nodes:
            box = node.hitbox
            box.x, box.y = box.y, box.x
            box.width, box.height = box.height, box.width
            offset = node.group_offset
            offset.x, offset.y = offset.y, offset.x
        self.calculate_group_offsets()

    def reverse_constraints(self):
        incoming = {}
        for node in self.graph.nodes:
            _NODE_IDENTITIES.identity_hash(node)
            incoming[node] = []
        for node in self.graph.nodes:
            node.start_pos = -float('inf')
            for predecessor in node.constraints:
                _NODE_IDENTITIES.identity_hash(predecessor)
                incoming[predecessor].append(node)
        for node in self.graph.nodes:
            node.constraints.clear()
            _NODE_IDENTITIES.identity_hash(node)
            node.constraints = incoming[node]
        self.calculate_constraints_for_groups()

    def _ensure_unfinished(self):
        if self.finished:
            raise RuntimeError('The OneDimensionalCompactor instance has been finished already.')

    def change_direction(self, direction):
        self._ensure_unfinished()
        if direction not in self.graph.supported_directions:
            raise RuntimeError('The direction ' + direction + ' is not supported by the CGraph instance.')
        if direction == self.direction:
            return self
        old, self.direction = self.direction, direction
        # Each sequence is the actual source state transition. UNDEFINED as
        # destination changes the enum only; it does not restore hitboxes.
        actions = {
            ('UNDEFINED', 'LEFT'): 'C', ('UNDEFINED', 'RIGHT'): 'MC',
            ('UNDEFINED', 'UP'): 'TC', ('UNDEFINED', 'DOWN'): 'TMC',
            ('LEFT', 'RIGHT'): 'MR', ('LEFT', 'UP'): 'TC', ('LEFT', 'DOWN'): 'TMC',
            ('RIGHT', 'LEFT'): 'MR', ('RIGHT', 'UP'): 'MTC', ('RIGHT', 'DOWN'): 'MTMC',
            ('UP', 'LEFT'): 'TC', ('UP', 'RIGHT'): 'TMC', ('UP', 'DOWN'): 'MR',
            ('DOWN', 'LEFT'): 'MTC', ('DOWN', 'RIGHT'): 'MTMC', ('DOWN', 'UP'): 'MR',
        }
        operations = {'C': self.calculate_constraints, 'M': self.mirror_hitboxes,
                      'T': self.transpose_hitboxes, 'R': self.reverse_constraints}
        for action in actions.get((old, direction), ''):
            operations[action]()
        return self

    def set_locking_strategy(self, strategy):
        self.locking_strategy = strategy
        return self

    def set_spacings_handler(self, handler):
        self.spacings_handler = handler
        return self

    def apply_locking_strategy(self, direction=None):
        direction = self.direction if direction is None else direction
        for group in self.graph.groups:
            group.reposition = True
        for node in self.graph.nodes:
            first = self.locking_strategy((node, direction))
            if type(first) is not bool:
                raise TypeError('Actual Boolean locking result required')
            node.reposition = first
            group = node.group
            previous = group.reposition
            second = self.locking_strategy((node, direction))
            if type(second) is not bool:
                raise TypeError('Actual Boolean locking result required')
            group.reposition = int(previous) & int(second)
        return self

    def _compact_groups(self):
        minimum = float('inf')
        for node in self.graph.nodes:
            minimum = _minimum(minimum, node.group.reference.hitbox.x + node.group_offset.x)
        sinks = deque()
        for group in self.graph.groups:
            group.start_pos = minimum
            if group.out_degree == 0:
                sinks.append(group)
        while sinks:
            group = sinks.popleft()
            difference = group.reference.hitbox.x
            for node in group.nodes:
                proposed = group.start_pos + node.group_offset.x
                node.start_pos = proposed if group.reposition or node.hitbox.x < proposed else node.hitbox.x
            difference -= group.reference.start_pos
            group.delta += difference
            if self.direction in ('RIGHT', 'DOWN'):
                group.delta_normalized += difference
            else:
                group.delta_normalized -= difference
            for node in group.nodes:
                for incoming in node.constraints:
                    spacing = (self.spacings_handler.horizontal(node, incoming)
                               if self.direction in ('LEFT', 'RIGHT')
                               else self.spacings_handler.vertical(node, incoming))
                    incoming.group.start_pos = _maximum(incoming.group.start_pos,
                        node.start_pos + node.hitbox.width + spacing - incoming.group_offset.x)
                    if not incoming.reposition:
                        incoming.group.start_pos = _maximum(incoming.group.start_pos,
                            incoming.hitbox.x - incoming.group_offset.x)
                    incoming.group.out_degree -= 1
                    if incoming.group.out_degree == 0:
                        sinks.append(incoming.group)
        for node in self.graph.nodes:
            node.hitbox.x = node.start_pos

    def compact(self):
        self._ensure_unfinished()
        if self.direction == 'UNDEFINED':
            self.change_direction('LEFT')
        for group in self.graph.groups:
            group.out_degree = 0
        for node in self.graph.nodes:
            node.start_pos = -float('inf')
            for incoming in node.constraints:
                incoming.group.out_degree += 1
        self._compact_groups()
        for node in self.graph.nodes:
            node.reposition = True
        return self

    def finish(self):
        self.change_direction('LEFT')
        self.finished = True
        return self


class OwnedCGroup(CGroup):
    """Linked member order with an explicit caller's shared identity owner."""
    def __init__(self, owner, nodes=()):
        self.identity_owner = owner
        super().__init__(nodes)
        self.incoming_constraints = IdentitySet(owner)

    def add_node(self, node):
        if node.group is not None:
            raise RuntimeError('CNode belongs to another CGroup.')
        self.identity_owner.identity_hash(node)
        self.nodes[node] = None
        node.group = self
        if self.reference is None:
            self.reference = node

    def remove_node(self, node):
        self.identity_owner.identity_hash(node)
        if node not in self.nodes:
            return False
        del self.nodes[node]
        node.group = None
        return True


class StrategyCompactor(OneDimensionalCompactor):
    """Common-compaction source strategy interface for the Layered caller.

    Kept opt-in: the historical component compactor and its default ABI retain
    their existing implementation. The Layered transformer supplies predefined
    constraints and a real algorithm object, rather than substituting the
    default longest-path routine for another selected strategy.
    """
    def __init__(self, graph):
        self.graph = graph
        self.constraint_algorithm = _SCANLINE_CONSTRAINTS
        self.spacings_handler = _DEFAULT_SPACING
        self.direction = 'UNDEFINED'
        self.finished = False
        self.locking_strategy = None
        self.compaction_algorithm = None
        self.calculate_group_offsets()
        for node in graph.nodes:
            if node.group is None:
                graph.groups.append(OwnedCGroup(graph.identity_owner, (node,)))
            box = node.hitbox
            node.hitbox_pre_compaction = Rectangle(box.x, box.y, box.width, box.height)

    def set_constraint_algorithm(self, algorithm):
        self.constraint_algorithm = algorithm
        return self

    def set_compaction_algorithm(self, algorithm):
        self.compaction_algorithm = algorithm
        return self

    def calculate_constraints(self):
        for node in self.graph.nodes:
            node.constraints.clear()
        constraints = (self.graph.predefined_horizontal_constraints
                       if self.direction in ('LEFT', 'RIGHT')
                       else self.graph.predefined_vertical_constraints)
        for first, second in constraints:
            if self.direction in ('LEFT', 'UP'):
                first.constraints.append(second)
            else:
                second.constraints.append(first)
        self.constraint_algorithm.calculate(self)
        self.calculate_constraints_for_groups()
        for group in self.graph.groups:
            group.out_degree_real = group.out_degree

    def reverse_constraints(self):
        incoming = {}
        for node in self.graph.nodes:
            self.graph.identity_owner.identity_hash(node)
            incoming[node] = []
        for node in self.graph.nodes:
            node.start_pos = -float('inf')
            for predecessor in node.constraints:
                self.graph.identity_owner.identity_hash(predecessor)
                incoming[predecessor].append(node)
        for node in self.graph.nodes:
            node.constraints.clear()
            self.graph.identity_owner.identity_hash(node)
            node.constraints = incoming[node]
        self.calculate_constraints_for_groups()
        for group in self.graph.groups:
            group.out_degree_real = group.out_degree

    def is_locked(self, node):
        return False if self.locking_strategy is None else self.locking_strategy((node, self.direction))

    def _compact_groups(self):
        minimum = float('inf')
        for node in self.graph.nodes:
            minimum = _minimum(minimum, node.group.reference.hitbox.x + node.group_offset.x)
        sinks = deque()
        for group in self.graph.groups:
            group.start_pos = minimum
            if group.out_degree == 0:
                sinks.append(group)
        while sinks:
            group = sinks.popleft()
            difference = group.reference.hitbox.x
            for node in group.nodes:
                proposed = group.start_pos + node.group_offset.x
                locked = any(self.is_locked(member) for member in group.nodes)
                node.start_pos = proposed if not locked or node.hitbox.x < proposed else node.hitbox.x
            difference -= group.reference.start_pos
            group.delta += difference
            group.delta_normalized += difference if self.direction in ('RIGHT', 'DOWN') else -difference
            for node in group.nodes:
                for incoming in node.constraints:
                    spacing = (self.spacings_handler.horizontal(node, incoming)
                               if self.direction in ('LEFT', 'RIGHT')
                               else self.spacings_handler.vertical(node, incoming))
                    target = incoming.group
                    target.start_pos = _maximum(target.start_pos,
                        node.start_pos + node.hitbox.width + spacing - incoming.group_offset.x)
                    if self.is_locked(incoming):
                        target.start_pos = _maximum(target.start_pos, incoming.hitbox.x - incoming.group_offset.x)
                    target.out_degree -= 1
                    if target.out_degree == 0:
                        sinks.append(target)
        for node in self.graph.nodes:
            node.hitbox.x = node.start_pos

    def compact(self):
        self._ensure_unfinished()
        if self.direction == 'UNDEFINED':
            self.change_direction('LEFT')
        for group in self.graph.groups:
            group.out_degree = group.out_degree_real
        for node in self.graph.nodes:
            node.start_pos = -float('inf')
        if self.compaction_algorithm is None:
            self._compact_groups()
        else:
            self.compaction_algorithm.compact(self)
        return self
