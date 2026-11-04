"""Ordered host graph data, independent of layout algorithms and resources.

The typed identity and validation boundary is ADR-0002.  This module does not
emulate GWT's numeric conversions or copy a Java importer implementation.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .._errors import ModelValidationError
from .._json import clone_json, finite_number, pointer


@dataclass(frozen=True, slots=True)
class TypedId:
    """A Python string or integer identity, without bool/number conflation."""

    kind: str
    value: str | int

    def __post_init__(self):
        if not ((self.kind == "string" and type(self.value) is str)
                or (self.kind == "integer" and type(self.value) is int)):
            raise ModelValidationError("INVALID_ID", "", "Expected a string or integer typed ID")

    @classmethod
    def from_value(cls, value, *, path=""):
        if type(value) is str:
            return cls("string", value)
        if type(value) is int:
            return cls("integer", value)
        raise ModelValidationError("INVALID_ID", path, "ID must be a string or Python integer")


@dataclass(frozen=True, slots=True, kw_only=True)
class Anchor:
    """An internal finite anchor value; never added to exported graph JSON."""

    x: int | float
    y: int | float

    def __post_init__(self):
        for key in ("x", "y"):
            finite_number(getattr(self, key), path=pointer("", key), error_type=ModelValidationError)


@dataclass(frozen=True, slots=True, kw_only=True)
class Margin:
    """Internal nonnegative margins; explicit keywords prevent side ambiguity."""

    top: int | float = 0
    right: int | float = 0
    bottom: int | float = 0
    left: int | float = 0

    def __post_init__(self):
        for key in ("top", "right", "bottom", "left"):
            finite_number(getattr(self, key), path=pointer("", key), nonnegative=True,
                          error_type=ModelValidationError)


# Changing these fields would invalidate a relationship or an identity index.
_STRUCTURAL_FIELDS = frozenset({
    "id", "children", "ports", "edges", "labels", "sources", "targets",
    "source", "target", "sourcePort", "targetPort", "sections",
    "incomingSections", "outgoingSections", "container",
})


def _dimensions(data, path):
    for key in ("width", "height"):
        if key in data:
            finite_number(data[key], path=pointer(path, key), nonnegative=True,
                          error_type=ModelValidationError)


def _option_container(data, path):
    # Container ownership is a host model rule. Option keys, values and selected
    # scopes belong exclusively to the option resolver.
    if "layoutOptions" in data and not isinstance(data["layoutOptions"], Mapping):
        raise ModelValidationError("INVALID_CONTAINER", pointer(path, "layoutOptions"),
                                   "Expected a layout option mapping")


def _array(data, key, path):
    if key not in data:
        return []
    value = data[key]
    if type(value) is not list:
        raise ModelValidationError("INVALID_CONTAINER", pointer(path, key), "Expected a JSON array")
    return value


def _object(value, path):
    if type(value) is not dict:
        raise ModelValidationError("INVALID_ELEMENT", path, "Expected a JSON object")
    return value


def _identity(data, path):
    if "id" not in data:
        raise ModelValidationError("MISSING_ID", pointer(path, "id"), "Element must have an ID")
    return TypedId.from_value(data["id"], path=pointer(path, "id"))


def _labels(data, path):
    for index, raw in enumerate(_array(data, "labels", path)):
        where = pointer(pointer(path, "labels"), index)
        label = _object(raw, where)
        if "id" in label:
            TypedId.from_value(label["id"], path=pointer(where, "id"))
        _dimensions(label, where)
        _option_container(label, where)
        _labels(label, where)


def _point(value, path):
    point = _object(value, path)
    for key in ("x", "y"):
        if key in point:
            finite_number(point[key], path=pointer(path, key), error_type=ModelValidationError)


def _edge_geometry(data, path):
    """Validate declared geometry values without resolving section topology."""
    for key in ("startPoint", "endPoint"):
        if key in data:
            _point(data[key], pointer(path, key))
    for key in ("bendPoints", "junctionPoints"):
        for index, value in enumerate(_array(data, key, path)):
            _point(value, pointer(pointer(path, key), index))
    for index, raw in enumerate(_array(data, "sections", path)):
        where = pointer(pointer(path, "sections"), index)
        section = _object(raw, where)
        if "id" in section:
            TypedId.from_value(section["id"], path=pointer(where, "id"))
        _option_container(section, where)
        for key in ("incomingShape", "outgoingShape"):
            if key in section:
                TypedId.from_value(section[key], path=pointer(where, key))
        for key in ("incomingSections", "outgoingSections"):
            for ref_index, value in enumerate(_array(section, key, where)):
                TypedId.from_value(value, path=pointer(pointer(where, key), ref_index))
        for key in ("startPoint", "endPoint"):
            if key in section:
                _point(section[key], pointer(where, key))
        for point_index, value in enumerate(_array(section, "bendPoints", where)):
            _point(value, pointer(pointer(where, "bendPoints"), point_index))


class _Element:
    __slots__ = ("_data", "_path", "_typed_id")

    def __init__(self, data, path, identity):
        self._data = data
        self._path = path
        self._typed_id = identity

    @property
    def id(self):
        return self._typed_id.value

    @property
    def typed_id(self):
        return self._typed_id

    @property
    def path(self):
        return self._path

    def to_json(self):
        return clone_json(self._data, path=self.path, error_type=ModelValidationError)

    def set_property(self, key, value):
        """Set one nonstructural property on this graph's owned working copy.

        Validation and cloning finish before assignment, so failure leaves the
        graph unchanged.  The caller and subsequent exports never share values.
        """
        if type(key) is not str:
            raise ModelValidationError("INVALID_PROPERTY", self.path, "Property key must be a string")
        where = pointer(self.path, key)
        if key in _STRUCTURAL_FIELDS:
            raise ModelValidationError("STRUCTURAL_MUTATION", where, "Structural properties cannot be replaced")
        cloned = clone_json(value, path=where, error_type=ModelValidationError)
        if key in ("width", "height"):
            finite_number(cloned, path=where, nonnegative=True, error_type=ModelValidationError)
        if key == "layoutOptions":
            _option_container({key: cloned}, self.path)
        if isinstance(self, Edge):
            candidate = dict(self._data)
            candidate[key] = cloned
            _edge_geometry(candidate, self.path)
        self._data[key] = cloned


class Node(_Element):
    __slots__ = ("_parent", "_children", "_ports", "_edges")

    def __init__(self, data, path, identity, parent):
        super().__init__(data, path, identity)
        self._parent = parent
        self._children = ()
        self._ports = ()
        self._edges = ()

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

    @property
    def ports(self):
        return self._ports

    @property
    def edges(self):
        return self._edges


class Port(_Element):
    __slots__ = ("_owner",)

    def __init__(self, data, path, identity, owner):
        super().__init__(data, path, identity)
        self._owner = owner

    @property
    def owner(self):
        return self._owner


class Edge(_Element):
    __slots__ = ("_owner", "_sources", "_targets", "_source_endpoints", "_target_endpoints")

    def __init__(self, data, path, identity, owner, sources, targets,
                 source_endpoints, target_endpoints):
        super().__init__(data, path, identity)
        self._owner = owner
        self._sources = sources
        self._targets = targets
        self._source_endpoints = source_endpoints
        self._target_endpoints = target_endpoints

    @property
    def owner(self):
        return self._owner

    @property
    def sources(self):
        return self._sources

    @property
    def targets(self):
        return self._targets

    @property
    def source_endpoints(self):
        return self._source_endpoints

    @property
    def target_endpoints(self):
        return self._target_endpoints


class Graph:
    """Independent JSON ownership plus stable node/port/edge identity lookup."""

    __slots__ = ("_data", "_root", "_nodes", "_ports", "_edges",
                 "_node_index", "_port_index", "_edge_index")

    @classmethod
    def from_json(cls, mapping):
        if not isinstance(mapping, Mapping):
            raise ModelValidationError("INVALID_GRAPH", "", "Graph root must be a mapping")
        data = clone_json(mapping, error_type=ModelValidationError)
        nodes, ports, edges = [], [], []
        node_index, port_index, edge_index, identities = {}, {}, {}, {}

        def register(element, index):
            previous = identities.get(element.typed_id)
            if previous is not None:
                raise ModelValidationError("DUPLICATE_ID", pointer(element.path, "id"),
                                           "ID duplicates element at " + (previous or "/"))
            identities[element.typed_id] = element.path
            index[element.typed_id] = element

        def parse_node(raw, path, parent):
            item = _object(raw, path)
            identity = _identity(item, path)
            _dimensions(item, path)
            _option_container(item, path)
            _labels(item, path)
            node = Node(item, path, identity, parent)
            register(node, node_index)
            nodes.append(node)
            owned_ports = []
            for i, raw_port in enumerate(_array(item, "ports", path)):
                where = pointer(pointer(path, "ports"), i)
                port_data = _object(raw_port, where)
                port_id = _identity(port_data, where)
                _dimensions(port_data, where)
                _option_container(port_data, where)
                _labels(port_data, where)
                port = Port(port_data, where, port_id, node)
                register(port, port_index)
                ports.append(port)
                owned_ports.append(port)
            node._ports = tuple(owned_ports)
            node._children = tuple(parse_node(child, pointer(pointer(path, "children"), i), node)
                                   for i, child in enumerate(_array(item, "children", path)))
            return node

        root = parse_node(data, "", None)

        def endpoints(item, key, path):
            values = _array(item, key, path)
            if not values:
                raise ModelValidationError("MISSING_ENDPOINT", pointer(path, key),
                                           "Edge requires at least one " + key)
            resolved = []
            for i, value in enumerate(values):
                where = pointer(pointer(path, key), i)
                identity = TypedId.from_value(value, path=where)
                endpoint = node_index.get(identity)
                if endpoint is None:
                    endpoint = port_index.get(identity)
                if endpoint is None:
                    raise ModelValidationError("UNKNOWN_ENDPOINT", where, "Referenced node or port does not exist")
                resolved.append(endpoint)
            return tuple(values), tuple(resolved)

        for owner in nodes:
            owned_edges = []
            for i, raw_edge in enumerate(_array(owner._data, "edges", owner.path)):
                where = pointer(pointer(owner.path, "edges"), i)
                edge_data = _object(raw_edge, where)
                identity = _identity(edge_data, where)
                if any(key in edge_data for key in ("source", "target", "sourcePort", "targetPort")):
                    raise ModelValidationError("UNSUPPORTED_EDGE", where,
                                               "Primitive edges are outside this host model slice")
                _dimensions(edge_data, where)
                _option_container(edge_data, where)
                _labels(edge_data, where)
                _edge_geometry(edge_data, where)
                sources, source_endpoints = endpoints(edge_data, "sources", where)
                targets, target_endpoints = endpoints(edge_data, "targets", where)
                edge = Edge(edge_data, where, identity, owner, sources, targets,
                            source_endpoints, target_endpoints)
                register(edge, edge_index)
                edges.append(edge)
                owned_edges.append(edge)
            owner._edges = tuple(owned_edges)

        graph = cls()
        graph._data, graph._root = data, root
        graph._nodes, graph._ports, graph._edges = tuple(nodes), tuple(ports), tuple(edges)
        graph._node_index = MappingProxyType(node_index)
        graph._port_index = MappingProxyType(port_index)
        graph._edge_index = MappingProxyType(edge_index)
        return graph

    @property
    def root(self):
        return self._root

    @property
    def nodes(self):
        return self._nodes

    @property
    def ports(self):
        return self._ports

    @property
    def edges(self):
        return self._edges

    @property
    def node_index(self):
        return self._node_index

    @property
    def port_index(self):
        return self._port_index

    @property
    def edge_index(self):
        return self._edge_index

    def node(self, identity):
        return self._node_index[TypedId.from_value(identity)]

    def port(self, identity):
        return self._port_index[TypedId.from_value(identity)]

    def edge(self, identity):
        return self._edge_index[TypedId.from_value(identity)]

    def to_json(self):
        return clone_json(self._data, error_type=ModelValidationError)
