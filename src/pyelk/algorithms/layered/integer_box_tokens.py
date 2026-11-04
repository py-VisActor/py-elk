# Original Python host identity adapter; project license selection remains separate.
# Source Integer/valueOf identity observations: component P08D,
# references/e13-kernel-sources.json; no GWT runtime code transplanted.
# Fixed worker SHA256 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Original opaque source Integer identities; numeric getters remain numeric.

The fixed generated Integer/valueOf bodies are observations, not transplanted
runtime code. A token records identity and its numeric payload for adapters.
"""
from dataclasses import dataclass

@dataclass(eq=False, frozen=True)
class IntegerBoxToken:
    value: int
_VALUE_OF_CACHE = {}

def new_integer_box(value):
    """A source direct-new Integer allocation, including small numeric values."""
    return IntegerBoxToken(value)

def value_of_integer_box(value):
    """Source valueOf identity observations, without Python int-identity guesses."""
    if -128 <= value <= 127:
        if value not in _VALUE_OF_CACHE:
            _VALUE_OF_CACHE[value] = new_integer_box(value)
        return _VALUE_OF_CACHE[value]
    return new_integer_box(value)

def holder_integer_box_identity(holder, property_name, declared_default_token):
    """Standalone native view; central adapters may supply an explicit getter.

    Explicit properties require their actual parse/assignment token. Shallowly
    copying the map values preserves source sharing. No numeric range is
    rejected here; provenance is a separate native representation obligation.
    """
    identities = getattr(holder, 'integer_box_identities', None)
    if identities is not None and property_name in identities:
        return identities[property_name]
    if property_name not in holder.properties:
        return declared_default_token
    raise TypeError('Actual Integer box provenance is required for ' + property_name)
