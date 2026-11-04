# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P21A actual compound transfer source.
"""Restore original hierarchy edges from their actual routed segment objects."""
from ..radial import IdentitySet
from ...execution.node_micro import VectorChain
from .compound_model import CrossHierarchyEdgeComparator, change_coordinate_system
from .graph import Vec2, set_source, set_target
from .graph_configurator import _graph_of
from .native_transfer import _descendant, _sum_vectors
from .orthogonal_general import get_junction_points
from .ports import _source_sort
from .property_access import read_layered_scalar


def clear_junction_points(original, segments):
    junctions = get_junction_points(original)
    any_junctions = False
    for segment in segments:
        value = get_junction_points(segment.new_edge)
        if value is not None and len(value) != 0:
            any_junctions = True
            break
    if any_junctions:
        if junctions is None:
            junctions = VectorChain()
            original.properties['JUNCTION_POINTS'] = junctions
        else:
            junctions.clear()
    elif junctions is not None:
        original.properties['JUNCTION_POINTS'] = None
    return junctions


def copy_junction_points(source, target, offset):
    junctions = get_junction_points(source)
    if junctions is not None:
        copies = [Vec2(point.x, point.y) for point in junctions]
        for point in copies:
            point.x += offset.x
            point.y += offset.y
        # Source addAll touches target only while copying an actual element.
        # An empty nonnull source with target=None therefore succeeds.
        for point in copies:
            target.append(point)


def copy_labels_back(segment_edge, original, reference_graph):
    index = 0
    while index < len(segment_edge.labels):
        label = segment_edge.labels[index]
        if label.properties.get('ORIGINAL_LABEL_EDGE') is not original:
            index += 1
            continue
        change_coordinate_system(label.pos, _graph_of(segment_edge.source.owner), reference_graph)
        segment_edge.labels.pop(index)
        original.labels.append(label)


def compound_postprocessor(graph, *, monitor):
    monitor.begin('Compound graph postprocessor', 1)
    unnecessary = read_layered_scalar(graph, 'UNNECESSARY_BENDPOINTS', 'UNNECESSARY_BENDPOINTS_0')
    hierarchy_map = graph.properties.get('CROSS_HIERARCHY_MAP')
    dummy_edges = IdentitySet(graph)
    for original in hierarchy_map.keys():
        segments = list(hierarchy_map.values_for(original))
        _source_sort(segments, CrossHierarchyEdgeComparator(graph).compare)
        source = segments[0].get_actual_source()
        target = segments[-1].get_actual_target()
        reference_node = source.owner
        reference = (reference_node.nested_graph if _descendant(target.owner, reference_node)
                     else _graph_of(reference_node))
        junctions = clear_junction_points(original, segments)
        original.bend_points.clear()
        last = None
        for segment in segments:
            offset = Vec2()
            change_coordinate_system(offset, segment.graph, reference)
            edge = segment.new_edge
            bends = [Vec2(point.x, point.y) for point in edge.bend_points]
            for point in bends:
                point.x += offset.x
                point.y += offset.y
            source_point = _sum_vectors(edge.source.owner.pos, edge.source.pos, edge.source.anchor)
            target_point = _sum_vectors(edge.target.owner.pos, edge.target.pos, edge.target.anchor)
            source_point.x += offset.x
            source_point.y += offset.y
            target_point.x += offset.x
            target_point.y += offset.y
            if last is not None:
                following = target_point if len(bends) == 0 else bends[0]
                x_diff = abs(last.x - following.x) > 0.001
                y_diff = abs(last.y - following.y) > 0.001
                if ((not unnecessary and x_diff and y_diff)
                        or (unnecessary and (x_diff or y_diff))):
                    original.bend_points.append(source_point)
            original.bend_points.extend(bends)
            last = source_point if len(bends) == 0 else bends[-1]
            copy_junction_points(edge, junctions, offset)
            if segment.get_actual_target() is target:
                if _graph_of(target.owner) is not segment.graph:
                    offset = Vec2()
                    change_coordinate_system(offset, _graph_of(target.owner), reference)
                original.properties['TARGET_OFFSET'] = offset
            copy_labels_back(edge, original, reference)
            dummy_edges.add(edge)
        set_source(original, source)
        set_target(original, target)
    for edge in dummy_edges.values():
        set_source(edge, None)
        set_target(edge, None)
    monitor.done()
