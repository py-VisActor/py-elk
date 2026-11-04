# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Fixed elkjs0.12.1 gather/post and actual hyperedge incident-owner helpers.
# Source: next-recursive-coordinator-sources.json; support observations in
# HOST11/V/inside-self-loops-source-review-01.json. Worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Inside-loop helpers over actual owned Session graph objects.

Import establishes unique per-shape incidence in edge encounter order. This
module neither rebuilds arbitrary EMF inverse mutations nor adds edge/section
admission limits. The main recursive scheduler is a separate component.
"""

_EMPTY_INSIDE_SELF_LOOPS=()


def all_outgoing_edges(state,node):
    """Node's own outgoing list, then each physical port's list; no dedup."""
    yield from state.incidence(node,incoming=False)
    for port in node.get('ports',()):
        yield from state.incidence(port,incoming=False)


def connectable_shape_to_node(state,shape):
    if shape is None:
        raise ValueError('connectableShape cannot be null')
    kind=state.kinds.get(id(shape))
    if kind=='node':
        return shape
    if kind=='port':
        return state.owners[id(shape)]
    raise TypeError('Only support nodes and ports.')


def _shape(state,identifier):
    # Source endpoint lists contain actual references; the importer's unique
    # typed-ID index supplies those same native object identities here.
    return state.shapes[(type(identifier),identifier)]


def is_self_loop(state,edge):
    common_node=None
    for endpoints in (edge.get('sources',()),edge.get('targets',())):
        for identifier in endpoints:
            shape_node=connectable_shape_to_node(state,_shape(state,identifier))
            if common_node is None:
                common_node=shape_node
            elif common_node is not shape_node:
                return False
    return True


def gather_inside_self_loops(state,node):
    if not state.read_native_property(node,'insideSelfLoops.activate'):
        return _EMPTY_INSIDE_SELF_LOOPS
    inside=[]
    for edge in all_outgoing_edges(state,node):
        if is_self_loop(state,edge)and state.read_native_property(edge,'insideSelfLoops.yo'):
            inside.append(edge)
    return inside


def post_process_inside_self_loops(state,inside):
    for edge in inside:
        # Missing source or section is an actual failing index access. Do not
        # silently select another edge, make a section or skip this occurrence.
        node=connectable_shape_to_node(state,_shape(state,edge.get('sources',())[0]))
        dx,dy=node['x'],node['y']
        section=edge.get('sections',())[0]
        start,end=section['startPoint'],section['endPoint']
        start['x'],start['y']=start['x']+dx,start['y']+dy
        end['x'],end['y']=end['x']+dx,end['y']+dy
        for point in section.get('bendPoints',()):
            point['x'],point['y']=point['x']+dx,point['y']+dy
        # Actual Core JUNCTION_POINTS defaults to a cloned/cached empty chain.
        # Always read it, and keep existing Vec objects and duplicate aliases.
        for point in state.get_native_property(edge,'junctionPoints'):
            point.x+=dx
            point.y+=dy
