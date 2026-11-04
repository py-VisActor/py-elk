"""Canonical enum identities for native collection-key adapters only.

Ordinary property values remain names. These process-lifetime symbols share
the existing native identity allocator; they do not replay the GWT heap.
Source contract: worker275e6caf Enum.hashCode_26 / ADR0010 / EC18.
"""
from .identity import identity_hash

class _EnumScope:pass

_SCOPE=_EnumScope()
_SYMBOLS={}
PORT_SIDE_DOMAIN='org.eclipse.elk.core.options.PortSide'
PORT_SIDE_ORDER=('UNDEFINED','NORTH','EAST','SOUTH','WEST')


def enum_symbol(domain,name):
    key=(domain,name)
    if key not in _SYMBOLS:_SYMBOLS[key]=object()
    return _SYMBOLS[key]


def enum_identity_hash(domain,name):
    return identity_hash(_SCOPE,enum_symbol(domain,name))


def enum_set_identity_hash(domain,values,order):
    code=0
    for name in order:
        if name in values:
            code=(code+enum_identity_hash(domain,name)+2147483648)%4294967296-2147483648
    return code
