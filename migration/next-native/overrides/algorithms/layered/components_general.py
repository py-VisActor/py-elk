# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. elkjs0.12.1 worker275e6caf,
# ComponentsProcessor30926-31026/SimpleRow31179-31338/moves29973-30025.
# HOST-13/B/components-general-source-review-01.json; subsequent component-group
# placers and connected compaction have their own implementation modules.
"""General component DFS, shallow split, four placers and connected compaction."""
import math
from .graph import LGraph,Vec2
from .native_properties import CanonicalPropertyMap
from .native_adapters import _read_property
from .property_access import read_layered_scalar
from .ports import _source_sort,double_compare
from .placement import _max as _maximum


def _read(holder,name,symbol):return read_layered_scalar(holder,name,symbol)


def _minimum_order(graph):
    order=2147483647
    for node in graph.layerless_nodes:
        if 'MODEL_ORDER'in node.properties:order=min(order,node.properties['MODEL_ORDER'])
    return order


def _copy_properties(target,source):
    if not isinstance(target.properties,CanonicalPropertyMap):
        target.properties=CanonicalPropertyMap(target.properties)
    target.properties.update(source.properties)
    target.integer_box_identities=target.properties.integer_boxes


def _copy_padding(target,source):
    target.padding.top=source.padding.top;target.padding.right=source.padding.right
    target.padding.bottom=source.padding.bottom;target.padding.left=source.padding.left


def _offset_nodes(graph,vector):
    for node in graph.layerless_nodes:
        node.pos.x+=vector.x;node.pos.y+=vector.y
        for port in node.ports:
            for edge in port.outgoing_edges:
                for point in edge.bend_points:point.x+=vector.x;point.y+=vector.y
                junctions=_read_property(edge,'JUNCTION_POINTS')
                if junctions is not None:
                    for point in junctions:point.x+=vector.x;point.y+=vector.y
                for label in edge.labels:label.pos.x+=vector.x;label.pos.y+=vector.y


def offset_graph(graph,x,y):_offset_nodes(graph,Vec2(x,y))


def move_graph(target,source,x=0.0,y=0.0):
    source.offset.x+=x;source.offset.y+=y
    _offset_nodes(source,source.offset)
    for node in source.layerless_nodes:
        target.layerless_nodes.append(node);node.graph=target


class SimpleRowGraphPlacer:
    def sort_components(self,components,target):
        if _read(target,'CONSIDER_MODEL_ORDER_COMPONENTS','CONSIDER_MODEL_ORDER_COMPONENTS_0')=='NONE':
            for graph in components:
                priority=0.0
                for node in graph.layerless_nodes:priority+=float(_read(node,'PRIORITY','PRIORITY_0'))
                graph.id=priority
            def compare(first,second):
                priority=second.id-first.id
                return priority if priority!=0 else double_compare(first.size.x*first.size.y,second.size.x*second.size.y)
            _source_sort(components,compare)

    def place_components(self,components,target,max_row_width,spacing):
        x=y=highest=0.0;broadest=spacing
        for graph in components:
            if x+graph.size.x>max_row_width:
                x=0.0;y+=highest+spacing;highest=0.0
            offset_graph(graph,x+graph.offset.x,y+graph.offset.y)
            graph.offset.x=0.0;graph.offset.y=0.0
            broadest=_maximum(broadest,x+graph.size.x);highest=_maximum(highest,graph.size.y)
            x+=graph.size.x+spacing
        target.size.x=broadest;target.size.y=y+highest

    def combine(self,components,target):
        if len(components)==1:
            source=components[0]
            if source is not target:
                target.layerless_nodes.clear();move_graph(target,source)
                _copy_properties(target,source);_copy_padding(target,source)
                target.size.x=source.size.x;target.size.y=source.size.y
            return
        if not components:
            target.layerless_nodes.clear();target.size.x=0.0;target.size.y=0.0;return
        self.sort_components(components,target)
        first=components[0];target.layerless_nodes.clear();_copy_properties(target,first)
        width=area=0.0
        for graph in components:
            width=_maximum(width,graph.size.x);area+=graph.size.x*graph.size.y
        root=math.sqrt(area)if area>=0 else math.nan
        width=_maximum(width,root*_read(target,'ASPECT_RATIO','ASPECT_RATIO_1'))
        spacing=_read(target,'SPACING_COMPONENT_COMPONENT','SPACING_COMPONENT_COMPONENT_0')
        self.place_components(components,target,width,spacing)
        if _read(first,'COMPACTION_CONNECTED_COMPONENTS','COMPACTION_CONNECTED_COMPONENTS_0'):
            from .connected_compactor import compact_components
            compact_components(components,target,spacing)
        for graph in components:move_graph(target,graph)


class ComponentsProcessor:
    def __init__(self):
        from .component_groups import (ComponentGroupGraphPlacer,ComponentGroupModelOrderGraphPlacer,
                                       ModelOrderRowGraphPlacer)
        self.component_group_graph_placer=ComponentGroupGraphPlacer()
        self.component_group_model_order_graph_placer=ComponentGroupModelOrderGraphPlacer()
        self.model_order_row_graph_placer=ModelOrderRowGraphPlacer()
        self.simple_row_graph_placer=SimpleRowGraphPlacer();self.graph_placer=None

    @staticmethod
    def _neighbors(node):
        for port in node.ports:
            for edge in port.incoming_edges:yield edge.source.owner
            for edge in port.outgoing_edges:yield edge.target.owner

    def _component(self,node):
        if node.id!=0:return None
        members=[];sides=set()
        def enter(current):
            current.id=1;members.append(current)
            if current.type=='EXTERNAL_PORT':sides.add(_read_property(current,'EXT_PORT_SIDE'))
            return iter(self._neighbors(current))
        frames=[enter(node)]
        while frames:
            other=next(frames[-1],None)
            if other is None:frames.pop()
            elif other.id==0:frames.append(enter(other))
        return members,sides

    def split(self,graph):
        self.graph_placer=self.simple_row_graph_placer
        separate=_read(graph,'SEPARATE_CONNECTED_COMPONENTS','SEPARATE_CONNECTED_COMPONENTS_0')
        separate=separate is None or separate
        external='EXTERNAL_PORTS'in _read_property(graph,'GRAPH_PROPERTIES')
        constraints=_read_property(graph,'PORT_CONSTRAINTS')
        compatible=constraints not in('FIXED_ORDER','FIXED_RATIO','FIXED_POS')
        if separate and(compatible or not external):
            for node in graph.layerless_nodes:node.id=0
            result=[]
            for node in graph.layerless_nodes:
                data=self._component(node)
                if data is None:continue
                members,sides=data
                child=LGraph(None,None,None);_copy_properties(child,graph)
                child.properties['EXT_PORT_CONNECTIONS']=sides;_copy_padding(child,graph)
                child.properties['NODE_SIZE_MINIMUM']=None
                child.random=child.properties.get('RANDOM')
                for name in('_source_session','identity_hash'):
                    if hasattr(graph,name):setattr(child,name,getattr(graph,name))
                child.layerless_nodes.extend(members)
                for member in members:member.graph=child
                result.append(child)
            if external:
                order=_read(graph,'CONSIDER_MODEL_ORDER_COMPONENTS','CONSIDER_MODEL_ORDER_COMPONENTS_0')
                self.graph_placer=(self.component_group_model_order_graph_placer if order=='GROUP_MODEL_ORDER'
                                   else self.model_order_row_graph_placer if order=='MODEL_ORDER'
                                   else self.component_group_graph_placer)
        else:result=[graph]
        if _read(graph,'CONSIDER_MODEL_ORDER_COMPONENTS','CONSIDER_MODEL_ORDER_COMPONENTS_0')!='NONE':
            def compare(first,second):
                a,b=_minimum_order(first),_minimum_order(second)
                return -1 if a<b else 1 if a>b else 0
            _source_sort(result,compare)
        return result

    def combine(self,components,target):return self.graph_placer.combine(components,target)
