# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Actual fixed elkjs0.12.1 model-order producer spans:
# references/next-model-order-producer-sources.json. Worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Real import producer; geometry/endpoint transformation belongs to callers."""
from .integer_box_tokens import value_of_integer_box

_GROUP='layered.considerModelOrder.groupModelOrder.cycleBreakingId'


def needs_model_order(state,parent):
    """Actual owner defaults and source predicate/short-circuit order."""
    read=lambda name,default:state.read_native_property(parent,'layered.'+name,default)
    cycle=(read('cycleBreaking.strategy','GREEDY')in
           ('MODEL_ORDER','BFS_NODE_ORDER','DFS_NODE_ORDER','GREEDY_MODEL_ORDER','SCC_CONNECTIVITY','SCC_NODE_TYPE'))
    layering=(read('layering.strategy','NETWORK_SIMPLEX')in('BF_MODEL_ORDER','DF_MODEL_ORDER')
              or read('layering.nodePromotion.strategy','NONE')in('MODEL_ORDER_LEFT_TO_RIGHT','MODEL_ORDER_RIGHT_TO_LEFT'))
    crossing=(read('considerModelOrder.strategy','NONE')!='NONE'
              or read('crossingMinimization.forceNodeModelOrder',False)
              or read('considerModelOrder.components','NONE')!='NONE'
              or read('considerModelOrder.crossingCounterNodeInfluence',0)!=0
              or read('considerModelOrder.crossingCounterPortInfluence',0)!=0)
    return cycle or layering or crossing


def _assign_origin_order(state,holder,index):
    # Actual private Property id; no same-named business JSON import or default.
    state.computed_options.setdefault(id(holder),{})['modelOrder']=index
    state._computed_integer_boxes.setdefault(id(holder),{})['modelOrder']=value_of_integer_box(index)


def _assign_native_integer(holder,key,value):
    holder.properties[key]=value
    if not hasattr(holder,'integer_box_identities'):holder.integer_box_identities={}
    holder.integer_box_identities[key]=value_of_integer_box(value)


def bind_model_order(state,origin,native):
    """Copy actual stored order and the same token at the property-copy point."""
    snapshot=state.property_snapshot(origin)
    if snapshot.has('modelOrder'):
        native.properties['MODEL_ORDER']=snapshot.get_native('modelOrder')
        if not hasattr(native,'integer_box_identities'):native.integer_box_identities={}
        native.integer_box_identities['MODEL_ORDER']=snapshot.integer_boxes['modelOrder']


def transform_ordered_ports(state,node,transform_port):
    """Assign before port NO_LAYOUT filtering, guarded by its parent's node."""
    index=0
    for port in node.get('ports',[]):
        if (needs_model_order(state,state.parents[id(node)])
                and not state.read_native_property(node,'layered.considerModelOrder.noModelOrder',False)):
            _assign_origin_order(state,port,index);index+=1
        if not state.read_native_property(port,'noLayout',False):transform_port(port)


def import_flat_model_order(state,root,native_graph,*,transform_node,transform_edge):
    """Run actual flat producer order around supplied real transform bodies.

    Callbacks own geometry, endpoints and the remaining source filters. Node
    property copying and ordered-port transformation occur inside transform_node.
    This function does not implement the remaining flat importer or layout.
    """
    index=0;groups=set()
    for child in root.get('children',[]):
        if not state.read_native_property(child,'noLayout',False):
            if (needs_model_order(state,state.parents[id(child)])
                    and not state.read_native_property(child,'layered.considerModelOrder.noModelOrder',False)):
                _assign_origin_order(state,child,index);index+=1
                if state.has_option(child,_GROUP):groups.add(state.get_native_property(child,_GROUP))
            transform_node(child)
    _assign_native_integer(native_graph,'MAX_MODEL_ORDER_NODES',index)
    _assign_native_integer(native_graph,'CB_NUM_MODEL_ORDER_GROUPS',len(groups))
    index=0
    for edge in state.contained_edges(root):
        if needs_model_order(state,root):
            _assign_origin_order(state,edge,index);index+=1
        transform_edge(edge)
