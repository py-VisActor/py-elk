# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Seven fixed worker helper closures in next-recursive-coordinator-sources.json.
# SHA256 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Source-approved recursive helpers, separate from recursive scheduling."""
from .resolver import AlgorithmDescriptor
import math


def supported_features(builder,features):
    """Source metadata-builder setter: retain the provided set, return builder."""
    builder.supported_features=features
    return builder


def supports_feature(descriptor,feature):
    return descriptor.supports_feature(feature)


def count_nodes_recursively(state,node,count_ancestors=False):
    # Explicit frames retain recursive Number grouping without a Python stack
    # limit. A containment getter need not invent a JSON 'children': [] member.
    frames=[[iter(node.get('children',())),float(len(node.get('children',())))]]
    while frames:
        try:
            child=next(frames[-1][0])
        except StopIteration:
            count=frames.pop()[1]
            if frames:
                frames[-1][1]+=count
                continue
            break
        children=child.get('children',())
        if children:
            frames.append([iter(children),float(len(children))])
    if count_ancestors:
        parent=state.parents[id(node)]
        while parent is not None:
            count+=len(parent.get('children',()))
            parent=state.parents[id(parent)]
    return count


def _resolved(state,node):
    value=state.get_native_property(node,'resolvedAlgorithm')
    if value is not None and not isinstance(value,AlgorithmDescriptor):
        raise TypeError('Resolved algorithm must be an AlgorithmDescriptor')
    return value


def count_nodes_with_hierarchy(state,node):
    frames=[[node,iter(node.get('children',())),float(len(node.get('children',())))]]
    while frames:
        parent,children,_=frames[-1]
        try:
            child=next(children)
        except StopIteration:
            count=frames.pop()[2]
            if frames:
                frames[-1][2]+=count
                continue
            return count
        if state.get_native_property(child,'hierarchyHandling')!='SEPARATE_CHILDREN':
            parent_data,child_data=_resolved(state,parent),_resolved(state,child)
            # The first source reference comparison includes None/None.
            if (parent_data is child_data or parent_data is not None and parent_data==child_data):
                descendants=child.get('children',())
                if descendants:
                    frames.append([child,iter(descendants),float(len(descendants))])


def evaluate_hierarchy_handling_inheritance(state,node):
    if state.get_native_property(node,'hierarchyHandling')=='INHERIT':
        parent=state.parents[id(node)]
        handling=('SEPARATE_CHILDREN' if parent is None
                  else state.get_native_property(parent,'hierarchyHandling'))
        state.set_option(node,'hierarchyHandling',handling)


def apply_configured_node_scaling(state,node):
    factor=state.read_native_property(node,'scaleFactor')
    if factor==1:
        return
    node['width'],node['height']=factor*node.get('width',0),factor*node.get('height',0)
    ports=node.get('ports',())
    # The source concatenates own labels, own ports, then port labels. Retain
    # duplicate native anchor references and scale them at each encounter.
    for shapes in (node.get('labels',()),ports,
                   (label for port in ports for label in port.get('labels',()))):
        for shape in shapes:
            shape['x'],shape['y']=factor*shape.get('x',0),factor*shape.get('y',0)
            shape['width'],shape['height']=factor*shape.get('width',0),factor*shape.get('height',0)
            # Actual Core PORT_ANCHOR is nullable. The adapter's zero vector
            # fallback must not create an anchor property on these holders.
            anchor=state.read_native_property(shape,'port.anchor',None)
            if anchor is not None:
                anchor.x*=factor
                anchor.y*=factor


def _maximum(first,second):
    if math.isnan(first)or math.isnan(second):return math.nan
    if first==second==0:
        return 0.0 if math.copysign(1.0,first)>0 or math.copysign(1.0,second)>0 else -0.0
    return first if first>=second else second


def _minimum(first,second):
    return -_maximum(-first,-second)


def compute_child_area_dimensions(state,node):
    min_x=min_y=math.inf
    max_x=max_y=0
    edges=state.contained_edges(node)
    edge_labels=(label for edge in edges for label in edge.get('labels',()))
    for shapes in (node.get('labels',()),node.get('children',()),edge_labels):
        for shape in shapes:
            margins=state.read_native_property(shape,'margins')
            if min_x>shape.get('x',0)-margins.left:
                min_x=shape.get('x',0)-margins.left
            if min_y>shape.get('y',0)-margins.top:
                min_y=shape.get('y',0)-margins.top
            if max_x<shape.get('x',0)+shape.get('width',0)+margins.right:
                max_x=shape.get('x',0)+shape.get('width',0)+margins.right
            if max_y<shape.get('y',0)+shape.get('height',0)+margins.bottom:
                max_y=shape.get('y',0)+shape.get('height',0)+margins.bottom
    for edge in edges:
        for section in edge.get('sections',()):
            start,end=section['startPoint'],section['endPoint']
            min_x=_minimum(min_x,start['x'])
            min_x=_minimum(min_x,end['x'])
            max_x=_maximum(max_x,start['x'])
            max_x=_maximum(max_x,end['x'])
            min_y=_minimum(min_y,start['y'])
            min_y=_minimum(min_y,end['y'])
            max_y=_maximum(max_y,start['y'])
            max_y=_maximum(max_y,end['y'])
            for point in section.get('bendPoints',()):
                min_x=_minimum(min_x,point['x'])
                max_x=_maximum(max_x,point['x'])
                min_y=_minimum(min_y,point['y'])
                max_y=_maximum(max_y,point['y'])
    # These are real Core opaque output properties, not JSON business fields.
    state.set_option(node,'childAreaWidth',max_x-min_x)
    state.set_option(node,'childAreaHeight',max_y-min_y)
