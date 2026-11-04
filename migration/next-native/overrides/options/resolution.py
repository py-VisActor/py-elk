"""Presence-aware option parsing, independent of layout or runtime scheduling."""
from collections.abc import Mapping
from dataclasses import dataclass
import math
import re
from types import MappingProxyType

from .._errors import OptionValidationError, UnknownOptionError, UnsupportedOptionError
from .._json import clone_json, pointer
from ._catalogue import KNOWN_OPTION_IDS
from .schema import OPTION_SPECS, OptionSpec, Padding

_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_ALIASES = {spec.alias: spec.id for spec in OPTION_SPECS.values()}


@dataclass(frozen=True)
class ResolvedOptions:
    """Immutable typed results and source labels; raw source values are copied."""
    values: Mapping
    origins: Mapping
    selected_global: str
    _raw_values: dict

    @property
    def raw_values(self):
        return MappingProxyType(clone_json(self._raw_values))


def _container(value, path, *, omitted=False):
    if value is None and omitted:
        return {}
    if not isinstance(value, Mapping):
        raise OptionValidationError("INVALID_OPTION_CONTAINER", path, "Expected an option mapping")
    return clone_json(value, path=path, error_type=OptionValidationError)


def _canonical_id(key, path):
    canonical = key if key in KNOWN_OPTION_IDS else _ALIASES.get(key)
    if canonical is None and key.startswith("elk."):
        candidate = "org.eclipse." + key
        if candidate in KNOWN_OPTION_IDS:
            canonical = candidate
    if canonical is None:
        candidates = [name for name in KNOWN_OPTION_IDS if name.endswith("." + key)]
        if len(candidates) == 1:
            canonical = candidates[0]
    if canonical is None:
        raise UnknownOptionError("UNKNOWN_OPTION", path, "Unknown or unsupported identifier spelling: " + key)
    if canonical not in OPTION_SPECS:
        raise UnsupportedOptionError("UNSUPPORTED_OPTION", path, "Known reference option is not parsed by this slice: " + canonical)
    return canonical


def _invalid(path, message):
    raise OptionValidationError("INVALID_OPTION_VALUE", path, message)


def _number(value, path):
    original = value
    if type(value) is str:
        if not _DECIMAL.fullmatch(value):
            _invalid(path, "Expected a finite nonnegative number or decimal string")
        try:
            value = float(value)
        except (ValueError, OverflowError):
            _invalid(path, "Expected a finite nonnegative number")
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        _invalid(path, "Expected a finite nonnegative number")
    return value if type(original) is str else original


def _padding(value, path):
    fields = ("top", "right", "bottom", "left")
    if type(value) is str:
        if not value.startswith("[") or not value.endswith("]"):
            _invalid(path, "Expected a complete bracketed four-side padding string")
        parts = value[1:-1].split(",")
        parsed = {}
        for part in parts:
            pair = part.split("=")
            if len(pair) != 2 or pair[0].strip() not in fields or pair[0].strip() in parsed:
                _invalid(path, "Padding requires four unique top/right/bottom/left fields")
            parsed[pair[0].strip()] = pair[1].strip()
        value = parsed
    if not isinstance(value, Mapping) or set(value) != set(fields):
        _invalid(path, "Padding requires all and only top/right/bottom/left")
    return Padding(**{key: _number(value[key], pointer(path, key)) for key in fields})


def _parse(spec: OptionSpec, value, path):
    if spec.kind == 'opaque':
        raise UnsupportedOptionError('UNAVAILABLE_OBJECT_FACTORY', path,
            'The reference registers no raw data constructor for this property: ' + spec.id)
    if spec.kind == 'string':
        if type(value) is not str or value in ('', 'null'):
            _invalid(path, 'Expected a nonempty property string; null/empty values follow native strict input policy')
        return value
    if spec.kind == "algorithm":
        if type(value) is not str:
            _invalid(path, "Algorithm must be a string")
        if value not in spec.accepted_values:
            raise UnsupportedOptionError("UNSUPPORTED_OPTION", path, "This slice parses layered selection only")
        return "org.eclipse.elk.layered"
    if spec.kind == "enum":
        if type(value) is not str or value not in spec.accepted_values:
            _invalid(path, "Expected one of: " + ", ".join(spec.accepted_values))
        return value
    if spec.kind == "spacing":
        return _number(value, path)
    if spec.kind == "seed":
        if type(value) is str:
            if not _INTEGER.fullmatch(value):
                _invalid(path, "Seed must be a signed 32-bit integer or integer string")
            try:
                value = int(value)
            except ValueError:
                _invalid(path, "Seed must be a signed 32-bit integer")
        if type(value) is not int or not -(2**31) <= value < 2**31:
            _invalid(path, "Seed must be a signed 32-bit integer")
        return value
    if spec.kind == "boolean":
        if type(value) is bool:
            return value
        if type(value) is str and value.lower() in ("true", "false"):
            return value.lower() == "true"
        _invalid(path, "Expected bool or a true/false string")
    if spec.kind == "padding":
        return _padding(value, path)
    if spec.kind in ("enum_ordinal", "integer", "vector", "vector_chain", "signed_number", "enumset", "insets", "individual_spacings"):
        from .element import parse_extended
        return parse_extended(spec, value, path)
    raise AssertionError("Unimplemented internal option schema")


def _parse_scope(options, path, *, global_options=False):
    parsed, raw = {}, {}
    for key, value in options.items():
        where = pointer(path, key)
        canonical = _canonical_id(key, where)
        if canonical in parsed:
            raise OptionValidationError("AMBIGUOUS_OPTION", where, "Two aliases for the same option in one scope")
        adapted = value
        if global_options and OPTION_SPECS[canonical].kind in ("vector", "enumset", "insets", "individual_spacings") and type(value) in (list, dict):
            import json
            adapted = json.dumps(value, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        parsed[canonical] = _parse(OPTION_SPECS[canonical], adapted, where)
        raw[canonical] = clone_json(value, path=where, error_type=OptionValidationError)
    return parsed, raw


def resolve_options(*, constructor=None, layout_arguments=None, local=None):
    """Select one global mapping, then apply root/local values without mutation."""
    constructor = _container(constructor, "/constructor", omitted=True)
    arguments = _container(layout_arguments, "/layoutArguments", omitted=True)
    # Validate an explicit container's shape even when a later call replaces it;
    # do not parse its fields or let values leak out of an unselected global.
    if "defaultLayoutOptions" in constructor:
        defaults = _container(constructor["defaultLayoutOptions"], "/constructor/defaultLayoutOptions")
    else:
        defaults = {}
    if "layoutOptions" in arguments:
        selected = _container(arguments["layoutOptions"], "/layoutArguments/layoutOptions")
        label, path = "call", "/layoutArguments/layoutOptions"
    elif "defaultLayoutOptions" in constructor:
        selected = defaults
        label, path = "constructor", "/constructor/defaultLayoutOptions"
    else:
        selected, label, path = {}, "default", "/constructor/defaultLayoutOptions"
    local = _container(local, "/local", omitted=True)
    selected_values, raw = _parse_scope(selected, path, global_options=True)
    local_values, local_raw = _parse_scope(local, "/local")
    values = {key: spec.declared_default for key, spec in OPTION_SPECS.items()}
    origins = {key: "default" for key in OPTION_SPECS}
    values.update(selected_values)
    origins.update({key: label for key in selected_values})
    values.update(local_values)
    origins.update({key: "local" for key in local_values})
    raw.update(local_raw)
    if values["org.eclipse.elk.algorithm"] is None:
        values["org.eclipse.elk.algorithm"] = "org.eclipse.elk.layered"
        origins["org.eclipse.elk.algorithm"] = "layout-fallback"
    return ResolvedOptions(MappingProxyType(values), MappingProxyType(origins), label, raw)
