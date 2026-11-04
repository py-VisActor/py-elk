"""Explicit actual-owner scalar defaults; no automatic owner selection.

Structured defaults need their own native object/factory identity. Observation
identity labels in the static declarations are never Python object identities.
"""
from ._owner_data import OWNER_PROPERTY_DECLARATIONS

_DECLARATIONS={(row[0],row[1]):row for row in OWNER_PROPERTY_DECLARATIONS}


def scalar_owner_default(owner,symbol):
    """Return the actual Property id/default for an explicitly named owner."""
    row=_DECLARATIONS[owner,symbol]
    value=row[3]
    if row[6]:raise ValueError('A structured owner default requires its actual native factory')
    if isinstance(value,tuple):
        tag,payload=value
        if tag=='enum':value=payload
        elif tag=='negativeZero':value=-0.0
        else:raise ValueError('A structured owner default requires its actual native factory')
    return row[2],value
