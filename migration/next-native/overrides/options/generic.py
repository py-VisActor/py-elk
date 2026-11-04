"""Static generic parsing declarations, separate from runtime Property owners.

The metadata default field describes LayoutOptionData only. This module does
not inject it into Core/algorithm getters, register executable algorithms, or
change the preserved bounded resolver. No reference files are read at runtime.
"""
from types import MappingProxyType

from .._errors import OptionValidationError, UnknownOptionError, UnsupportedOptionError
from .._json import clone_json, pointer
from ._catalogue import KNOWN_OPTION_IDS
from ._generic_data import SCALAR_DECLARATIONS
from ._core_defaults import CORE_SCALAR_DEFAULTS
from ._object_data import OBJECT_DECLARATIONS
from .resolution import _container, _parse
from .schema import OPTION_SPECS, OptionSpec, VectorChainValue, generic_spec


def _spec(row):
    canonical, kind, default, targets, members = row
    if kind == 'enumset' and default is not None:
        default = frozenset(default)
    return OptionSpec(canonical, canonical[len('org.eclipse.'):], kind, default, targets, members)


METADATA_SCALAR_SPECS = MappingProxyType({row[0]: _spec(row) for row in SCALAR_DECLARATIONS})

# A parsing declaration does not select an actual runtime Property owner.
# Existing reviewed Core/adapter defaults stay available; new declarations
# require an actual caller default until their owners are separately ported.
NO_RUNTIME_DEFAULT = object()
_OBJECT_TYPES = {row[0]: row for row in OBJECT_DECLARATIONS}


def _runtime_spec(canonical):
    if canonical not in METADATA_SCALAR_SPECS:
        if canonical in OPTION_SPECS:
            return generic_spec(canonical)
        _,kind,targets,_,_= _OBJECT_TYPES[canonical]
        # These actual Core declarations are in the independently reviewed
        # object closure. Other opaque owner defaults are not inferred.
        defaults={'org.eclipse.elk.position':None,'org.eclipse.elk.bendPoints':None,
                  'org.eclipse.elk.junctionPoints':VectorChainValue(),
                  'org.eclipse.elk.resolvedAlgorithm':None}
        return OptionSpec(canonical,canonical[len('org.eclipse.'):],kind,
                          defaults.get(canonical,NO_RUNTIME_DEFAULT),targets)
    spec = METADATA_SCALAR_SPECS[canonical]
    # The explicit old adapter projection (notably port border-offset0) has
    # its own reviewed caller semantics. New Core defaults use actual owners.
    default = (generic_spec(canonical).declared_default if canonical in OPTION_SPECS
               else CORE_SCALAR_DEFAULTS.get(canonical, NO_RUNTIME_DEFAULT))
    return OptionSpec(spec.id, spec.alias, spec.kind, default, spec.targets, spec.accepted_values)


RUNTIME_PROPERTY_SPECS = MappingProxyType({
    canonical: _runtime_spec(canonical)
    for canonical in dict.fromkeys((*METADATA_SCALAR_SPECS, *OPTION_SPECS, *_OBJECT_TYPES))
})
RAW_CONSTRUCTIBLE_PROPERTY_IDS = frozenset(key for key,spec in RUNTIME_PROPERTY_SPECS.items() if spec.kind!='opaque')


def runtime_spec(canonical):
    if canonical not in RUNTIME_PROPERTY_SPECS:
        raise UnsupportedOptionError('UNSUPPORTED_OPTION', '/layoutOptions/' + canonical,
                                     'Property parser has not been migrated: ' + canonical)
    return RUNTIME_PROPERTY_SPECS[canonical]


def canonical_generic_id(key, path):
    canonical = key if key in KNOWN_OPTION_IDS else None
    if canonical is None and key.startswith('elk.'):
        candidate = 'org.eclipse.' + key
        if candidate in KNOWN_OPTION_IDS:
            canonical = candidate
    if canonical is None:
        matches = [name for name in KNOWN_OPTION_IDS if name.endswith('.' + key)]
        if len(matches) == 1:
            canonical = matches[0]
    if canonical is None:
        raise UnknownOptionError('UNKNOWN_OPTION', path, 'Unknown or unsupported identifier spelling: ' + key)
    return canonical


def parse_generic_mapping(raw, path='/layoutOptions'):
    """Parse explicitly supplied scalar properties without choosing defaults.

    Targets are declarations used later by the actual global configurator;
    local JSON property import does not filter them. OBJECT factories remain a
    separate migration step. Existing finite and strict invalid-value policy
    applies; this does not claim all permissive source error coercions.
    """
    raw = _container(raw, path)
    parsed, original = {}, {}
    for spelling, value in raw.items():
        where = pointer(path, spelling)
        canonical = canonical_generic_id(spelling, where)
        if canonical in parsed:
            raise OptionValidationError('AMBIGUOUS_OPTION', where, 'Two aliases for the same option in one scope')
        if canonical not in METADATA_SCALAR_SPECS:
            raise UnsupportedOptionError('UNSUPPORTED_OPTION', where, 'OBJECT property parsing is not part of the scalar registry: ' + canonical)
        parsed[canonical] = _parse(METADATA_SCALAR_SPECS[canonical], value, where)
        original[canonical] = clone_json(value, path=where, error_type=OptionValidationError)
    return parsed, original
