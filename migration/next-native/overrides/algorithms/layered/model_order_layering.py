# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf.
# Actual BF50945-51043 / DF51260-51476 model-order layering algorithms.
"""Actual model-order layer assignment, including label-dummy deferral."""
from .graph import Layer,set_layer
from .ports import _source_sort
from .native_adapters import _stored_key
from ...execution.diagnostics import BasicProgressMonitor


_CONFIGURATIONS={}


def _configuration(kind):
    if kind not in _CONFIGURATIONS:
        from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
        from .phase_factories import IntermediateProcessorStrategy as Strategy
        p1,p2,p3,_,_=tuple(LayeredPhase);cfg=LayoutProcessorConfiguration()
        cfg.add_before(p1,Strategy.EDGE_AND_LAYER_CONSTRAINT_EDGE_REVERSER)
        cfg.add_before(p2,Strategy.LAYER_CONSTRAINT_PREPROCESSOR)
        cfg.add_before(p3,Strategy.LAYER_CONSTRAINT_POSTPROCESSOR)
        _CONFIGURATIONS[kind]=cfg
    return _CONFIGURATIONS[kind]


def _incoming(node):
    lists=[port.incoming_edges for port in node.ports]
    return(edge for edges in lists for edge in edges)


def _at(values,index):
    if index<0 or index>=len(values):raise IndexError('Layer index out of bounds')
    return values[index]


def _compare_model_order(first,second,kind):
    left=_stored_key(first,'MODEL_ORDER');right=_stored_key(second,'MODEL_ORDER')
    if left is None or right is None:
        raise ValueError('The '+kind+' model order layer assigner requires all real nodes to have a model order.')
    a=first.properties[left];b=second.properties[right]
    if type(a)is not int or type(b)is not int:raise TypeError('Actual Integer model orders are required')
    return -1 if a<b else 1 if a>b else 0


def _remove_empty_layers(graph):
    graph.layers[:]=[layer for layer in graph.layers if layer.nodes]
    for index,layer in enumerate(graph.layers):layer.id=index


class BreadthFirstModelOrderLayerer:
    source_name='BreadthFirstModelOrderLayerer'

    def __init__(self):
        _configuration('BF');self.layered_graph=None

    def get_layout_processor_configuration(self,graph):return _configuration('BF')

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Breadth first model order layering',1)
        self.layered_graph=graph
        nodes=[node for node in graph.layerless_nodes if node.type=='NORMAL']
        # Missing orders fail only if the actual source sort invokes compare.
        _source_sort(nodes,lambda a,b:_compare_model_order(a,b,'BF'))
        first=True;current=Layer(graph);dummy=None;graph.layers.append(current)
        for node in nodes:
            if first:
                set_layer(node,current);first=False
            else:
                for edge in _incoming(node):
                    source=edge.source.owner
                    if (source.type=='NORMAL'and source.layer is current
                            or source.type=='LABEL'and next(_incoming(source)).source.owner.layer is current):
                        dummy=Layer(graph);graph.layers.append(dummy)
                        current=Layer(graph);graph.layers.append(current)
                for edge in _incoming(node):
                    source=edge.source.owner
                    if source.type=='LABEL'and source.layer is None:set_layer(source,dummy)
                set_layer(node,current)
        graph.layerless_nodes.clear()
        _remove_empty_layers(graph)
        monitor.done()


class DepthFirstModelOrderLayerer:
    source_name='DepthFirstModelOrderLayerer'

    def __init__(self):
        _configuration('DF');self.layered_graph=None
        self.current_layer=None;self.current_dummy_layer=None
        self.current_layer_id=0;self.max_to_place=0;self.nodes_to_place=[]

    def get_layout_processor_configuration(self,graph):return _configuration('DF')

    def _add_node_to_layer(self,layer_id,node):
        graph=self.layered_graph
        if layer_id<len(graph.layers):
            self.current_layer=_at(graph.layers,layer_id)
            self.current_dummy_layer=_at(graph.layers,layer_id-1)
            self.current_layer_id=layer_id
        else:
            self.current_dummy_layer=Layer(graph);self.current_dummy_layer.id=layer_id-1
            graph.layers.append(self.current_dummy_layer)
            self.current_layer=Layer(graph);self.current_layer.id=layer_id
            graph.layers.append(self.current_layer);self.current_layer_id=layer_id
        set_layer(node,self.current_layer)
        for edge in _incoming(node):
            source=edge.source.owner
            if source.layer is None and source.type=='LABEL':set_layer(source,self.current_dummy_layer)

    @staticmethod
    def _max_connected_layer(layer_id,node):
        maximum=layer_id
        for edge in _incoming(node):
            layer=edge.source.owner.layer
            if layer is not None:maximum=max(maximum,layer.id)
        return maximum

    def _connected_to_current(self,node):
        for edge in _incoming(node):
            source=edge.source.owner
            if not self.nodes_to_place:
                direct=source.type=='NORMAL'and source.layer is not None and source.layer.id==self.current_layer_id
                first=next(_incoming(source),None)
                if first is not None:
                    connected_layer=first.source.owner.layer
                    via_label=source.type=='LABEL'and connected_layer is not None and connected_layer.id==self.current_layer_id
                else:via_label=False
            else:
                direct=source.type=='NORMAL'and source.id==self.current_layer_id
                via_label=source.type=='LABEL'and next(_incoming(source)).source.owner.id==self.current_layer_id
            if direct or via_label:return True
        return False

    def _place_nodes_to_place(self):
        self.max_to_place=0
        graph=self.layered_graph
        for node in self.nodes_to_place:
            if node.id>=len(graph.layers):
                dummy=Layer(graph);dummy.id=node.id-1;graph.layers.append(dummy)
                layer=Layer(graph);layer.id=node.id;graph.layers.append(layer)
            set_layer(node,_at(graph.layers,node.id))

    def process(self,graph,monitor=None):
        monitor=monitor if monitor is not None else BasicProgressMonitor(False,False)
        monitor.begin('Depth first model order layering',1)
        self.layered_graph=graph
        nodes=[node for node in graph.layerless_nodes if node.type=='NORMAL']
        _source_sort(nodes,lambda a,b:_compare_model_order(a,b,'DF'))
        first=True;self.current_layer=Layer(graph);self.current_dummy_layer=None
        graph.layers.append(self.current_layer);self.current_layer.id=0
        self.current_layer_id=0;self.nodes_to_place=[]
        for node in nodes:
            if first:
                set_layer(node,self.current_layer);first=False
            elif self._connected_to_current(node):
                maximum=self._max_connected_layer(self.current_layer_id,node)
                desired=maximum+2;difference=maximum-self.current_layer_id
                if not self.nodes_to_place:self._add_node_to_layer(desired,node)
                elif difference>0:
                    for pending in self.nodes_to_place:pending.id+=maximum-self.max_to_place
                    self._place_nodes_to_place();self.nodes_to_place.clear()
                    self._add_node_to_layer(desired,node)
                else:
                    self.nodes_to_place.append(node);node.id=desired
                    self.max_to_place=max(self.max_to_place,desired)
                    for edge in _incoming(node):
                        source=edge.source.owner
                        if source.layer is None and source.type=='LABEL':
                            self.nodes_to_place.append(source);source.id=desired-1
                    self.current_layer_id=desired
            else:
                self._place_nodes_to_place();self.nodes_to_place.clear()
                if next(_incoming(node),None)is not None:
                    maximum=self._max_connected_layer(0,node)
                    self._add_node_to_layer(maximum+2,node)
                else:
                    self.nodes_to_place.append(node);node.id=0
                    self.max_to_place=max(self.max_to_place,0)
                    self.current_layer=_at(graph.layers,0);self.current_layer_id=0
        if self.nodes_to_place:self._place_nodes_to_place()
        graph.layerless_nodes.clear()
        _remove_empty_layers(graph)
        monitor.done()
