# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Copyright (c) Kiel University and others.
# Reuses the attributed Guava scalar adapter in algorithms/spore.py unchanged.
# Fixed elkjs0.12.1 worker275e6caf; P17E actual all-accept filter closure.
"""Source Layered base-spacing builder over its fixed 14 declared properties.

Property hash codes are distinct for this fixed source set. Its map traversal
therefore has constructor insertion order; this is not a generic map facade.
"""
from ...options.owners import scalar_owner_default
from ..spore import _fuzzy_compare


_SOURCE_SYMBOLS = (
    'SPACING_NODE_NODE_0',
    'SPACING_COMPONENT_COMPONENT_0',
    'SPACING_EDGE_EDGE',
    'SPACING_EDGE_LABEL_0',
    'SPACING_EDGE_NODE',
    'SPACING_LABEL_LABEL',
    'SPACING_LABEL_NODE',
    'SPACING_LABEL_PORT_HORIZONTAL',
    'SPACING_LABEL_PORT_VERTICAL',
    'SPACING_NODE_SELF_LOOP',
    'SPACING_PORT_PORT',
    'SPACING_EDGE_EDGE_BETWEEN_LAYERS_0',
    'SPACING_EDGE_NODE_BETWEEN_LAYERS_0',
    'SPACING_NODE_NODE_BETWEEN_LAYERS_0',
)


def _accept_declared_target(holder, property_id):
    # Actual source accept_149 examines arg1, the Property (not EObject171).
    # All fixed Property keys here accept; no generic metadata lookup is run.
    return True


def _no_overwrite(holder, property_id):
    return property_id not in holder.properties


class _NoOpConsumer:
    def __call__(self, holder):
        # A real default/fuzzy source branch, not an unimplemented callback.
        return None

    accept = __call__


class _ApplyingConsumer:
    def __init__(self, builder):
        self.builder = builder

    def __call__(self, holder):
        builder = self.builder
        for property_id, factor in builder.factor_map.items():
            if all(predicate(holder, property_id) for predicate in builder.filters):
                holder.properties[property_id] = factor * builder.base_spacing

    accept = __call__


class LayeredSpacingsBuilder:
    def __init__(self, base_spacing):
        self.filters = [_accept_declared_target]
        self.factor_map = {}
        self.base_spacing = base_spacing
        base_id, self.base_default = scalar_owner_default('LayeredOptions', _SOURCE_SYMBOLS[0])
        self.defaults = {base_id: self.base_default}
        self.factor_map[base_id] = 1.0
        for symbol in _SOURCE_SYMBOLS[1:]:
            property_id, default = scalar_owner_default('LayeredOptions', symbol)
            self.defaults[property_id] = default
            factor = default / self.base_default if self.base_default is not None and default is not None else 1.0
            self.factor_map[property_id] = factor

    def build(self):
        self.filters.append(_no_overwrite)
        # Existing 1e-4 adapter returns zero exactly on the source fuzzyEquals
        # branch, including exact equality/infinities and both-NaN semantics.
        if _fuzzy_compare(self.base_spacing, self.base_default, 1e-4) == 0:
            return _NoOpConsumer()
        return _ApplyingConsumer(self)

    def apply(self, holder):
        self.build().accept(holder)
