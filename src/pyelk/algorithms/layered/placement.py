# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Mechanical port from elkjs 0.12.1 generated lib/elk-worker.js.
# Upstream commit: 624ae90aa37110033a8af59c5ccbb292708b4317
# Worker SHA256: 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86
# Source/guard map: references/e05-source-components-B.json, phase:BRANDES_KOEPF.
# E06 loop margins/NORTH guard: references/e06-source-components-R.json; NOTICE-E06.md.
# Exact external Java build unresolved. See pyelk/_licenses/NOTICE.md.
"""Default proper-DAG Brandes/Koepf blocks, compaction and straightening.

The four actual candidates retain their own state, including recursive block
placement, class dependencies and the source threshold queue/stack. There is
no oracle/reference dependency or coordinate normalization at runtime.
"""
from collections import deque
import math

from ..._errors import UnsupportedFeatureError
from .crossing import _guard as _proper_guard

_P='org.eclipse.elk.'
_MAX=1.7976931348623157e308


def _outside(message):
    raise UnsupportedFeatureError('UNSUPPORTED_PHASE_INPUT','',message)


def _min(a,b):
    if math.isnan(a) or math.isnan(b):
        return math.nan
    if a==0 and b==0:
        return -0.0 if math.copysign(1,a)<0 or math.copysign(1,b)<0 else 0.0
    return a if a<=b else b


def _max(a,b):
    if math.isnan(a) or math.isnan(b):
        return math.nan
    if a==0 and b==0:
        return 0.0 if math.copysign(1,a)>0 or math.copysign(1,b)>0 else -0.0
    return a if a>=b else b


def _incoming(node):
    return [edge for port in node.ports for edge in port.incoming_edges]


def _outgoing(node):
    return [edge for port in node.ports for edge in port.outgoing_edges]


def _connected(node):
    return [edge for port in node.ports for edge in [*port.incoming_edges,*port.outgoing_edges]]


class _Neighborhood:
    def __init__(self,graph):
        self.graph=graph
        self.nodes=[node for layer in graph.layers for node in layer.nodes]
        self.node_index={}
        self.layer_index={}
        for index,layer in enumerate(graph.layers):
            layer.id=index
            self.layer_index[layer]=index
            for position,node in enumerate(layer.nodes):
                node.id=len(self.node_index)
                self.node_index[node]=position
        self.left,self.right={},{}
        for node in self.nodes:
            self.left[node]=self._neighbors(node,True)
        for node in self.nodes:
            self.right[node]=self._neighbors(node,False)

    def _neighbors(self,node,left):
        result=[]
        maximum=0
        for edge in _incoming(node) if left else _outgoing(node):
            if edge.source.owner is edge.target.owner or edge.source.owner.layer is edge.target.owner.layer:
                continue
            priority=edge.properties.get('PRIORITY_STRAIGHTNESS',0)
            if priority>maximum:
                maximum=priority
                result.clear()
            if priority==maximum:
                result.append((edge.source.owner if left else edge.target.owner,edge))
        result.sort(key=lambda item:self.node_index[item[0]])
        return result


class _Layout:
    def __init__(self,graph,nodes,vertical,horizontal):
        self.graph,self.nodes=graph,nodes
        self.vertical,self.horizontal=vertical,horizontal
        self.root={node:None for node in nodes}
        self.align={node:None for node in nodes}
        self.block_size={node:None for node in nodes}
        self.inner={node:None for node in nodes}
        self.sink={node:None for node in nodes}
        self.shift={node:None for node in nodes}
        self.y={node:None for node in nodes}
        self.su={node:False for node in nodes}
        self.od={node:True for node in nodes}

    def layers(self):
        return self.graph.layers if self.horizontal=='RIGHT' else list(reversed(self.graph.layers))

    def ordered_nodes(self,layer):
        return layer.nodes if self.vertical=='DOWN' else list(reversed(layer.nodes))

    def spacing(self,first,second):
        if first.type=='NORMAL' and second.type=='NORMAL':
            return self.graph.options.values[_P+'spacing.nodeNode']
        return 10.0  # reviewed default edgeNode and edgeEdge type-pair mappings

    def size(self):
        low,high=math.inf,-math.inf
        for node in self.nodes:
            low=_min(low,self.y[node])
            high=_max(high,self.y[node]+self.block_size[self.root[node]])
        return high-low

    def shift_block(self,start,delta):
        node=start
        while True:
            self.y[node]=self.y[node]+delta
            node=self.align[node]
            if node is start:
                break

    def delta(self,fixed,block):
        source=self.y[fixed.owner]+self.inner[fixed.owner]+fixed.pos.y+fixed.anchor.y
        target=self.y[block.owner]+self.inner[block.owner]+block.pos.y+block.anchor.y
        return target-source

    def available_space(self,start,delta,neighborhood,above):
        available,current=delta,start
        while True:
            current=self.align[current]
            position=neighborhood.node_index[current]
            offset=-1 if above else 1
            neighbor_index=position+offset
            if 0<=neighbor_index<len(current.layer.nodes):
                neighbor=current.layer.nodes[neighbor_index]
                current_y=self.y[self.root[current]]+self.inner[current]
                neighbor_y=self.y[self.root[neighbor]]+self.inner[neighbor]
                spacing=self.spacing(current,neighbor)
                if above:
                    minimum=current_y-current.margin.top
                    maximum=neighbor_y+neighbor.size.y+neighbor.margin.bottom
                    available=_min(available,minimum-(maximum+spacing))
                else:
                    maximum=current_y+current.size.y+current.margin.bottom
                    minimum=neighbor_y-neighbor.margin.top
                    available=_min(available,minimum-(maximum+spacing))
            if current is start:
                break
        return available


def _marked_edges(graph,neighborhood,*,observed_order=None):
    marked=set()
    if len(graph.layers)<3:
        return marked
    sizes=[len(layer.nodes) for layer in graph.layers]
    def inner(node,layer1,layer2):
        return node.type=='LONG_EDGE' and any(edge.source.owner.type=='LONG_EDGE'
            and neighborhood.layer_index[edge.source.owner.layer]==layer2
            and neighborhood.layer_index[node.layer]==layer1 for edge in _incoming(node))
    for index in range(1,len(graph.layers)-1):
        current=graph.layers[index+1]
        low=0
        scan=0
        for position,node in enumerate(current.nodes):
            if position==sizes[index+1]-1 or inner(node,index+1,index):
                high=sizes[index]-1
                if inner(node,index+1,index):
                    high=neighborhood.node_index[neighborhood.left[node][0][0]]
                while scan<=position:
                    item=current.nodes[scan]
                    if not inner(item,index+1,index):
                        for neighbor,edge in neighborhood.left[item]:
                            other=neighborhood.node_index[neighbor]
                            if other<low or other>high:
                                # Only this fresh private identity set's successful
                                # additions are observed; membership remains a set.
                                first_add = observed_order is not None and edge not in marked
                                marked.add(edge)
                                if first_add:
                                    observed_order.append(edge)
                    scan+=1
                low=high
    return marked


def _vertical_alignment(layout,neighborhood,marked):
    for node in layout.nodes:
        layout.root[node]=node
        layout.align[node]=node
        layout.inner[node]=0.0
    for layer in layout.layers():
        boundary=(1<<31)-1 if layout.vertical=='UP' else -1
        for node in layout.ordered_nodes(layer):
            neighbors=neighborhood.right[node] if layout.horizontal=='LEFT' else neighborhood.left[node]
            count=len(neighbors)
            if count:
                low=math.floor((count+1)/2)-1
                high=math.ceil((count+1)/2)-1
                medians=range(high,low-1,-1) if layout.vertical=='UP' else range(low,high+1)
                for median in medians:
                    if layout.align[node] is node:
                        neighbor,edge=neighbors[median]
                        position=neighborhood.node_index[neighbor]
                        allowed=boundary>position if layout.vertical=='UP' else boundary<position
                        if edge not in marked and allowed:
                            layout.align[neighbor]=node
                            layout.root[node]=layout.root[neighbor]
                            layout.align[node]=layout.root[node]
                            root=layout.root[node]
                            layout.od[root]=bool(layout.od[root] and node.type=='LONG_EDGE')
                            boundary=position


def _inside_block_shift(layout):
    blocks={}
    for node in layout.nodes:
        blocks.setdefault(layout.root[node],[]).append(node)
    for root in blocks:
        above=root.margin.top
        below=root.size.y+root.margin.bottom
        layout.inner[root]=0.0
        current=root
        while layout.align[current] is not root:
            following=layout.align[current]
            edge=next(edge for edge in _connected(current) if edge.source.owner is following or edge.target.owner is following)
            if layout.horizontal=='LEFT':
                difference=edge.target.pos.y+edge.target.anchor.y-edge.source.pos.y-edge.source.anchor.y
            else:
                difference=edge.source.pos.y+edge.source.anchor.y-edge.target.pos.y-edge.target.anchor.y
            value=layout.inner[current]+difference
            layout.inner[following]=value
            above=_max(above,following.margin.top-value)
            below=_max(below,value+following.size.y+following.margin.bottom)
            current=following
        current=root
        while True:
            layout.inner[current]=layout.inner[current]+above
            current=layout.align[current]
            if current is root:
                break
        layout.block_size[root]=above+below


class _Pending:
    def __init__(self,node,is_root):
        self.node,self.is_root=node,is_root
        self.has_edges=False
        self.edge=None


class _Threshold:
    def __init__(self,layout,neighborhood):
        self.layout,self.neighborhood=layout,neighborhood
        self.finished=set()
        self.queue=deque()
        self.stack=[]

    def _pick(self,pending):
        layout=self.layout
        incoming=(layout.horizontal=='RIGHT') if pending.is_root else (layout.horizontal=='LEFT')
        edges=_incoming(pending.node) if incoming else _outgoing(pending.node)
        has_edges=False
        for edge in edges:
            root=layout.root[pending.node]
            only_dummies=layout.od[root]
            if not only_dummies and edge.source.owner is not edge.target.owner and edge.source.owner.layer is edge.target.owner.layer:
                continue
            # The generated predicate checks this identical su entry twice.
            if layout.su[root]:
                continue
            has_edges=True
            other=edge.target.owner if edge.source.owner is pending.node else edge.source.owner
            if layout.root[other] in self.finished:
                pending.has_edges,pending.edge=True,edge
                return pending
        pending.has_edges,pending.edge=has_edges,None
        return pending

    def _bound(self,node,is_root):
        layout=self.layout
        invalid=math.inf if layout.vertical=='UP' else -math.inf
        pending=self._pick(_Pending(node,is_root))
        if pending.edge is None and pending.has_edges:
            self.queue.append(pending)
            return invalid
        if pending.edge is not None:
            left,right=pending.edge.source,pending.edge.target
            root_on_right=layout.horizontal=='RIGHT' if is_root else layout.horizontal=='LEFT'
            root_port,other_port=(right,left) if root_on_right else (left,right)
            other_root=layout.root[other_port.owner]
            threshold=layout.y[other_root]+layout.inner[other_port.owner]+other_port.pos.y+other_port.anchor.y-layout.inner[root_port.owner]-root_port.pos.y-root_port.anchor.y
            layout.su[layout.root[left.owner]]=True
            layout.su[layout.root[right.owner]]=True
            return threshold
        return invalid

    def calculate(self,old,root,current):
        is_root=root is current
        is_last=self.layout.align[current] is root
        if not (is_root or is_last):
            return old
        value=self._bound(root,True) if is_root else old
        if math.isinf(value) and is_last:
            value=self._bound(current,False)
        return value

    def _process(self,pending):
        edge=pending.edge
        fixed,block=(edge.target,edge.source) if edge.source.owner is pending.node else (edge.source,edge.target)
        delta=self.layout.delta(fixed,block)
        if 0<delta<_MAX:
            available=self.layout.available_space(block.owner,delta,self.neighborhood,True)
            self.layout.shift_block(block.owner,-available)
            return available>0
        if delta<0 and -delta<_MAX:
            available=self.layout.available_space(block.owner,-delta,self.neighborhood,False)
            self.layout.shift_block(block.owner,available)
            return available>0
        return False

    def post_process(self):
        while self.queue:
            pending=self.queue.popleft()
            pick=self._pick(pending)
            if pick.edge is None:
                continue
            edge=pick.edge
            only_dummies=self.layout.od[self.layout.root[pending.node]]
            if not only_dummies and edge.source.owner is not edge.target.owner and edge.source.owner.layer is edge.target.owner.layer:
                continue
            if not self._process(pending):
                self.stack.append(pending)
        while self.stack:
            self._process(self.stack.pop())


class _ClassNode:
    def __init__(self,node):
        self.node=node
        self.outgoing=[]
        self.indegree=0
        self.shift=None


class _Compactor:
    def __init__(self,graph,neighborhood):
        self.graph,self.neighborhood=graph,neighborhood

    def compact(self,layout):
        self.layout=layout
        self.classes={}
        self.threshold=_Threshold(layout,self.neighborhood)
        for node in layout.nodes:
            layout.sink[node]=node
            layout.shift[node]=-math.inf if layout.vertical=='UP' else math.inf
            layout.y[node]=None
        for layer in layout.layers():
            for node in layout.ordered_nodes(layer):
                if layout.root[node] is node:
                    self._place_block(node)
        self._place_classes()
        for layer in layout.layers():
            for node in layer.nodes:
                layout.y[node]=layout.y[layout.root[node]]
                if node is layout.root[node]:
                    shift=layout.shift[layout.sink[node]]
                    if (layout.vertical=='UP' and shift>-math.inf) or (layout.vertical=='DOWN' and shift<math.inf):
                        layout.y[node]=layout.y[node]+shift
        self.threshold.post_process()

    def _class(self,sink):
        if sink not in self.classes:
            self.classes[sink]=_ClassNode(sink)
        return self.classes[sink]

    def _add_class_edge(self,source,target,separation):
        source.outgoing.append((target,separation))
        target.indegree+=1

    def _place_block(self,root):
        layout=self.layout
        if layout.y[root] is not None:
            return
        initial=True
        layout.y[root]=0.0
        current=root
        threshold=-math.inf if layout.vertical=='DOWN' else math.inf
        while True:
            index=self.neighborhood.node_index[current]
            count=len(current.layer.nodes)
            if (layout.vertical=='DOWN' and index>0) or (layout.vertical=='UP' and index<count-1):
                neighbor=current.layer.nodes[index+1 if layout.vertical=='UP' else index-1]
                neighbor_root=layout.root[neighbor]
                self._place_block(neighbor_root)
                threshold=self.threshold.calculate(threshold,root,current)
                if layout.sink[root] is root:
                    layout.sink[root]=layout.sink[neighbor_root]
                if layout.sink[root] is layout.sink[neighbor_root]:
                    spacing=layout.spacing(current,neighbor)
                    current_position=layout.y[root]
                    if layout.vertical=='UP':
                        position=layout.y[neighbor_root]+layout.inner[neighbor]-neighbor.margin.top-spacing-current.margin.bottom-current.size.y-layout.inner[current]
                        layout.y[root]=_min(position,threshold) if initial else _min(current_position,_min(position,threshold))
                    else:
                        position=layout.y[neighbor_root]+layout.inner[neighbor]+neighbor.size.y+neighbor.margin.bottom+spacing+current.margin.top-layout.inner[current]
                        layout.y[root]=_max(position,threshold) if initial else _max(current_position,_max(position,threshold))
                    if initial:
                        initial=False
                else:
                    # This class separation intentionally uses graph nodeNode,
                    # not the source type-pair spacing mapping used above.
                    spacing=self.graph.options.values[_P+'spacing.nodeNode']
                    sink=self._class(layout.sink[root])
                    neighbor_sink=self._class(layout.sink[neighbor_root])
                    if layout.vertical=='UP':
                        separation=layout.y[root]+layout.inner[current]+current.size.y+current.margin.bottom+spacing-(layout.y[neighbor_root]+layout.inner[neighbor]-neighbor.margin.top)
                    else:
                        separation=layout.y[root]+layout.inner[current]-current.margin.top-layout.y[neighbor_root]-layout.inner[neighbor]-neighbor.size.y-neighbor.margin.bottom-spacing
                    self._add_class_edge(sink,neighbor_sink,separation)
            else:
                threshold=self.threshold.calculate(threshold,root,current)
            current=layout.align[current]
            if current is root:
                break
        self.threshold.finished.add(root)

    def _place_classes(self):
        # The fixed GWT identity-key HashMap is backed by insertion-ordered
        # ES Map hash chains; these private node hashes are unique.
        sources=deque(node for node in self.classes.values() if node.indegree==0)
        while sources:
            node=sources.popleft()
            if node.shift is None:
                node.shift=0.0
            for target,separation in node.outgoing:
                value=node.shift+separation
                if target.shift is None:
                    target.shift=value
                elif self.layout.vertical=='DOWN':
                    target.shift=_min(target.shift,value)
                else:
                    target.shift=_max(target.shift,value)
                target.indegree-=1
                if target.indegree==0:
                    sources.append(target)
        for node in self.classes.values():
            self.layout.shift[node.node]=node.shift


def _feasible(layout,*,monitor=None):
    if monitor is not None:
        from ...execution.diagnostics import layout_name, node_text
    for layer in layout.graph.layers:
        previous=-math.inf
        previous_node=None
        for node in layer.nodes:
            top=layout.y[node]+layout.inner[node]-node.margin.top
            bottom=layout.y[node]+layout.inner[node]+node.size.y+node.margin.bottom
            if top>previous and bottom>previous:
                previous=layout.y[node]+layout.inner[node]+node.size.y+node.margin.bottom
                previous_node=node
            else:
                if monitor is not None and monitor.record_logs:
                    monitor.log('bk node placement breaks on '+node_text(node)+' which should have been after '+node_text(previous_node))
                    monitor.log(layout_name(layout)+' is feasible: false')
                return False
    if monitor is not None and monitor.record_logs:
        monitor.log(layout_name(layout)+' is feasible: true')
    return True


def _admit(graph):
    # Late loop restoration adds empty NORTH ports and leaves old side caches.
    # The actual BK neighborhood walks current edge lists, never those caches.
    nodes=_proper_guard(graph,'BARYCENTER',allow_detached_north=True)
    if not nodes:
        _outside('Empty graphs use the outer layout early return')
    if graph.properties.get('NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES') is not True or graph.properties.get('NODE_PLACEMENT_BK_FIXED_ALIGNMENT','NONE')!='NONE' or graph.properties.get('NODE_PLACEMENT_BK_EDGE_STRAIGHTENING','IMPROVE_STRAIGHTNESS')!='IMPROVE_STRAIGHTNESS':
        _outside('Only default ORTHOGONAL BK/straightening is source-approved')
    spacing=graph.options.values[_P+'spacing.nodeNode']
    if type(spacing) not in (int,float) or not math.isfinite(spacing) or not 0<=spacing<=1_000_000:
        _outside('Node spacing exceeds the approved finite domain')
    for node in nodes:
        if 'SPACING_INDIVIDUAL' in node.properties:
            _outside('Individual spacing is outside the approved default type mapping')
        if any(type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1_000_000
               for value in (node.size.x,node.size.y,node.margin.top,node.margin.right,node.margin.bottom,node.margin.left)):
            _outside('BK requires bounded finite actual dimensions and margins')
        if node.type=='LONG_EDGE' and (node.size.x!=0 or node.size.y!=1):
            _outside('The approved long-edge splitter uses thickness1 dummies')
        for port in node.ports:
            if any(type(value) not in (int,float) or value!=0 for value in (port.size.x,port.size.y,port.anchor.x,port.anchor.y)):
                _outside('Only zero-size zero-anchor implicit ports are approved')
            if any(type(value) not in (int,float) or not math.isfinite(value) or abs(value)>1_000_000_000 for value in (port.pos.x,port.pos.y)):
                _outside('The real node-size processor must prepare finite port positions')
            if node.type=='LONG_EDGE' and (port.pos.x!=0 or port.pos.y!=0):
                _outside('Dummy port position must retain floor(thickness/2)=0')
            for edge in [*port.incoming_edges,*port.outgoing_edges]:
                priority=edge.properties.get('PRIORITY_STRAIGHTNESS',0)
                if type(priority) is not int or priority!=0:
                    _outside('Custom straightness priorities need their own source branch')
    return nodes


def bk_node_placer(graph,*,monitor=None):
    """Source four alignments, actual compaction and stable candidate choice."""
    _admit(graph)
    neighborhood=_Neighborhood(graph)
    marked_order=[] if monitor is not None and monitor.record_logs else None
    marked=_marked_edges(graph,neighborhood,observed_order=marked_order)
    # Match source object allocation order separately from evaluation order.
    left_down=_Layout(graph,neighborhood.nodes,'DOWN','LEFT')
    left_up=_Layout(graph,neighborhood.nodes,'UP','LEFT')
    right_down=_Layout(graph,neighborhood.nodes,'DOWN','RIGHT')
    right_up=_Layout(graph,neighborhood.nodes,'UP','RIGHT')
    layouts=[right_down,right_up,left_down,left_up]
    for layout in layouts:
        _vertical_alignment(layout,neighborhood,marked)
        _inside_block_shift(layout)
    compactor=_Compactor(graph,neighborhood)
    for layout in layouts:
        compactor.compact(layout)
    if monitor is not None and monitor.record_logs:
        from ...execution.diagnostics import layout_name, number_text
        for layout in layouts:
            monitor.log(layout_name(layout)+' size is '+number_text(layout.size()))
    chosen=None
    for layout in layouts:
        feasible = _feasible(layout) if monitor is None else _feasible(layout,monitor=monitor)
        if feasible and (chosen is None or chosen.size()>layout.size()):
            chosen=layout
    if chosen is None:
        chosen=layouts[0]
    for node in neighborhood.nodes:
        node.pos.y=chosen.y[node]+chosen.inner[node]
    if monitor is not None:
        from ...execution.diagnostics import log_bk_choice
        log_bk_choice(monitor,chosen,marked_order)
    # Every temporary array/set/queue belongs to this call. No scratch escapes
    # through the work graph; source cleanup cannot affect origin/model data.
