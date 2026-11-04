"""Explicit actual-owner scalar reads over native stored Layered properties.

Native field names and source Property symbols are explicit caller facts.
Structured defaults and Integer identity are separate source adapters.
"""
from ...options.owners import scalar_owner_default


def read_layered_scalar(holder, native_key, symbol):
    value = holder.properties.get(native_key)
    if value is not None:
        return value
    _, value = scalar_owner_default('LayeredOptions', symbol)
    return value
