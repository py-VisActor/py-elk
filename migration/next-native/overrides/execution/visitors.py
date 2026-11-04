# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Actual owned-element/properties-skipping traversal source protocol:
# HOST11/B/traversal-source-review-01/review.json. Worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Owned graph-element visits for the engine's property-only visitors.

This is an original Python containment walk, not an EMF tree-runtime facade.
Arbitrary containment-mutating visitors and raw business dictionaries are not
the supported protocol. Non-GraphElement sections/bends get no callbacks.
"""


def _owned_children(state,element):
    kind=state.kinds[id(element)]
    groups=[element.get('labels',())]
    if kind=='node':
        groups.extend((element.get('ports',()),element.get('children',()),state.contained_edges(element)))
    for group in groups:
        for child in group:
            if state.kinds.get(id(child))in('node','port','label','edge'):
                yield child


def graph_elements(state,root=None):
    root=state.graph if root is None else root
    if state.kinds.get(id(root))not in('node','port','label','edge'):
        raise ValueError('Traversal requires an actual owned graph element')
    frames=[iter((root,))]
    while frames:
        try:element=next(frames[-1])
        except StopIteration:
            frames.pop();continue
        yield element
        frames.append(iter(_owned_children(state,element)))


def apply_property_visitors(state,visitors,root=None):
    for element in graph_elements(state,root):
        for visitor in visitors:visitor(state,element)


def prepare_graph_properties(state,registry,root=None):
    """Actual two ordered passes; an existing root descriptor skips resolution."""
    from .deprecated import replace_deprecated_options
    from .resolver import visit_algorithm
    root=state.graph if root is None else root
    apply_property_visitors(state,[replace_deprecated_options],root)
    if not state.has_option(root,'resolvedAlgorithm'):
        apply_property_visitors(state,[lambda current,element:visit_algorithm(current,element,registry)],root)
