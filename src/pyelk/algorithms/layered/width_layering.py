# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed worker51756-51971/52100-52330.
"""Actual MinWidth and StretchWidth layerers with source floating arithmetic."""
import math
from .graph import Layer,set_layer
from .ports import _source_sort
from .property_access import read_layered_scalar
from .strategy_collections import NodeIdentities,NodeSet,LinkedNodes,incoming,outgoing,baseline_configuration
from ..fixed import _div
from ..radial import _maximum
from ..triangulation import _minimum
from ...execution.diagnostics import BasicProgressMonitor


def _count_nonself(edges):return sum(edge.source.owner is not edge.target.owner for edge in edges)


class MinWidthLayerer(NodeIdentities):
    source_name='MinWidthLayerer'

    def __init__(self):
        super().__init__();self.avg_size=0.0;self.dummy_size=0.0;self.minimum_node_size=0.0
        self.in_degree=[];self.out_degree=[];self.normalized_size=[]

    def get_layout_processor_configuration(self,graph):return baseline_configuration()

    @staticmethod
    def _select(nodes,successors,targets):
        for node in nodes.values():
            if all(targets.contains(target)for target in successors[node.id].values()):return node
        return None

    def _compute(self,upper,compensator,nodes,successors):
        layers=[];unplaced=LinkedNodes(self,nodes);consider_size=upper*self.avg_size
        in_degree=0;out_degree=0;current_nodes=NodeSet(self);other_nodes=NodeSet(self)
        current=[];width_current=0.0;width_up=0.0;maximum=0.0;real_width=0.0
        spanning=0.0;going_out=0.0
        while unplaced:
            node=self._select(unplaced,successors,other_nodes)
            if node is not None:
                unplaced.remove(node);current.append(node);current_nodes.add(node)
                out_degree=self.out_degree[node.id]
                width_current+=self.normalized_size[node.id]-out_degree*self.dummy_size
                in_degree=self.in_degree[node.id];width_up+=in_degree*self.dummy_size
                going_out+=out_degree*self.dummy_size;real_width+=self.normalized_size[node.id]
            if (node is None or not unplaced
                    or width_current>=consider_size and self.normalized_size[node.id]>out_degree*self.dummy_size
                    or width_up>=compensator*consider_size):
                layers.append(current);current=[];other_nodes.update(current_nodes);current_nodes.clear()
                spanning-=going_out
                maximum=_maximum(maximum,spanning*self.dummy_size+real_width)
                spanning+=width_up;width_current=width_up;width_up=0.0;going_out=0.0;real_width=0.0
        return maximum,layers

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('MinWidth layering',1);self._identity_graph=graph
        nodes=graph.layerless_nodes
        upper=read_layered_scalar(graph,'LAYERING_MIN_WIDTH_UPPER_BOUND_ON_WIDTH','LAYERING_MIN_WIDTH_UPPER_BOUND_ON_WIDTH_0')
        compensator=read_layered_scalar(graph,'LAYERING_MIN_WIDTH_UPPER_LAYER_ESTIMATION_SCALING_FACTOR','LAYERING_MIN_WIDTH_UPPER_LAYER_ESTIMATION_SCALING_FACTOR_0')
        self.dummy_size=read_layered_scalar(graph,'SPACING_EDGE_EDGE','SPACING_EDGE_EDGE')
        self.minimum_node_size=math.inf
        for node in nodes:
            if node.type=='NORMAL':self.minimum_node_size=_minimum(self.minimum_node_size,node.size.y)
        self.minimum_node_size=_maximum(1.0,self.minimum_node_size)
        count=len(nodes);self.in_degree=[0]*count;self.out_degree=[0]*count;self.normalized_size=[0.0]*count
        self.avg_size=0.0
        for index,node in enumerate(nodes):
            node.id=index;self.in_degree[index]=_count_nonself(incoming(node));self.out_degree[index]=_count_nonself(outgoing(node))
            self.normalized_size[index]=_div(node.size.y,self.minimum_node_size);self.avg_size+=self.normalized_size[index]
        self.dummy_size=_div(self.dummy_size,self.minimum_node_size);self.avg_size=_div(self.avg_size,count)
        successors=[]
        for node in nodes:
            targets=NodeSet(self)
            for edge in outgoing(node):
                if edge.source.owner is not edge.target.owner:targets.add(edge.target.owner)
            successors.append(targets)
        _source_sort(nodes,lambda a,b:-((self.out_degree[a.id]>self.out_degree[b.id])-(self.out_degree[a.id]<self.out_degree[b.id])))
        minimum=math.inf;minimum_layers=2147483647;candidate=None
        uppers=range(1,5)if upper<0 else range(upper,upper+1)
        compensators=range(1,3)if compensator<0 else range(compensator,compensator+1)
        for width in uppers:
            for multiplier in compensators:
                actual_width,layering=self._compute(width,multiplier,nodes,successors)
                if actual_width<minimum or actual_width==minimum and len(layering)<minimum_layers:
                    minimum=actual_width;minimum_layers=len(layering);candidate=layering
        for values in candidate:
            layer=Layer(graph)
            for node in values:set_layer(node,layer)
            graph.layers.append(layer)
        graph.layers.reverse();nodes.clear();self._identity_graph=None;monitor.done()


class StretchWidthLayerer(NodeIdentities):
    source_name='StretchWidthLayerer'

    def __init__(self):
        super().__init__();self.already_placed_nodes=NodeSet(self);self.already_placed_in_other_layers=NodeSet(self)
        self.current_graph=None;self.width_current=0.0;self.width_up=0.0
        self.minimum_node_size=0.0;self.maximum_node_size=0.0;self.dummy_size=0.0;self.max_width=0.0
        self.upper_layer_influence=0.0;self.sorted_nodes=[];self.successors=[]
        self.in_degree=[];self.out_degree=[];self.normalized_size=[];self.temporary_nodes=[];self.remaining_outgoing=[]
        self.selected_node=None

    def get_layout_processor_configuration(self,graph):return baseline_configuration()

    @staticmethod
    def _rank(node):
        result=sum(1 for _ in outgoing(node))
        for edge in incoming(node):result=max(result,sum(1 for _ in outgoing(edge.source.owner)))
        return result

    def _compute_sorted(self):
        self.sorted_nodes=list(self.current_graph.layerless_nodes)
        for node in self.current_graph.layerless_nodes:node.id=self._rank(node)
        _source_sort(self.sorted_nodes,lambda a,b:1 if a.id<b.id else -1 if a.id>b.id else 0)

    def _compute_successors(self):
        self.successors=[];current=NodeSet(self)
        for index,node in enumerate(self.sorted_nodes):
            node.id=index
            for edge in outgoing(node):current.add(edge.target.owner)
            current.remove(node);self.successors.append(NodeSet(self,current.values()));current.clear()

    def _go_up(self):
        index=self.selected_node.id
        a=self.width_current-self.out_degree[index]*self.dummy_size+self.normalized_size[index]>self.max_width
        b=self.width_up+self.in_degree[index]*self.dummy_size>self.max_width*self.upper_layer_influence*self.dummy_size
        return a or b

    def _select(self):
        return next((node for node in self.temporary_nodes if self.remaining_outgoing[node.id]<=0),None)

    def _update_outgoing(self,layer):
        for node in layer.nodes:
            for edge in incoming(node):self.remaining_outgoing[edge.source.owner.id]-=1

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('StretchWidth layering',1)
        if not graph.layerless_nodes:monitor.done();return
        self.current_graph=graph;self._identity_graph=graph;self.width_current=0.0;self.width_up=0.0
        self.minimum_node_size=math.inf;self.maximum_node_size=-math.inf
        self.dummy_size=read_layered_scalar(graph,'SPACING_EDGE_EDGE','SPACING_EDGE_EDGE')
        self._compute_sorted();self._compute_successors();count=len(self.sorted_nodes)
        self.in_degree=[0]*count;self.out_degree=[0]*count
        for node in self.sorted_nodes:
            self.in_degree[node.id]=sum(1 for _ in incoming(node));self.out_degree[node.id]=sum(1 for _ in outgoing(node))
        for node in self.sorted_nodes:
            if node.type=='NORMAL':
                self.minimum_node_size=_minimum(self.minimum_node_size,node.size.y)
                self.maximum_node_size=_maximum(self.maximum_node_size,node.size.y)
        # Source normalizes before clamping the size extrema to at least1.
        self.normalized_size=[0.0]*count
        for node in self.sorted_nodes:self.normalized_size[node.id]=_div(node.size.y,self.minimum_node_size)
        self.minimum_node_size=_maximum(1.0,self.minimum_node_size);self.maximum_node_size=_maximum(1.0,self.maximum_node_size)
        self.dummy_size=_div(self.dummy_size,self.minimum_node_size);self.max_width=_div(self.maximum_node_size,self.minimum_node_size)
        self.upper_layer_influence=_div(sum(sum(1 for _ in outgoing(node))for node in graph.layerless_nodes),len(graph.layerless_nodes))
        current=Layer(graph);graph.layers.append(current);self.temporary_nodes=list(self.sorted_nodes);self.remaining_outgoing=list(self.out_degree)
        while self.temporary_nodes:
            self.selected_node=self._select()
            if self.selected_node is None or self._go_up()and self.already_placed_nodes:
                self._update_outgoing(current);current=Layer(graph);graph.layers.append(current)
                self.already_placed_in_other_layers.update(self.already_placed_nodes);self.already_placed_nodes.clear()
                self.width_current=self.width_up;self.width_up=0.0
            elif self._go_up():
                graph.layers.clear();current=Layer(graph);graph.layers.append(current)
                self.width_current=0.0;self.width_up=0.0;self.already_placed_nodes.clear();self.already_placed_in_other_layers.clear()
                self.max_width+=1;self.temporary_nodes=list(self.sorted_nodes);self.remaining_outgoing=list(self.out_degree)
            else:
                node=self.selected_node;set_layer(node,current)
                for index,old in enumerate(self.temporary_nodes):
                    if old is node:del self.temporary_nodes[index];break
                self.already_placed_nodes.add(node)
                self.width_current=self.width_current-self.out_degree[node.id]*self.dummy_size+self.normalized_size[node.id]
                self.width_up+=self.in_degree[node.id]*self.dummy_size
        graph.layerless_nodes.clear();graph.layers.reverse();monitor.done()
