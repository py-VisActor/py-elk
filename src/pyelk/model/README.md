# Ordered host graph model

E03 implements the internal data boundary in [ADR-0002](../../../docs/decisions/0002-model-options-context.md).
It does not implement an ELK/layout API or compute coordinates. The fixed sources
and explicit host decisions are recorded in
[e03-model-sources.json](../../../references/e03-model-sources.json).

`Graph.from_json(mapping)` owns a deep JSON copy. `to_json()` on a graph, node,
port or edge returns another independent copy. Object key order, model array
order, missing fields, business null/false/0, `$H`, `error.stack` and existing
geometry survive without defaults or field removal. Mapping input is a host
convenience; non-JSON objects, tuples, cycles and nonfinite floats are rejected.

`graph.nodes` includes the root in preorder. `ports` and `edges` follow owner
node preorder and each original array. All are tuples; the corresponding
`node_index`, `port_index` and `edge_index` are read-only ordered mappings keyed
by `TypedId`. `node(id)`, `port(id)` and `edge(id)` retain the caller's ID type.
Strings, including an empty string, and Python integers are accepted. Bool and
float IDs are rejected; `1` and `'1'` remain different. This deliberately does
not simulate GWT's integral JSONNumber conversion, integer range or overflow.
Node/port/edge IDs are globally unique by typed identity. Optional label IDs
are validated but are not endpoint identities.

Nodes expose `id`, `typed_id`, `path`, `parent`, `children`, `ports`, `edges`.
Ports expose `owner`; edges expose `owner`, raw `sources`/`targets` tuples and
resolved `source_endpoints`/`target_endpoints` tuples containing nodes or ports.
Forward references are resolved after collecting all shapes. Invalid dimensions,
duplicates, containers and endpoints raise `ModelValidationError` with `code`
and an RFC 6901 `path`; valid missing lookups raise `KeyError`.

`set_property(key, value)` clones a nonstructural property before changing only
the owned graph. ID, relationship and section replacement is prohibited; an
invalid replacement leaves the graph unchanged. Explicit width/height must be
finite nonnegative numbers, excluding bool; absence remains absence.
Every recognized node, port, edge, label and section requires an explicit
`layoutOptions` value to be a mapping. This is a conservative host container
rule: keys/values are preserved without option parsing or priority selection.

Nested nodes, ports, labels and extended edges with multiple source/target IDs
are transported as data. Primitive edges are explicitly rejected in this slice.
Sections, point arrays, section references and existing point coordinates receive
basic container/ID/finite-number checks and retain their original order and
values. This does not validate section topology, section connectivity, coordinate
frames or orthogonal geometry. Known structural null containers are rejected;
business objects containing the same field names are only cloned.

`Anchor(x=..., y=...)` and keyword-only
`Margin(top=..., right=..., bottom=..., left=...)` are internal finite values;
margins must be nonnegative. They do not add fields to graph JSON. The model
contains no worker, renderer, Java dependency or random/layout state. Its ability
to carry advanced graph data does not expand the E02 layout comparison profile
or establish native algorithm support.
