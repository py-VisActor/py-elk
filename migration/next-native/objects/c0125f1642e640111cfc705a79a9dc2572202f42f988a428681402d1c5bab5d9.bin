"""Original native identity containers for mathematical strategy callers.

These retain the source's bucket and linked encounter protocols without
transplanting a Java collection runtime or allocating a second identity domain.
"""
from weakref import WeakKeyDictionary
from ...execution.identity import identity_hash as _host_identity_hash


class NodeIdentities:
    def __init__(self):
        self._node_identity_codes=WeakKeyDictionary();self._identity_graph=None

    def identity_hash(self,node):
        if node not in self._node_identity_codes:
            graph=getattr(node,'graph',None)
            layer=getattr(node,'layer',None)
            if graph is None and layer is not None:graph=layer.graph
            if graph is None:
                source=getattr(node,'source',None)
                if source is not None and source.owner is not None:
                    graph=source.owner.graph
                    if graph is None and source.owner.layer is not None:graph=source.owner.layer.graph
            if graph is None:graph=self._identity_graph
            if graph is None:raise TypeError('A native graph is required for a first node hash')
            getter=getattr(graph,'identity_hash',None)
            code=getter(node)if getter is not None else _host_identity_hash(graph,node)
            self._node_identity_codes[node]=code
        return self._node_identity_codes[node]


class NodeSet:
    def __init__(self,owner,values=()):
        self.owner=owner;self.buckets={};self.count=0
        for value in values:self.add(value)

    def _code(self,value):
        code=self.owner.identity_hash(value)
        return(code+2147483648)%4294967296-2147483648

    def add(self,value):
        bucket=self.buckets.setdefault(self._code(value),[])
        if not any(old is value for old in bucket):bucket.append(value);self.count+=1

    def contains(self,value):
        return any(old is value for old in self.buckets.get(self._code(value),()))

    def remove(self,value):
        code=self._code(value);bucket=self.buckets.get(code,[])
        for index,old in enumerate(bucket):
            if old is value:
                del bucket[index];self.count-=1
                if not bucket:del self.buckets[code]
                return True
        return False

    def clear(self):self.buckets.clear();self.count=0

    def values(self):return[value for bucket in self.buckets.values()for value in bucket]

    def update(self,other):
        for value in other.values():self.add(value)

    def __len__(self):return self.count


class LinkedNodes(NodeSet):
    def __init__(self,owner,values=()):
        self.order=[];super().__init__(owner,values)

    def add(self,value):
        if not any(old is value for old in self.order):self.order.append(value)
        super().add(value)

    def remove(self,value):
        changed=super().remove(value)
        if changed:
            for index,old in enumerate(self.order):
                if old is value:del self.order[index];break
        return changed

    def values(self):return list(self.order)

    def clear(self):super().clear();self.order.clear()


def outgoing(node):
    lists=[port.outgoing_edges for port in node.ports]
    return(edge for edges in lists for edge in edges)


def incoming(node):
    lists=[port.incoming_edges for port in node.ports]
    return(edge for edges in lists for edge in edges)


def baseline_configuration(first='EDGE_AND_LAYER_CONSTRAINT_EDGE_REVERSER'):
    from .layout_configuration import LayoutProcessorConfiguration,LayeredPhase
    from .phase_factories import IntermediateProcessorStrategy as Strategy
    p1,p2,p3,_,_=tuple(LayeredPhase);cfg=LayoutProcessorConfiguration()
    cfg.add_before(p1,Strategy[first]);cfg.add_before(p2,Strategy.LAYER_CONSTRAINT_PREPROCESSOR)
    cfg.add_before(p3,Strategy.LAYER_CONSTRAINT_POSTPROCESSOR)
    return cfg
