# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# HOST18/root/longest-path-source-review-01, complete two layerer variants.
"""Actual longest-path layerers with explicit native continuation frames.

Only raw non-self cyclic phase input has an explicit host failure boundary:
RecursionError replaces runtime stack exhaustion, without geometry fallback or
success cleanup. Normal pipeline cycle breaking remains the caller's task.
"""
from .graph import Layer,set_layer
from ...execution.diagnostics import BasicProgressMonitor


_CONFIGURATIONS={}


def _configuration(source_directed):
    if source_directed not in _CONFIGURATIONS:
        from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as Strategy
        p1,p2,p3,_,_=tuple(LayeredPhase)
        configuration=LayoutProcessorConfiguration()
        configuration.add_before(p1,Strategy.EDGE_AND_LAYER_CONSTRAINT_EDGE_REVERSER)
        configuration.add_before(p2,Strategy.LAYER_CONSTRAINT_PREPROCESSOR)
        configuration.add_before(p3,Strategy.LAYER_CONSTRAINT_POSTPROCESSOR)
        _CONFIGURATIONS[source_directed]=configuration
    return _CONFIGURATIONS[source_directed]


class _LongestPath:
    source_directed=False

    def __init__(self):
        _configuration(self.source_directed)
        self.layered_graph=None
        self.node_heights=None

    def get_layout_processor_configuration(self,graph):
        return _configuration(self.source_directed)

    def _neighbors(self,node):
        for port in node.ports:
            if self.source_directed:
                for edge in port.incoming_edges:yield edge.source.owner
            else:
                for edge in port.outgoing_edges:yield edge.target.owner

    def _put_node(self,node,height):
        graph=self.layered_graph;layers=graph.layers
        for _ in range(len(layers),height):
            if self.source_directed:layers.append(Layer(graph))
            else:layers.insert(0,Layer(graph))
        index=height-1 if self.source_directed else len(layers)-height
        set_layer(node,layers[index])
        self.node_heights[node.id]=height

    def _visit(self,node):
        height=self.node_heights[node.id]
        if height>=0:return height
        # Each frame owns the original iterator and its pending Math.max
        # continuation. Memoization happens only after actual setLayer.
        frames=[[node,self._neighbors(node),1]];active={id(node)}
        while frames:
            current,iterator,_=frames[-1]
            try:neighbor=next(iterator)
            except StopIteration:
                height=frames[-1][2]
                self._put_node(current,height)
                active.remove(id(current));frames.pop()
                if frames:frames[-1][2]=max(frames[-1][2],height+1)
                else:return height
                continue
            if neighbor is current:continue
            height=self.node_heights[neighbor.id]
            if height>=0:
                frames[-1][2]=max(frames[-1][2],height+1)
            else:
                if id(neighbor)in active:
                    raise RecursionError('A raw non-self cycle has no finite longest-path height')
                active.add(id(neighbor))
                frames.append([neighbor,self._neighbors(neighbor),1])

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Longest path to source layering'if self.source_directed else'Longest path layering',1)
        self.layered_graph=graph;nodes=graph.layerless_nodes
        self.node_heights=[-1]*len(nodes)
        for index,node in enumerate(nodes):node.id=index
        for node in nodes:self._visit(node)
        nodes.clear()
        self.layered_graph=None
        self.node_heights=None
        monitor.done()


class LongestPathLayerer(_LongestPath):
    source_name='LongestPathLayerer'


class LongestPathSourceLayerer(_LongestPath):
    source_name='LongestPathSourceLayerer'
    source_directed=True
