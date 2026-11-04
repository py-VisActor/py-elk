# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed worker51477-51601.
"""Actual horizontal-span interactive layering and ordered downstream shifts."""
from dataclasses import dataclass,field
from .graph import Layer,set_layer
from .strategy_collections import NodeIdentities,LinkedNodes,baseline_configuration
from ..radial import _maximum
from ..triangulation import _minimum
from ...execution.diagnostics import BasicProgressMonitor


@dataclass(eq=False)
class _Span:
    start:float=0.0
    end:float=0.0
    nodes:list=field(default_factory=list)


class InteractiveLayerer(NodeIdentities):
    source_name='InteractiveLayerer'

    def get_layout_processor_configuration(self,graph):
        return baseline_configuration('INTERACTIVE_EXTERNAL_PORT_POSITIONER')

    def _check_node(self,node,graph):
        node.id=1;first_layer=node.layer;shifted=LinkedNodes(self)
        for port in node.ports:
            if not port.outgoing_edges:continue
            for edge in port.outgoing_edges:
                target=edge.target.owner
                if node is target:continue
                if target.layer.id<=first_layer.id:
                    index=first_layer.id+1
                    if index==len(graph.layers):
                        layer=Layer(graph);layer.id=index;graph.layers.append(layer)
                    else:layer=graph.layers[index]
                    set_layer(target,layer);shifted.add(target)
        return shifted

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Interactive node layering',1);self._identity_graph=graph
        spans=[]
        for node in graph.layerless_nodes:
            minimum=node.pos.x;maximum=_maximum(minimum+1,minimum+node.size.x)
            index=0;found=None
            while index<len(spans):
                span=spans[index];index+=1
                if span.start>=maximum:index-=1;break
                elif span.end>minimum:
                    if found is None:
                        span.nodes.append(node);span.start=_minimum(span.start,minimum)
                        span.end=_maximum(span.end,maximum);found=span
                    else:
                        found.nodes.extend(span.nodes);found.end=_maximum(found.end,span.end)
                        del spans[index-1];index-=1
            if found is None:spans.insert(index,_Span(minimum,maximum,[node]))
        for index,span in enumerate(spans):
            layer=Layer(graph);layer.id=index;graph.layers.append(layer)
            for node in span.nodes:set_layer(node,layer);node.id=0
        for node in graph.layerless_nodes:
            if node.id!=0:continue
            shifted=self._check_node(node,graph)
            while shifted:
                following=shifted.values()[0];shifted.remove(following)
                shifted.update(self._check_node(following,graph))
        graph.layers[:]=[layer for layer in graph.layers if layer.nodes]
        graph.layerless_nodes.clear();self._identity_graph=None
        monitor.done()
