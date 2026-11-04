# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. elkjs0.12.1 worker275e6caf,
# optsToCfg81909-81929; HOST-13/B/global-options-source-review-01.json.
"""Actual selected-registry global option parsing, before class application.

Class targets, NO_OVERWRITE and native type4 cloning remain in the existing
property reader. This does not implement arbitrary LayoutConfigurator filters.
"""
from ..options.generic import RUNTIME_PROPERTY_SPECS
from .local_properties import lookup_option,_parse_text,_SKIP
from .json_text import json_value_text,object_keys


def serialize_global_value(value):
    return value if type(value)is str else json_value_text(value)


def parse_global_mapping(raw,path='/selectedGlobalOptions',*,metadata=None):
    result={}
    for spelling in object_keys(raw):
        canonical=lookup_option(spelling,metadata)
        if canonical is None:continue
        parsed=_parse_text(RUNTIME_PROPERTY_SPECS[canonical],serialize_global_value(raw[spelling]),
                           path+'/'+spelling,metadata)
        if parsed is not _SKIP:result[canonical]=parsed
    return result
