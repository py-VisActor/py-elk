# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed elkjs0.12.1 worker275e6caf,
# LGraphAdapters32102-32474; HOST12/root native-adapter source reviews.
"""Live native Layered adapter views, separate from raw JSON adapters.

Geometry getters expose the actual native vectors. Collection adapters cache
their first snapshot, just as their source counterparts do. No geometry is
reconstructed from ORIGIN or from the older raw node_micro adapter.
"""
from collections.abc import MutableMapping

from ..._errors import UnsupportedOptionError
from ...execution.properties import PropertySnapshot
from ...execution.node_micro import VectorChain,_ENUMSET_DEFAULTS,_union
from ...execution.diagnostics import BasicProgressMonitor
from ...options._core_defaults import CORE_SCALAR_DEFAULTS
from .native_properties import canonical_property_key,CanonicalPropertyMap
from .graph import Insets,Vec2
from .ports import _source_sort,double_compare
from .property_access import read_layered_scalar
from .cell_layout import _maximum

_ABSENT=object()
_EMPTY=()
_INTERNAL_DEFAULTS={'compoundNode':False,'insideConnections':False,'portDummy':None,
                    'selfLoopHolder':None,'TopSideComments':None,'BottomSideComments':None,
                    'externalPortSide':'UNDEFINED',
                    # Actual InternalProperties_1 declarations48636-48705.
                    'origin':None,'coordinateOrigin':None,'processors':None,
                    'originalBendpoints':None,'originalDummyNodePosition':None,
                    'originalLabelEdge':None,'representedLabels':None,
                    'endLabels':None,'endLabel.origin':None,'labelSide':'UNKNOWN',
                    'maxEdgeThickness':0,'reversed':False,'random':None,
                    'longEdgeSource':None,'longEdgeTarget':None,
                    'longEdgeHasLabelDummies':False,'longEdgeBeforeLabelDummy':False,
                    'edgeConstraint':'NONE','inLayerLayoutUnit':None,'inLayerConstraint':'NONE',
                    'inLayerSuccessorConstraintBetweenNonDummies':False,'crossingHint':0,
                    'externalPortReplacedDummies':None,'externalPortReplacedDummy':None,
                    'portRatioOrPosition':0,'barycenterAssociates':None,
                    'CommentConnectionPort':None,'inputCollect':False,'outputCollect':False,
                    'cyclic':False,'crossHierarchyMap':None,'targetOffset':None,
                    'spacings':None,'partitionConstraint':False,'breakingPoint.info':None,
                    'splines.survivingEdge':None,'splines.route.start':None,
                    'splines.edgeChain':None,'originalPortConstraints':None,
                    'splines.nsPortY':None,'modelOrder':None,'modelOrder.maximum':None,
                    'modelOrderGroups.cb.number':None,'longEdgeTargetNode':None,
                    'firstTryWithInitialOrder':False,'layerConstraints.hiddenNodes':None,
                    'layerConstraints.opposidePort':None,'targetNode.modelOrder':None,
                    'tarjan.lowlink':2147483647,'tarjan.id':-1,'tarjan.onstack':False,
                    'partOfCycle':False,'medianHeuristic.weight':None}
_INTERNAL_SHARED_DEFAULTS={'inLayerSuccessorConstraint':[]}
_INTERNAL_FACTORIES={'externalPortSize':Vec2,'splineLabelSize':Vec2}
_LAYERED_SCALAR_DEFAULTS=None
_CORE_NULL_IDS=frozenset('org.eclipse.elk.'+name for name in (
    'port.anchor','position','bendPoints','resolvedAlgorithm','spacing.individual',
    'labelManager','labels.labelManager'))
_CORE_FACTORIES={
    'org.eclipse.elk.padding':lambda:Insets(12,12,12,12),
    'org.eclipse.elk.margins':Insets,
    'org.eclipse.elk.spacing.portsSurrounding':Insets,
    'org.eclipse.elk.nodeLabels.padding':lambda:Insets(5,5,5,5),
    'org.eclipse.elk.nodeSize.minimum':Vec2,
    'org.eclipse.elk.junctionPoints':VectorChain,
}


def _properties(element,create=False):
    values=getattr(element,'properties',None)
    if values is None and create:
        values=CanonicalPropertyMap();element.properties=values
    return values


def _stored_key(element,name):
    values=_properties(element);canonical=canonical_property_key(name)
    if values is None:return None
    if canonical in values:return canonical
    for key in values:
        if canonical_property_key(key)==canonical:return key
    return None


def _has_property(element,name):return _stored_key(element,name)is not None


def _read_property(element,name):
    key=_stored_key(element,name);values=_properties(element,True)
    if key is not None and values[key]is not None:return values[key]
    canonical=canonical_property_key(name)
    # Actual owner declarations, never generic metadata-declared defaults.
    temporary=PropertySnapshot({})
    if canonical in CORE_SCALAR_DEFAULTS:value=temporary.read_native(canonical)
    elif canonical in _CORE_NULL_IDS:value=temporary.read_native(canonical,None,materialize=False)
    elif canonical in _CORE_FACTORIES:
        value=temporary.read_native(canonical,factory=_CORE_FACTORIES[canonical],materialize=True)
    elif canonical in _INTERNAL_DEFAULTS:
        value=temporary.read_native(canonical,_INTERNAL_DEFAULTS[canonical],materialize=False)
    elif canonical in _INTERNAL_SHARED_DEFAULTS:
        value=temporary.read_native(canonical,factory=lambda:_INTERNAL_SHARED_DEFAULTS[canonical],materialize=False)
    elif canonical in _INTERNAL_FACTORIES:
        value=temporary.read_native(canonical,factory=_INTERNAL_FACTORIES[canonical],materialize=True)
    elif canonical=='graphProperties':
        # Actual InternalProperties EnumSet default is shared and not type4.
        value=temporary.read_native(canonical,factory=lambda:_ENUMSET_DEFAULTS.setdefault(
            '@InternalProperties:graphProperties',set()),materialize=False)
    elif canonical=='externalPortConnections':
        # Source48670: one shared empty EnumSet, without clone/cache.
        value=temporary.read_native(canonical,factory=lambda:_ENUMSET_DEFAULTS.setdefault(
            '@InternalProperties:externalPortConnections',set()),materialize=False)
    else:
        global _LAYERED_SCALAR_DEFAULTS
        if _LAYERED_SCALAR_DEFAULTS is None:
            from ...options._owner_data import OWNER_PROPERTY_DECLARATIONS
            from ...options.owners import scalar_owner_default
            _LAYERED_SCALAR_DEFAULTS={}
            for owner,symbol,identifier,*_ in OWNER_PROPERTY_DECLARATIONS:
                if owner!='LayeredOptions':continue
                try:_,default=scalar_owner_default(owner,symbol)
                except ValueError:continue
                _LAYERED_SCALAR_DEFAULTS[identifier]=default
        if canonical not in _LAYERED_SCALAR_DEFAULTS:
            raise UnsupportedOptionError('NATIVE_PROPERTY_DEFAULT_PENDING','/nativeProperties/'+canonical,
                                         'An actual Property owner declaration is required')
        value=temporary.read_native(canonical,_LAYERED_SCALAR_DEFAULTS[canonical],materialize=False)
    if temporary.has(canonical):values[canonical if key is None else key]=value
    return value


class _PropertyView(MutableMapping):
    def __init__(self,element):self.element=element
    def __getitem__(self,key):return _read_property(self.element,key)
    def __contains__(self,key):return _has_property(self.element,key)
    def __setitem__(self,key,value):
        values=_properties(self.element,True);actual=_stored_key(self.element,key)
        if actual is not None:del values[actual]
        if value is not None:values[canonical_property_key(key)]=value
    def __delitem__(self,key):
        actual=_stored_key(self.element,key)
        if actual is None:raise KeyError(key)
        del _properties(self.element)[actual]
    def __iter__(self):return iter(_properties(self.element)or{})
    def __len__(self):return len(_properties(self.element)or{})


class AbstractShapeAdapter:
    def __init__(self,element):self.element=element;self.properties=_PropertyView(element)
    @property
    def pos(self):return self.element.pos
    @pos.setter
    def pos(self,value):self.element.pos.x=value.x;self.element.pos.y=value.y
    @property
    def size(self):return self.element.size
    @size.setter
    def size(self,value):self.element.size.x=value.x;self.element.size.y=value.y
    @property
    def id(self):return self.element.id
    @id.setter
    def id(self,value):self.element.id=value
    def get_position(self):return self.pos
    def set_position(self,value):self.pos=value
    def get_size(self):return self.size
    def set_size(self,value):self.size=value
    def get_volatile_id(self):return self.id
    def set_volatile_id(self,value):self.id=value
    def get_property(self,name):return self.properties[name]
    def has_property(self,name):return name in self.properties


class LLabelAdapter(AbstractShapeAdapter):pass


class LEdgeAdapter:
    def __init__(self,element):self.element=element;self._labels=None
    @property
    def labels(self):
        if self._labels is None:self._labels=[LLabelAdapter(label)for label in getattr(self.element,'labels',())]
        return self._labels
    def get_labels(self):return self.labels


class LPortAdapter(AbstractShapeAdapter):
    def __init__(self,element,transparent_north_south_edges=False,owner=None):
        super().__init__(element);self.transparent_north_south_edges=transparent_north_south_edges
        self.owner=element.owner if owner is None else owner
        self._labels=None;self._incoming=None;self._outgoing=None
    @property
    def side(self):return self.element.side
    @property
    def labels(self):
        if self._labels is None:self._labels=[LLabelAdapter(label)for label in getattr(self.element,'labels',())]
        return self._labels
    def _edges(self,incoming):
        port=self.element
        if self.transparent_north_south_edges and port.owner.type=='NORTH_SOUTH_PORT':return _EMPTY
        cache='_incoming'if incoming else'_outgoing';cached=getattr(self,cache)
        if cached is None:
            cached=[];setattr(self,cache,cached)
            edges=port.incoming_edges if incoming else port.outgoing_edges
            cached.extend(LEdgeAdapter(edge)for edge in edges)
            if self.transparent_north_south_edges:
                dummy=_read_property(port,'PORT_DUMMY')
                if dummy is not None:
                    for p in dummy.ports:
                        edges=p.incoming_edges if incoming else p.outgoing_edges
                        cached.extend(LEdgeAdapter(edge)for edge in edges)
            if _has_property(port.owner,'SELF_LOOP_HOLDER'):
                holder=_read_property(port.owner,'SELF_LOOP_HOLDER')
                # Explicit agreed native ABI; missing fields are not empty.
                sl_port=holder.sl_ports.get(port)
                if sl_port is not None:
                    edges=sl_port.incoming_sl_edges if incoming else sl_port.outgoing_sl_edges
                    cached.extend(LEdgeAdapter(edge.l_edge)for edge in edges)
        return cached
    @property
    def incoming_edges(self):return self._edges(True)
    @property
    def outgoing_edges(self):return self._edges(False)
    def get_incoming_edges(self):return self.incoming_edges
    def get_outgoing_edges(self):return self.outgoing_edges
    def get_labels(self):return self.labels
    def get_side(self):return self.side
    def has_compound_connections(self):return self.properties['INSIDE_CONNECTIONS']


class LNodeAdapter(AbstractShapeAdapter):
    def __init__(self,parent,element,transparent_north_south_edges=False):
        super().__init__(element);self.graph=parent
        self.transparent_north_south_edges=transparent_north_south_edges
        self._labels=None;self._ports=None
    @property
    def type(self):return self.element.type
    @property
    def labels(self):
        if self._labels is None:self._labels=[LLabelAdapter(label)for label in getattr(self.element,'labels',())]
        return self._labels
    @property
    def ports(self):
        if self._ports is None:self._ports=[LPortAdapter(port,self.transparent_north_south_edges,self)for port in self.element.ports]
        return self._ports
    @property
    def incoming_edges(self):return _EMPTY
    @property
    def outgoing_edges(self):return _EMPTY
    @property
    def margin(self):
        value=self.element.margin;return Insets(value.top,value.right,value.bottom,value.left)
    @margin.setter
    def margin(self,value):
        target=self.element.margin;target.left=value.left;target.top=value.top
        target.right=value.right;target.bottom=value.bottom
    @property
    def padding(self):return self.element.padding
    @padding.setter
    def padding(self,value):
        target=self.element.padding;target.left=value.left;target.top=value.top
        target.right=value.right;target.bottom=value.bottom
    def get_graph(self):return self.graph
    def get_labels(self):return self.labels
    def get_ports(self):return self.ports
    def get_incoming_edges(self):return self.incoming_edges
    def get_outgoing_edges(self):return self.outgoing_edges
    def get_margin(self):return self.margin
    def set_margin(self,value):self.margin=value
    def set_padding(self,value):self.padding=value
    def is_compound_node(self):return self.properties['COMPOUND_NODE']
    def sort_port_list(self):
        if self.properties['PORT_CONSTRAINTS']in('FIXED_ORDER','FIXED_RATIO','FIXED_POS'):
            _source_sort(self.element.ports,_compare_ports)


class LGraphAdapter:
    def __init__(self,element,transparent_north_south_edges=False,transparent_comment_nodes=False,node_filter=None):
        self.element=element;self.properties=_PropertyView(element);self.options=None
        self.transparent_north_south_edges=transparent_north_south_edges
        self.transparent_comment_nodes=transparent_comment_nodes
        self.node_filter=(lambda node:True)if node_filter is None else node_filter
        self._nodes=None
    @property
    def nodes(self):
        if self._nodes is None:
            self._nodes=[]
            for layer in self.element.layers:
                for node in layer.nodes:
                    if self.node_filter(node):
                        self._nodes.append(LNodeAdapter(self,node,self.transparent_north_south_edges))
                        if self.transparent_comment_nodes:
                            for key in('TOP_COMMENTS','BOTTOM_COMMENTS'):
                                if _has_property(node,key):
                                    for comment in _read_property(node,key):self._nodes.append(LNodeAdapter(self,comment,False))
        return self._nodes
    @property
    def size(self):return self.element.size
    @size.setter
    def size(self,value):self.element.size.x=value.x;self.element.size.y=value.y
    @property
    def id(self):return self.element.id
    @id.setter
    def id(self,value):self.element.id=value
    def get_nodes(self):return self.nodes
    def get_size(self):return self.size
    def set_size(self,value):self.size=value
    def get_volatile_id(self):return self.id
    def set_volatile_id(self,value):self.id=value
    def get_property(self,name):return self.properties[name]
    def has_property(self,name):return name in self.properties
    def get_position(self):raise NotImplementedError('Not supported by LGraph')
    def set_position(self,value):raise NotImplementedError('Not supported by LGraph')


def _compare_ports(first,second):
    sides=('UNDEFINED','NORTH','EAST','SOUTH','WEST')
    difference=sides.index(first.side)-sides.index(second.side)
    if difference:return difference
    index1=_read_property(first,'PORT_INDEX');index2=_read_property(second,'PORT_INDEX')
    if index1 is not None and index2 is not None and index1!=index2:return index1-index2
    if first.side=='NORTH':return double_compare(first.pos.x,second.pos.x)
    if first.side=='EAST':return double_compare(first.pos.y,second.pos.y)
    if first.side=='SOUTH':return double_compare(second.pos.x,first.pos.x)
    if first.side=='WEST':return double_compare(second.pos.y,first.pos.y)
    raise ValueError('Port side is undefined')


class _LazyEdges:
    """Do not read outgoing adjacency before incoming is found empty."""
    def __init__(self,port,incoming):self.port=port;self.incoming=incoming
    def _get(self):return self.port.incoming_edges if self.incoming else self.port.outgoing_edges
    def __bool__(self):return bool(self._get())
    def __iter__(self):return iter(self._get())
    def __len__(self):return len(self._get())


class _AdaptedPortEdges:
    def __getitem__(self,port):return _LazyEdges(port,True),_LazyEdges(port,False)


def calculate_label_and_node_sizes(adapter):
    """Source common calculateLabelAndNodeSizes, over live native views."""
    from .node_size_process import process_node_size
    for node in adapter.nodes:
        process_node_size(adapter,node,True,False,adapted_port_edges=_AdaptedPortEdges(),
                          transparent_north_south_edges=adapter.transparent_north_south_edges)


def _compute_label_box(label,incoming,node,port,space,spacing):
    x,y=node.pos.x,node.pos.y
    if port is not None:x+=port.pos.x;y+=port.pos.y
    width,height=label.size.x,label.size.y
    if port is None:
        x=x-(spacing+width) if incoming else x+(node.size.x+spacing)
    elif port.side in('UNDEFINED','EAST'):
        x+=port.size.x+spacing+space.x+spacing
    elif port.side=='WEST':x-=spacing+space.x+spacing+width
    elif port.side=='NORTH':
        x+=port.size.x+spacing;y-=spacing+space.y+spacing+height
    elif port.side=='SOUTH':
        x+=port.size.x+spacing;y+=port.size.y+spacing+space.y+spacing
    return [x,y,width,height]


def _edge_label_bounds(box,outgoing,incoming,node,port,space,spacing):
    for edges,is_incoming in((outgoing,False),(incoming,True)):
        for edge in edges:
            for label in edge.labels:
                if label.get_property('EDGE_LABELS_PLACEMENT')==('HEAD'if is_incoming else'TAIL'):
                    _union(box,_compute_label_box(label,is_incoming,node,port,space,spacing))


class NodeMarginCalculator:
    def __init__(self,adapter):
        self.adapter=adapter;self.include_edge_head_tail_labels=True
        self.include_labels=True;self.include_port_labels=True;self.include_ports=True
    def exclude_edge_head_tail_labels(self):
        self.include_edge_head_tail_labels=False;return self
    def process(self):
        spacing=self.adapter.get_property('SPACING_LABEL_NODE')
        for node in self.adapter.nodes:self._process_node(node,spacing)
    def process_node(self,node):
        self._process_node(node,self.adapter.get_property('SPACING_LABEL_NODE'))
    def _process_node(self,node,spacing):
        box=[node.pos.x,node.pos.y,node.size.x,node.size.y]
        if self.include_labels:
            for label in node.labels:
                _union(box,[label.pos.x+node.pos.x,label.pos.y+node.pos.y,label.size.x,label.size.y])
        for port in node.ports:
            px=port.pos.x+node.pos.x;py=port.pos.y+node.pos.y
            if self.include_ports:_union(box,[px,py,port.size.x,port.size.y])
            if self.include_port_labels:
                for label in port.labels:
                    _union(box,[label.pos.x+px,label.pos.y+py,label.size.x,label.size.y])
            if self.include_edge_head_tail_labels:
                space=Vec2(-spacing,-spacing)
                if 'OUTSIDE'in node.get_property('PORT_LABELS_PLACEMENT'):
                    for label in port.labels:
                        space.x+=label.size.x+spacing;space.y+=label.size.y+spacing
                space.x=_maximum(space.x,0);space.y=_maximum(space.y,0)
                _edge_label_bounds(box,port.outgoing_edges,port.incoming_edges,node,port,space,spacing)
        if self.include_edge_head_tail_labels:
            _edge_label_bounds(box,node.outgoing_edges,node.incoming_edges,node,None,None,spacing)
        previous=node.margin
        margin=Insets(previous.top,previous.right,previous.bottom,previous.left)
        margin.top=_maximum(0,node.pos.y-box[1])
        margin.bottom=_maximum(0,box[1]+box[3]-(node.pos.y+node.size.y))
        margin.left=_maximum(0,node.pos.x-box[0])
        margin.right=_maximum(0,box[0]+box[2]-(node.pos.x+node.size.x))
        node.margin=margin


def _compute_port_label_box(port,spacing):
    if not port.labels:return None
    width=0.0;height=0.0
    for label in port.labels:
        width=_maximum(width,label.size.x);height+=label.size.y
    height+=(len(port.labels)-1)*spacing
    return [0.0,0.0,width,height]


def place_external_port_dummy_labels(dummy,placement,next_to_port,treat_as_group):
    horizontal=read_layered_scalar(dummy,'SPACING_LABEL_PORT_HORIZONTAL','SPACING_LABEL_PORT_HORIZONTAL')
    vertical=read_layered_scalar(dummy,'SPACING_LABEL_PORT_VERTICAL','SPACING_LABEL_PORT_VERTICAL')
    spacing=read_layered_scalar(dummy,'SPACING_LABEL_LABEL','SPACING_LABEL_LABEL')
    size=dummy.size;port=dummy.ports[0];position=port.pos
    box=_compute_port_label_box(port,spacing)
    if box is None:return
    if 'INSIDE'in placement:
        side=_read_property(dummy,'EXT_PORT_SIDE')
        if side=='NORTH':box[0]=(size.x-box[2])/2-position.x;box[1]=vertical
        elif side=='SOUTH':box[0]=(size.x-box[2])/2-position.x;box[1]=-vertical-box[3]
        elif side in('EAST','WEST'):
            if next_to_port and not port.incoming_edges and not port.outgoing_edges:
                height=box[3]if treat_as_group else port.labels[0].size.y
                box[1]=(size.y-height)/2-position.y
            else:box[1]=size.y+vertical-position.y
            box[0]=-horizontal-box[2]if side=='EAST'else horizontal
    elif 'OUTSIDE'in placement:
        side=_read_property(dummy,'EXT_PORT_SIDE')
        if side in('NORTH','SOUTH'):box[0]=position.x+horizontal
        elif side in('EAST','WEST'):
            # Source LPort prototype default true; explicit native field wins.
            if next_to_port and not getattr(port,'connected_to_external_nodes',True):
                height=box[3]if treat_as_group else port.labels[0].size.y
                box[1]=(size.y-height)/2-position.y
            else:box[1]=position.y+vertical
    current_y=box[1]
    for label in port.labels:
        label.pos.x=box[0];label.pos.y=current_y;current_y+=label.size.y+spacing


def label_and_node_size_processor(graph,*,monitor=None):
    monitor=BasicProgressMonitor(False,False)if monitor is None else monitor
    monitor.begin('Node and Port Label Placement and Node Sizing',1)
    calculate_label_and_node_sizes(LGraphAdapter(graph,True,True,lambda node:node.type=='NORMAL'))
    if 'EXTERNAL_PORTS'in _read_property(graph,'GRAPH_PROPERTIES'):
        placement=_read_property(graph,'PORT_LABELS_PLACEMENT')
        next_to_port='NEXT_TO_PORT_IF_POSSIBLE'in placement
        treat_as_group=read_layered_scalar(graph,'PORT_LABELS_TREAT_AS_GROUP','PORT_LABELS_TREAT_AS_GROUP')
        for layer in graph.layers:
            for node in layer.nodes:
                if node.type=='EXTERNAL_PORT':
                    place_external_port_dummy_labels(node,placement,next_to_port,treat_as_group)
    monitor.done()


def innermost_node_margin_processor(graph,*,monitor=None):
    monitor=BasicProgressMonitor(False,False)if monitor is None else monitor
    monitor.begin('Node margin calculation',1)
    NodeMarginCalculator(LGraphAdapter(graph,False,False)).exclude_edge_head_tail_labels().process()
    monitor.done()
