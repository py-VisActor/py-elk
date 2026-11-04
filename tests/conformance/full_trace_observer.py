"""Test-only selected-field snapshots of the actual general Layered objects.

No layout, defaults, cache materialization, allocator requests or RNG draws are
performed by this observer. IDs identify observed object identity, not origin
business identifiers. Public production trace remains the RGE job summary.
"""
import math
from collections.abc import Mapping


class Observer:
    def __init__(self):
        self.ids = {'node': {}, 'port': {}, 'edge': {}}
        self.trace = []
        self.progress = None

    def identity(self, obj):
        from pyelk.algorithms.layered.graph import LNode, LPort
        kind = 'node' if isinstance(obj, LNode) else 'port' if isinstance(obj, LPort) else 'edge'
        registry = self.ids[kind]
        if obj not in registry:
            registry[obj] = kind + ':' + str(len(registry))
        return registry[obj]

    def origin(self, obj):
        raw = obj.properties.get('ORIGIN')
        if isinstance(raw, dict):
            return raw.get('id')
        old = getattr(obj, 'origin', None)
        return getattr(old, 'id', None)

    def name(self, node):
        origin = self.origin(node)
        return origin if origin is not None else 'temporary:' + self.identity(node)

    def value(self, value):
        from pyelk.algorithms.layered.graph import LNode, LPort, LEdge, Layer, Vec2, Insets
        from pyelk.algorithms.layered.self_loops_general import SelfLoopHolder
        from pyelk.algorithms.layered.native_properties import _ALIAS_IDS
        if value is None or type(value) in (str, bool, int, float):
            if isinstance(value, float) and not math.isfinite(value):
                return {'internalNonfinite': 'NaN' if math.isnan(value) else 'Infinity' if value > 0 else '-Infinity'}
            return value
        if isinstance(value, Vec2):return {'x': value.x, 'y': value.y}
        if isinstance(value, Insets):return {key: getattr(value, key) for key in ('top','right','bottom','left')}
        if isinstance(value, LNode):return {'node': self.name(value), 'traceId': self.identity(value)}
        if isinstance(value, LPort):return {'port': value.id, 'node': self.name(value.owner) if value.owner else None, 'traceId': self.identity(value)}
        if isinstance(value, LEdge):return {'edge': self.origin(value) if self.origin(value) is not None else value.id, 'traceId': self.identity(value)}
        if isinstance(value, Layer):return {'layer': value.id}
        if isinstance(value, SelfLoopHolder):return self.holder(value)
        if isinstance(value, Mapping):
            aliases = {identifier: key for key, identifier in _ALIAS_IDS.items()}
            return {aliases.get(key,key): self.value(child) for key,child in value.items() if key != 'ORIGIN' and key != 'origin'}
        if isinstance(value, (list,tuple)):return [self.value(item) for item in value]
        if isinstance(value, (set,frozenset)):return {'setValues': sorted((self.value(item) for item in value),key=str)}
        return {'supportType': type(value).__name__}

    def edge(self, edge):
        return {'reference': self.value(edge), 'source': self.value(edge.source), 'target': self.value(edge.target),
                'bendPoints': self.value(edge.bend_points), 'properties': self.value(edge.properties)}

    def holder(self, holder):
        ports = []
        for _, wrapped in holder.sl_ports.items():
            port = wrapped.l_port
            ports.append({'reference': self.value(port), 'owner': self.value(port.owner),
                'id':port.id,'side':port.side,'pos':self.value(port.pos),'size':self.value(port.size),
                'anchor':self.value(port.anchor),'properties':self.value(port.properties),
                'incoming':[self.edge(e)for e in port.incoming_edges], 'outgoing':[self.edge(e)for e in port.outgoing_edges],
                'isHidden':wrapped.is_hidden,'hadOnlySelfLoops':wrapped.had_only_self_loops})
        return {'node':self.value(holder.l_node),'arePortsHidden':holder.are_ports_hidden,
            'routingSlotCount':list(holder.routing_slot_count),'ports':ports,
            'loops':[{'portOrder':[self.value(p.l_port)for p in loop.sl_ports],
                'selfLoopType':loop.self_loop_type,'occupiedSides':sorted(loop.occupied_port_sides),
                'routingSlot':list(loop.routing_slot),'labelsPresent':loop.sl_labels is not None,
                'edges':[{'sourcePort':self.value(e.sl_source.l_port),'targetPort':self.value(e.sl_target.l_port),
                          'edge':self.edge(e.l_edge)}for e in loop.sl_edges.values()]}
                     for loop in holder.sl_hyper_loops]}

    def snapshot(self, graph):
        nodes = []
        for node in [*graph.layerless_nodes,*(n for layer in graph.layers for n in layer.nodes)]:
            if node not in nodes:nodes.append(node)
        edges = []
        for node in nodes:
            self.identity(node)
            for port in node.ports:
                self.identity(port)
                for edge in [*port.incoming_edges,*port.outgoing_edges]:
                    if edge not in edges:edges.append(edge);self.identity(edge)
        value = self.value
        return {'layerless':[self.name(n)for n in graph.layerless_nodes],
            'layers':[{'id':layer.id,'nodes':[self.name(n)for n in layer.nodes],'size':value(layer.size)}for layer in graph.layers],
            'nodes':[{'originId':self.name(n),'traceId':self.identity(n),'id':n.id,'type':n.type,
                'pos':value(n.pos),'size':value(n.size),'margin':value(n.margin),'properties':value(n.properties),
                'portSidesCached':n.port_sides_cached,'portSideIndices':value(n.port_side_indices),
                'ports':[{'id':p.id,'side':p.side,'pos':value(p.pos),'size':value(p.size),'anchor':value(p.anchor),
                          'traceId':self.identity(p),'incoming':[self.origin(e) for e in p.incoming_edges],
                          'outgoing':[self.origin(e)for e in p.outgoing_edges],
                          'incomingTraceIds':[self.identity(e)for e in p.incoming_edges],
                          'outgoingTraceIds':[self.identity(e)for e in p.outgoing_edges]}for p in n.ports]}for n in nodes],
            'edges':[{'traceId':self.identity(e),'originId':self.origin(e),'id':e.id,
                      'source':value(e.source),'target':value(e.target),'bendPoints':value(e.bend_points),
                      'properties':value(e.properties)}for e in edges],
            'size':value(graph.size),'offset':value(graph.offset),'padding':value(graph.padding),
            'random':None if graph.random is None else {'state48':graph.random.state48,'primitiveDraws':graph.random.primitive_draws}}

    def wrap(self, processor, omitted=None):
        observer = self
        class ObservedProcessor:
            source_name = getattr(processor,'source_name',type(processor).__name__)
            def process(self, graph, monitor):
                row = {'index':len(observer.trace),'processor':self.source_name,'strategy':getattr(processor,'cross_min_type',None),
                       'before':observer.snapshot(graph),'outcome':'running'}
                observer.trace.append(row)
                if observer.progress is not None:observer.progress(row)
                if self.source_name != omitted:processor.process(graph,monitor)
                row.update(after=observer.snapshot(graph),outcome='returned')
        return ObservedProcessor()
