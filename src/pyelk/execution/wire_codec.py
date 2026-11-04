"""Flat JSON-tree tokens for process messages, independent of graph depth.

Tokens are two-item tuples: ('v', scalar), ('a', None), ('o', None),
('k', string), ('e', None). Containers are closed explicitly. Repeated
noncyclic input references are expanded; no object graph or typed property
objects are serialized by this JSON-only boundary.
"""
from collections.abc import Mapping
import math

from .._errors import ValidationError
from .._json import _Path, _path_text


def encode_json_tree(value):
    """Encode a JSON value without recursive pickle/container nesting."""
    tokens = []; active = set(); frames = [('value', value, '')]
    while frames:
        frame = frames.pop()
        if frame[0] == 'items':
            _, item, where, iterator, mapping = frame
            try: key, child = next(iterator)
            except StopIteration:
                active.remove(id(item)); tokens.append(('e', None)); continue
            if mapping:
                if type(key) is not str:
                    raise ValidationError('INVALID_JSON', _path_text(where), 'JSON object keys must be strings')
                tokens.append(('k', key))
            frames.append(frame); frames.append(('value', child, _Path(where, key)))
            continue
        _, item, where = frame
        if item is None or type(item) in (str, bool, int): tokens.append(('v', item))
        elif type(item) is float:
            if not math.isfinite(item):
                raise ValidationError('INVALID_JSON', _path_text(where), 'JSON numbers must be finite')
            tokens.append(('v', item))
        elif isinstance(item, Mapping) or type(item) is list:
            if id(item) in active:
                raise ValidationError('INVALID_JSON', _path_text(where), 'JSON cannot contain a cycle')
            active.add(id(item)); mapping = isinstance(item, Mapping)
            tokens.append(('o' if mapping else 'a', None))
            frames.append(('items', item, where, iter(item.items()) if mapping else enumerate(item), mapping))
        else:
            raise ValidationError('INVALID_JSON', _path_text(where), 'Expected a JSON value')
    return tokens


def decode_json_tree(tokens):
    """Decode the flat protocol into independent built-in JSON containers."""
    missing = object(); root = missing; frames = []
    for token in tokens:
        if type(token) not in (tuple, list) or len(token) != 2:
            raise ValueError('Invalid JSON tree token')
        operation, payload = token
        if operation == 'k':
            if (not frames or type(frames[-1][0]) is not dict
                    or frames[-1][1] is not missing or type(payload) is not str):
                raise ValueError('Invalid JSON object key token')
            frames[-1][1] = payload
            continue
        if operation == 'e':
            if payload is not None or not frames or frames[-1][1] is not missing:
                raise ValueError('Invalid JSON container closing token')
            frames.pop()
            continue
        if operation == 'v':
            if not (payload is None or type(payload) in (str, bool, int)
                    or type(payload) is float and math.isfinite(payload)):
                raise ValueError('Invalid JSON scalar token')
            value = payload
        elif operation in ('a', 'o') and payload is None:
            value = [] if operation == 'a' else {}
        else:
            raise ValueError('Invalid JSON tree operation')
        if not frames:
            if root is not missing: raise ValueError('More than one JSON root token')
            root = value
        else:
            parent, key = frames[-1]
            if type(parent) is list: parent.append(value)
            else:
                if key is missing: raise ValueError('JSON object value has no key')
                parent[key] = value; frames[-1][1] = missing
        if operation in ('a', 'o'): frames.append([value, missing])
    if root is missing or frames: raise ValueError('Incomplete JSON tree tokens')
    return root
