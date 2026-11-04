# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P21B generic PropertyHolder caller.
"""Actual external-port dummy math over native property holders."""
from .graph import LNode, LPort, Vec2, set_port_owner
from .native_properties import CanonicalPropertyMap
from .ports import _divide, set_side
from .property_access import read_layered_scalar


FROM_DIRECTION = {'RIGHT': 'EAST', 'LEFT': 'WEST', 'DOWN': 'SOUTH',
                  'UP': 'NORTH', 'UNDEFINED': 'UNDEFINED'}
OPPOSED = {'NORTH': 'SOUTH', 'SOUTH': 'NORTH', 'EAST': 'WEST',
           'WEST': 'EAST', 'UNDEFINED': 'UNDEFINED'}


def create_external_port_dummy(holder, constraints, side, net_flow, node_size,
                               position, port_size, direction, graph):
    final_side = side
    dummy = LNode(graph, type='EXTERNAL_PORT', properties=CanonicalPropertyMap())
    dummy.integer_box_identities = dummy.properties.integer_boxes
    dummy.labels = []
    dummy.properties['EXT_PORT_SIZE'] = port_size
    dummy.properties['PORT_CONSTRAINTS'] = 'FIXED_POS'
    offset = read_layered_scalar(holder, 'PORT_BORDER_OFFSET', 'PORT_BORDER_OFFSET')
    dummy.properties['PORT_BORDER_OFFSET'] = offset
    port = LPort(properties=CanonicalPropertyMap())
    port.integer_box_identities = port.properties.integer_boxes
    port.labels = []
    set_port_owner(port, dummy)
    if constraints in ('FREE', 'UNDEFINED'):
        final_side = FROM_DIRECTION[direction] if net_flow >= 0 else OPPOSED[FROM_DIRECTION[direction]]
        holder.properties['PORT_SIDE'] = final_side
    anchor = Vec2()
    explicit = False
    if 'PORT_ANCHOR' in holder.properties:
        value = holder.properties['PORT_ANCHOR']
        anchor.x, anchor.y = value.x, value.y
        explicit = True
    else:
        anchor.x, anchor.y = port_size.x / 2, port_size.y / 2
    if final_side in ('WEST', 'EAST'):
        dummy.properties['LAYER_CONSTRAINT'] = 'FIRST_SEPARATE' if final_side == 'WEST' else 'LAST_SEPARATE'
        dummy.properties['EDGE_CONSTRAINT'] = 'OUTGOING_ONLY' if final_side == 'WEST' else 'INCOMING_ONLY'
        dummy.size.y = port_size.y
        if offset < 0:
            dummy.size.x = -offset
        set_side(port, 'EAST' if final_side == 'WEST' else 'WEST')
        if not explicit:
            anchor.x = port_size.x if final_side == 'WEST' else 0.0
        if final_side == 'WEST':
            anchor.x -= port_size.x
    elif final_side in ('NORTH', 'SOUTH'):
        dummy.properties['IN_LAYER_CONSTRAINT'] = 'TOP' if final_side == 'NORTH' else 'BOTTOM'
        dummy.size.x = port_size.x
        if offset < 0:
            dummy.size.y = -offset
        set_side(port, 'SOUTH' if final_side == 'NORTH' else 'NORTH')
        if not explicit:
            anchor.y = port_size.y if final_side == 'NORTH' else 0.0
        if final_side == 'NORTH':
            anchor.y -= port_size.y
    port.pos.x, port.pos.y = anchor.x, anchor.y
    dummy.properties['PORT_ANCHOR'] = anchor
    if constraints in ('FIXED_ORDER', 'FIXED_RATIO', 'FIXED_POS'):
        information = 0.0
        if constraints == 'FIXED_ORDER' and 'PORT_INDEX' in holder.properties:
            if final_side in ('NORTH', 'EAST'):
                information = holder.properties['PORT_INDEX']
            elif final_side in ('SOUTH', 'WEST'):
                information = -holder.properties['PORT_INDEX']
        elif final_side in ('WEST', 'EAST'):
            information = position.y
            if constraints == 'FIXED_RATIO':
                information = _divide(information, node_size.y)
        elif final_side in ('NORTH', 'SOUTH'):
            information = position.x
            if constraints == 'FIXED_RATIO':
                information = _divide(information, node_size.x)
        dummy.properties['PORT_RATIO_OR_POSITION'] = information
    dummy.properties['EXT_PORT_SIDE'] = final_side
    return dummy
