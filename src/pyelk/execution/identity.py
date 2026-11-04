"""Native process identity codes; internal host policy in ADR-0010."""
import itertools

_CODES=itertools.count(1)


def identity_hash(owner,obj):
    """Retain identity until owner release; preserve signed32 collision behavior."""
    if not hasattr(owner,'_identity_objects'): owner._identity_objects={}
    key=id(obj)
    if key not in owner._identity_objects:
        value=next(_CODES)&0xffffffff
        if value>=0x80000000: value-=0x100000000
        owner._identity_objects[key]=(obj,value)
    return owner._identity_objects[key][1]
