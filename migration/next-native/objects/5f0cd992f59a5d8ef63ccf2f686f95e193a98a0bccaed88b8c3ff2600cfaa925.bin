# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P17F in references/e13-kernel-sources.json.
"""Actual two-pass hierarchical import, separate from compound scheduling.

The ordinary provider keeps its existing importer until the compound driver is
implemented. This class implements import only; it never flattens that driver.
"""
from collections import deque

from .model_order_import import (
    _GROUP, _assign_native_integer, _assign_origin_order, needs_model_order,
)
from .native_import_full import FullElkGraphImporter
from .property_access import read_layered_scalar


class HierarchicalElkGraphImporter(FullElkGraphImporter):
    def _uses_layered(self, raw):
        if not self.state.has_option(raw, 'algorithm'):
            return True
        return 'org.eclipse.elk.layered'.endswith(
            self.state.get_native_property(raw, 'algorithm'))

    def has_inside_self_loops(self, raw):
        if self._read(raw, 'INSIDE_SELF_LOOPS_ACTIVATE'):
            # Actual allOutgoingEdges visits the node, then its physical ports.
            # No dedup: one edge may occur in several actual incidence lists.
            for shape in (raw, *raw.get('ports', [])):
                for edge in self.state.incidence(shape):
                    if self._is_self_loop(edge):
                        if self._read(edge, 'INSIDE_SELF_LOOPS_YO'):
                            return True
        return False

    def find_coordinate_system_origin(self, edge, top_raw, top_native):
        source = self._endpoint_node(edge['sources'][0])
        target = self._endpoint_node(edge['targets'][0])
        if self.state.parents[id(source)] is self.state.parents[id(target)]:
            return None
        if self.state._ancestor(target, source):
            return None
        origin = self.state.current_containers[id(edge)]
        if origin is top_raw:
            return top_native
        node = self.lookup(origin)
        if node is not None:
            graph = getattr(node, 'nested_graph', None)
            if graph is not None:
                return graph
        return None

    def import_hierarchical_graph(self, raw, graph):
        queue = deque(raw.get('children', []))
        parent_direction = read_layered_scalar(graph, 'DIRECTION', 'DIRECTION')
        index = 0
        groups = set()
        while queue:
            child = queue.popleft()
            parent = self.state.parents[id(child)]
            # Hierarchical source assigns MODEL_ORDER before NO_LAYOUT.
            if (needs_model_order(self.state, parent)
                    and not self._read(child, 'CONSIDER_MODEL_ORDER_NO_MODEL_ORDER_0')):
                _assign_origin_order(self.state, child, index)
                index += 1
                if self.state.has_option(child, _GROUP):
                    groups.add(self.state.get_native_property(child, _GROUP))
            if not self._read(child, 'NO_LAYOUT'):
                has_children = bool(child.get('children'))
                has_inside = self.has_inside_self_loops(child)
                hierarchy = self._read(child, 'HIERARCHY_HANDLING') == 'INCLUDE_CHILDREN'
                uses_layered = self._uses_layered(child)
                nested = None
                if uses_layered and hierarchy and (has_children or has_inside):
                    nested = self.create_lgraph(child)
                    nested.properties['DIRECTION'] = parent_direction
                    if 'SPACING_BASE_VALUE' in nested.properties:
                        self.apply_base_spacing(nested)
                    if self.reader.get(child, 'node', 'nodeSize.constraints'):
                        for port in child.get('ports', []):
                            self.ensure_defined_port_side(nested, port)
                        self.calculate_minimum_graph_size(child, nested)
                parent_graph = graph
                parent_node = self.lookup(parent)
                if parent_node is not None:
                    parent_graph = getattr(parent_node, 'nested_graph', None)
                node = self.transform_node(child, parent_graph)
                if nested is not None:
                    node.nested_graph = nested
                    nested.parent_node = node
                    queue.extend(child.get('children', []))
        _assign_native_integer(graph, 'MAX_MODEL_ORDER_NODES', index)
        _assign_native_integer(graph, 'CB_NUM_MODEL_ORDER_GROUPS', len(groups))

        index = 0
        queue.append(raw)
        while queue:
            current = queue.popleft()
            for edge in self.state.contained_edges(current):
                self.check_edge_validity(edge)
                if needs_model_order(self.state, raw):
                    _assign_origin_order(self.state, edge, index)
                    index += 1
                source = self._endpoint_node(edge['sources'][0])
                target = self._endpoint_node(edge['targets'][0])
                if (self._read(edge, 'NO_LAYOUT') or self._read(source, 'NO_LAYOUT')
                        or self._read(target, 'NO_LAYOUT')):
                    continue
                inside = (self._is_self_loop(edge)
                          and self._read(source, 'INSIDE_SELF_LOOPS_ACTIVATE')
                          and self._read(edge, 'INSIDE_SELF_LOOPS_YO'))
                parent = current
                if inside or self.state._ancestor(target, source):
                    parent = source
                elif self.state._ancestor(source, target):
                    parent = target
                parent_graph = graph
                parent_node = self.lookup(parent)
                if parent_node is not None:
                    parent_graph = getattr(parent_node, 'nested_graph', None)
                native = self.transform_edge(edge, parent, parent_graph)
                native.properties['COORDINATE_SYSTEM_ORIGIN'] = (
                    self.find_coordinate_system_origin(edge, raw, graph))
            if self._read(current, 'HIERARCHY_HANDLING') == 'INCLUDE_CHILDREN':
                for child in current.get('children', []):
                    uses_layered = self._uses_layered(child)
                    same_run = self._read(child, 'HIERARCHY_HANDLING') == 'INCLUDE_CHILDREN'
                    if uses_layered and same_run:
                        queue.append(child)
