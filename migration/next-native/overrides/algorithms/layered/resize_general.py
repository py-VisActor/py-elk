# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. elkjs0.12.1 worker275e6caf,
# cleanup28301-28310 / resizeGraph28314-28349. Independent source approval:
# HOST-13/B/resize-general-source-review-01.json.
"""Actual Layered cleanup and final size adjustment over native graph fields."""
from .graph import Vec2,set_layer
from .native_adapters import _read_property
from .placement import _max as _maximum


def clear_layers(graph):
    for layer in graph.layers:
        graph.layerless_nodes.extend(layer.nodes)
        layer.nodes.clear()
    for node in graph.layerless_nodes:set_layer(node,None)
    graph.layers.clear()


def resize_graph(graph):
    constraints=_read_property(graph,'NODE_SIZE_CONSTRAINTS')
    options=_read_property(graph,'NODE_SIZE_OPTIONS')
    calculated=Vec2(graph.size.x+graph.padding.left+graph.padding.right,
                    graph.size.y+graph.padding.top+graph.padding.bottom)
    adjusted=Vec2(calculated.x,calculated.y)
    if 'MINIMUM_SIZE'in constraints:
        minimum=_read_property(graph,'NODE_SIZE_MINIMUM')
        if 'DEFAULT_MINIMUM_SIZE'in options:
            if minimum.x<=0:minimum.x=20.0
            if minimum.y<=0:minimum.y=20.0
        adjusted.x=_maximum(calculated.x,minimum.x)
        adjusted.y=_maximum(calculated.y,minimum.y)
    if not _read_property(graph,'NODE_SIZE_FIXED_GRAPH_SIZE'):
        resize_graph_no_really(graph,calculated,adjusted)


def resize_graph_no_really(graph,old_size,new_size):
    alignment=_read_property(graph,'CONTENT_ALIGNMENT')
    if new_size.x>old_size.x:
        if 'H_CENTER'in alignment:graph.offset.x+=(new_size.x-old_size.x)/2
        elif 'H_RIGHT'in alignment:graph.offset.x+=new_size.x-old_size.x
    if new_size.y>old_size.y:
        if 'V_CENTER'in alignment:graph.offset.y+=(new_size.y-old_size.y)/2
        elif 'V_BOTTOM'in alignment:graph.offset.y+=new_size.y-old_size.y
    if 'EXTERNAL_PORTS'in _read_property(graph,'GRAPH_PROPERTIES')and(new_size.x>old_size.x or new_size.y>old_size.y):
        for node in graph.layerless_nodes:
            if node.type=='EXTERNAL_PORT':
                side=_read_property(node,'EXT_PORT_SIDE')
                if side=='EAST':node.pos.x+=new_size.x-old_size.x
                elif side=='SOUTH':node.pos.y+=new_size.y-old_size.y
    graph.size.x=new_size.x-graph.padding.left-graph.padding.right
    graph.size.y=new_size.y-graph.padding.top-graph.padding.bottom
