"""One read-only source-validation transaction; no cached validation result.

Independent checks always create a new scope. Nested source checks share only
their input bytes/parsed JSON. Before a successful outer return, every input
is read again and parsed objects are checked for accidental mutation. Ordinary
layout_checks.load calls outside a scope retain their original fresh semantics.
"""
from contextvars import ContextVar
import asyncio
from dataclasses import dataclass, field
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path
from threading import get_ident

_CURRENT = ContextVar("pyelk_source_read_scope", default=None)
_UNPARSED = object()


def _owner():
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return os.getpid(), get_ident(), task


def _scope():
    current = _CURRENT.get()
    return current if current is not None and current.active and current.owner == _owner() else None


class SourceReadChanged(ValueError):
    """An input or an in-memory input object changed during a source check."""


def _strict_json(value, active=None):
    """JSON serialization alone cannot distinguish tuple/list or int/str keys."""
    kind = type(value)
    if kind not in (dict, list):
        if kind is float:
            if not math.isfinite(value):
                raise ValueError("Nonfinite JSON number")
        elif kind not in (str, int, bool, type(None)):
            raise TypeError("Source inputs require exact JSON types")
        return
    active = set() if active is None else active
    if id(value) in active:
        raise ValueError("Circular source JSON value")
    active.add(id(value))
    try:
        if kind is dict:
            for key, child in value.items():
                if type(key) is not str:
                    raise TypeError("Source JSON keys require strings")
                _strict_json(child, active)
        else:
            for child in value:
                _strict_json(child, active)
    finally:
        active.remove(id(value))


def _json_bytes(value):
    # Deliberately uncached. Preserve object insertion order as well as values.
    _strict_json(value)
    return json.dumps(value, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


@dataclass
class _Entry:
    path: Path
    target: Path
    raw: bytes
    digest: str
    value: object = _UNPARSED
    parsed_bytes: bytes | None = None


@dataclass
class _Scope:
    entries: dict = field(default_factory=dict)
    owner: tuple = field(default_factory=_owner)
    active: bool = True

    def read(self, path):
        path = Path(path).absolute()
        if path not in self.entries:
            raw = path.read_bytes()
            self.entries[path] = _Entry(path, path.resolve(), raw,
                                        hashlib.sha256(raw).hexdigest())
        return self.entries[path]

    def verify(self):
        for entry in self.entries.values():
            try:
                same = entry.path.resolve() == entry.target and entry.path.read_bytes() == entry.raw
            except OSError as error:
                raise SourceReadChanged("Source input disappeared during validation: " + str(entry.path)) from error
            if not same:
                raise SourceReadChanged("Source input bytes/path changed during validation: " + str(entry.path))
            if entry.value is not _UNPARSED:
                try:
                    same = _json_bytes(entry.value) == entry.parsed_bytes
                except (TypeError, ValueError, OverflowError, RecursionError) as error:
                    raise SourceReadChanged("Source JSON data changed during validation: " + str(entry.path)) from error
                if not same:
                    raise SourceReadChanged("Source JSON data changed during validation: " + str(entry.path))


def read_digest(path):
    scope = _scope()
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if scope is None else scope.read(path).digest


def read_json(path, parse):
    scope = _scope()
    if scope is None:
        return parse(Path(path).read_text(encoding="utf-8"))
    entry = scope.read(path)
    if entry.value is _UNPARSED:
        # Match text-mode universal-newline decoding. Raw identity above stays
        # exact and is never replaced with this parsed-text representation.
        text = entry.raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        value = parse(text)
        entry.parsed_bytes = _json_bytes(value)
        entry.value = value
    return entry.value


def readonly_source_check(function):
    """Scope a source checker without memoizing its result or its decisions."""
    @wraps(function)
    def scoped(*args, **kwargs):
        if _scope() is not None:
            return function(*args, **kwargs)
        scope = _Scope()
        token = _CURRENT.set(scope)
        try:
            result = function(*args, **kwargs)
            try:
                scope.verify()
            except SourceReadChanged as error:
                # Match existing source checkers' fail-closed report contract.
                # Do not leave a successful gate/canonical flag in a failed row.
                if not isinstance(result, dict) or not isinstance(result.get("errors"), list):
                    raise
                result["errors"].append(str(error))
                result["status"] = "FAIL"
                for key in ("wholeSourceApproved", "canonicalVerified"):
                    if key in result:
                        result[key] = False
            return result
        finally:
            scope.active = False
            _CURRENT.reset(token)
    return scoped
