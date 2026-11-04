# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# CT01-CT05 / HOST16/V/component-transformer-controller-source-review-01.
"""Actual component rectangle transformer and six-pass compaction controller.

The connected-component geometry producer is a separate caller. This module
uses its real component/extension accessors and the full CGraph engine.
"""
from dataclasses import dataclass

from .cell_layout import _maximum
from .compaction_graph import (CGraph, CGroup, CNode, ComponentSpacing,
    OneDimensionalCompactor, _minimum, _NODE_IDENTITIES)
from .graph import Vec2
from .native_adapters import _read_property
from ..disco import _IdentityMap
from ..triangulation import ValueMap
from ...execution.enum_collections import EnumKeyMap
from ...execution.enum_identity import enum_identity_hash
from ...execution.pair_hash import pair_hash_codes

_DIRECTION_DOMAIN = 'org.eclipse.elk.core.options.Direction'
_DIRECTION_ORDER = ('UNDEFINED', 'RIGHT', 'LEFT', 'DOWN', 'UP')
_DIRECTION_SETS = None
_SPACING_HANDLER = ComponentSpacing()


def _direction_sets():
    global _DIRECTION_SETS
    if _DIRECTION_SETS is None:
        pairs = []
        for values in (('LEFT', 'RIGHT'), ('UP', 'DOWN')):
            directions = ValueMap(lambda key: enum_identity_hash(_DIRECTION_DOMAIN, key),
                                  lambda a, b: a == b)
            for value in values:
                directions.put(value, True)
            pairs.append(directions)
        _DIRECTION_SETS = pairs
    return _DIRECTION_SETS


@dataclass(eq=False)
class _Pair:
    first: object
    second: object


def _pair_hash(pair):
    first = 0 if pair.first is None else _NODE_IDENTITIES.identity_hash(pair.first)
    second = 0 if pair.second is None else _NODE_IDENTITIES.identity_hash(pair.second)
    return pair_hash_codes(first, second)


class _Placeholders:
    def __init__(self):
        self.map = EnumKeyMap(_DIRECTION_DOMAIN, _DIRECTION_ORDER)

    def put(self, key, pair):
        values = self.map.get(key)
        if values is None:
            values = ValueMap(_pair_hash, lambda a, b: a.first is b.first and a.second is b.second)
            changed = values.put(pair, True) is None
            self.map.put(key, values)
            return changed
        return values.put(pair, True) is None

    def values_for(self, key):
        values = self.map.get(key)
        return [] if values is None else list(values)

    def values(self):
        return [pair for values in self.map.values() for pair in values]


# These are the literal source checks. The duplicate NORTH_SOUTH and missing
# NORTH_EAST_SOUTH row remain observable when applying a lock to an old node.
_LOCKS = (
    ((), (True, True, True, True)),
    (('NORTH',), (True, True, True, False)),
    (('EAST',), (False, True, True, True)),
    (('SOUTH',), (True, True, False, True)),
    (('WEST',), (True, False, True, True)),
    (('NORTH', 'EAST'), (False, True, True, False)),
    (('EAST', 'SOUTH'), (False, True, False, True)),
    (('SOUTH', 'WEST'), (True, False, False, True)),
    (('NORTH', 'WEST'), (True, False, True, False)),
    (('NORTH', 'SOUTH'), (True, True, True, True)),
    (('EAST', 'WEST'), (True, True, True, True)),
    (('NORTH', 'SOUTH'), (True, True, True, True)),
    (('EAST', 'SOUTH', 'WEST'), (True, True, True, True)),
    (('NORTH', 'SOUTH', 'WEST'), (True, True, True, True)),
    (('NORTH', 'EAST', 'WEST'), (True, True, True, True)),
    (('NORTH', 'EAST', 'SOUTH', 'WEST'), (True, True, True, True)),
)


def set_lock(node, sides):
    for members, values in _LOCKS:
        if sides == set(members):
            node.lock.left, node.lock.right, node.lock.up, node.lock.down = values


class ComponentsToCGraphTransformer:
    def __init__(self, spacing):
        self.old_position = _IdentityMap(_NODE_IDENTITIES)
        self.offsets = _IdentityMap(_NODE_IDENTITIES)
        self.external_extensions = _IdentityMap(_NODE_IDENTITIES)
        self.external_placeholder = _Placeholders()
        self.spacing = spacing

    def transform(self, connected_components):
        self.graph = CGraph(set(_DIRECTION_ORDER))
        for component in connected_components.components:
            group = CGroup()
            self.graph.groups.append(group)
            for rectangle in component.rectilinear_convex_hull:
                node = CNode(self, rectangle)
                set_lock(node, _read_property(component.graph, 'EXT_PORT_CONNECTIONS'))
                if self.old_position.get(component) is None:
                    self.old_position.put(component, Vec2(rectangle.x, rectangle.y))
                    self.offsets.put(component, node)
                self.graph.nodes.append(node)
                group.add_node(node)
            for extension in component.external_extensions:
                node = CNode(self, extension.get_representor())
                self.external_extensions.put(extension, _Pair(group, node))
                set_lock(node, _read_property(component.graph, 'EXT_PORT_CONNECTIONS'))
                if extension.get_placeholder() is not None:
                    placeholder = CNode(self, extension.get_placeholder(), 1.0)
                    set_lock(placeholder, _read_property(component.graph, 'EXT_PORT_CONNECTIONS'))
                    dummy_group = CGroup()
                    dummy_group.add_node(placeholder)
                    self.external_placeholder.put(extension.get_direction(), _Pair(group, placeholder))
        return self.graph

    def get_offset(self, component):
        saved = self.old_position.get(component)
        offset = Vec2(saved.x, saved.y)
        rectangle = self.offsets.get(component).rect
        offset.x -= rectangle.x
        offset.y -= rectangle.y
        return offset

    def apply_layout(self):
        for node in self.graph.nodes:
            node.rect.x, node.rect.y = node.hitbox.x, node.hitbox.y
        top_left, bottom_right = Vec2(float('inf'), float('inf')), Vec2(-float('inf'), -float('inf'))
        for node in self.graph.nodes:
            _bounds(top_left, bottom_right, node)
        for pair in self.external_placeholder.values():
            _bounds(top_left, bottom_right, pair.second)
        self.global_offset = Vec2(-top_left.x, -top_left.y)
        self.graph_size = Vec2(bottom_right.x - top_left.x, bottom_right.y - top_left.y)
        self.graph.groups.clear()
        self.graph.nodes.clear()


def _bounds(top_left, bottom_right, node):
    box = node.hitbox
    top_left.x = _minimum(top_left.x, box.x)
    top_left.y = _minimum(top_left.y, box.y)
    bottom_right.x = _maximum(bottom_right.x, box.x + box.width)
    bottom_right.y = _maximum(bottom_right.y, box.y + box.height)


def _remove_identity(values, item):
    for index, value in enumerate(values):
        if value is item:
            del values[index]
            return


def _final_lock(pair):
    node, direction = pair
    return node.lock.get(direction) or node.group.out_degree != 0 and node.lock.get(direction)


class OneDimensionalComponentsCompaction:
    def __init__(self, connected_components, spacing):
        _direction_sets()
        self.transformer = ComponentsToCGraphTransformer(spacing)
        self.graph = self.transformer.transform(connected_components)

    def _add_extensions(self, extensions):
        for pair in extensions:
            self.graph.nodes.append(pair.second)
            pair.first.add_node(pair.second)

    def _remove_extensions(self, extensions):
        for pair in extensions:
            _remove_identity(self.graph.nodes, pair.second)
            pair.first.remove_node(pair.second)

    def _placeholders(self, axis, *, add):
        for direction in _direction_sets()[axis]:
            for pair in self.transformer.external_placeholder.values_for(direction):
                if add:
                    self.graph.nodes.append(pair.second)
                    self.graph.groups.append(pair.second.group)
                else:
                    _remove_identity(self.graph.nodes, pair.second)
                    _remove_identity(self.graph.groups, pair.second.group)

    def _update_extensions(self, axis):
        for extension, pair in self.transformer.external_extensions.items():
            direction = extension.get_direction()
            if direction not in (('LEFT', 'RIGHT') if axis == 0 else ('UP', 'DOWN')):
                continue
            box, delta = pair.second.hitbox, pair.first.delta_normalized
            if direction == 'LEFT':
                box.x = self.top_left.x
                box.width = _maximum(1.0, box.width + delta)
            elif direction == 'RIGHT':
                box.x += delta
                box.width = _maximum(1.0, box.width - delta)
            elif direction == 'UP':
                box.y = self.top_left.y
                box.height = _maximum(1.0, box.height + delta)
            elif direction == 'DOWN':
                box.y += delta
                box.height = _maximum(1.0, box.height - delta)

    def _update_placeholders(self, axis):
        for direction in _direction_sets()[axis]:
            for pair in self.transformer.external_placeholder.values_for(direction):
                if direction in ('LEFT', 'RIGHT'):
                    pair.second.hitbox.y += pair.first.delta_normalized
                elif direction in ('UP', 'DOWN'):
                    pair.second.hitbox.x += pair.first.delta_normalized

    def _reset_deltas(self):
        for group in self.graph.groups:
            group.delta = group.delta_normalized = 0.0

    def _compact_pass(self):
        delta = 0.0
        self._reset_deltas()
        self._placeholders(0, add=True)
        self._add_extensions(self.vertical_extensions)
        self.compactor.calculate_group_offsets()
        self.compactor.force_constraints_recalculation()
        self.compactor.change_direction('LEFT').compact()
        self.compactor.change_direction('RIGHT').apply_locking_strategy().compact()
        self.compactor.change_direction('LEFT').apply_locking_strategy().compact()
        self.compactor.change_direction('LEFT')
        self._remove_extensions(self.vertical_extensions)
        self._placeholders(0, add=False)
        self._update_extensions(0)
        self._update_placeholders(1)
        self._placeholders(1, add=True)
        self._add_extensions(self.horizontal_extensions)
        self.compactor.calculate_group_offsets()
        for group in self.graph.groups:
            delta += abs(group.delta_normalized)
        self._reset_deltas()
        self.compactor.change_direction('UP').force_constraints_recalculation().compact()
        self.compactor.change_direction('DOWN').apply_locking_strategy().compact()
        self.compactor.change_direction('UP').apply_locking_strategy().compact()
        self.compactor.change_direction('LEFT')
        self._remove_extensions(self.horizontal_extensions)
        self._placeholders(1, add=False)
        self._update_extensions(1)
        self._update_placeholders(0)
        self.compactor.force_constraints_recalculation()
        for group in self.graph.groups:
            delta += abs(group.delta_normalized)
        return delta

    def compact(self):
        all_nodes = []
        self.vertical_extensions, self.horizontal_extensions = [], []
        for extension, pair in self.transformer.external_extensions.items():
            all_nodes.append(pair.second)
            (self.horizontal_extensions if extension.get_direction() in ('LEFT', 'RIGHT')
             else self.vertical_extensions).append(pair)
        self._add_extensions(self.horizontal_extensions)
        self._add_extensions(self.vertical_extensions)
        self.compactor = OneDimensionalCompactor(self.graph)
        self.compactor.set_spacings_handler(_SPACING_HANDLER)
        self._remove_extensions(self.horizontal_extensions)
        self._remove_extensions(self.vertical_extensions)
        all_nodes.extend(self.compactor.graph.nodes)
        self.top_left, self.bottom_right = Vec2(float('inf'), float('inf')), Vec2(-float('inf'), -float('inf'))
        for node in all_nodes:
            _bounds(self.top_left, self.bottom_right, node)
        self.compactor.set_locking_strategy(lambda pair: pair[0].group.out_degree != 0)
        run = 0
        while True:
            delta = self._compact_pass()
            run += 1
            if not ((run < 2 or delta > 1.0e-4) and run < 10):
                break
        self.compactor.set_locking_strategy(_final_lock)
        self._compact_pass()
        self.compactor.finish()
        self.transformer.apply_layout()

    def get_offset(self, component):
        offset = self.transformer.get_offset(component)
        offset.x = -offset.x
        offset.y = -offset.y
        offset.x += self.transformer.global_offset.x
        offset.y += self.transformer.global_offset.y
        return offset
