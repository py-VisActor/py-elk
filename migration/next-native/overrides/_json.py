"""Lossless JSON-value copies for internal model/configuration ownership."""
from collections.abc import Mapping
import math

from ._errors import ValidationError


def pointer(path: str, key: str | int) -> str:
    """Append one escaped RFC 6901 component; the document root is ''."""
    escaped = str(key).replace("~", "~0").replace("/", "~1")
    return path + "/" + escaped


def clone_json(value, *, path: str = "", error_type=ValidationError):
    """Copy JSON-compatible mappings/lists without coercion or shared children.

    Mapping is a host convenience. Tuples, arbitrary objects, non-string keys,
    cycles and nonfinite floats are rejected, including inside business data.
    Repeated references that do not form a cycle are copied independently.
    """
    active = set()
    result = [None]
    frames = [('visit', value, path, result, 0)]
    while frames:
        frame = frames.pop()
        if frame[0] == 'iterate':
            _, item, where, target, iterator, mapping = frame
            try:
                key, child = next(iterator)
            except StopIteration:
                active.remove(id(item))
                continue
            if mapping and type(key) is not str:
                raise error_type('INVALID_JSON', _path_text(where), 'JSON object keys must be strings')
            frames.append(frame)
            if not mapping: target.append(None)
            frames.append(('visit', child, _Path(where, key), target, key))
            continue
        _, item, where, parent, key = frame
        if item is None or type(item) in (str, bool, int):
            parent[key] = item
        elif type(item) is float:
            if not math.isfinite(item):
                raise error_type('INVALID_JSON', _path_text(where), 'JSON numbers must be finite')
            parent[key] = item
        elif isinstance(item, Mapping) or type(item) is list:
            if id(item) in active:
                raise error_type('INVALID_JSON', _path_text(where), 'JSON cannot contain a cycle')
            active.add(id(item))
            mapping = isinstance(item, Mapping)
            target = {} if mapping else []
            parent[key] = target
            iterator = iter(item.items()) if mapping else enumerate(item)
            frames.append(('iterate', item, where, target, iterator, mapping))
        else:
            raise error_type('INVALID_JSON', _path_text(where), 'Expected a JSON value')
    return result[0]


class _Path:
    """Linked path components avoid quadratic strings in valid deep business data."""
    __slots__ = ('parent', 'component')

    def __init__(self, parent, key):
        self.parent = parent
        self.component = '/' + str(key).replace('~', '~0').replace('/', '~1')


def _path_text(where):
    components = []
    while isinstance(where, _Path):
        components.append(where.component)
        where = where.parent
    components.append(where)
    return ''.join(reversed(components))


def finite_number(value, *, path: str, nonnegative: bool = False, error_type=ValidationError):
    """Check a geometry number without accepting bool or coercing strings."""
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (nonnegative and value < 0):
        description = "finite nonnegative number" if nonnegative else "finite number"
        raise error_type("INVALID_NUMBER", path, "Expected a " + description)
    return value


def json_wire(value):
    """Clone final JSON output using the reference JSON.stringify number rule.

    Original JSONNumber retains NaN/infinities internally. The reference wire
    turns those generated numbers into null. Input validation and algorithm
    arithmetic retain their separate rules; this helper never changes them.
    """
    result = [None]; active = set()
    frames = [('visit', value, result, 0)]
    while frames:
        frame = frames.pop()
        if frame[0] == 'iterate':
            _, item, target, iterator, mapping = frame
            try: key, child = next(iterator)
            except StopIteration:
                active.remove(id(item)); continue
            frames.append(frame)
            if not mapping: target.append(None)
            frames.append(('visit', child, target, key))
            continue
        _, item, parent, key = frame
        if type(item) is float:
            parent[key] = item if math.isfinite(item) else None
        elif item is None or type(item) in (str, int, bool):
            parent[key] = item
        elif type(item) in (dict, list):
            if id(item) in active: raise ValueError('JSON cannot contain a cycle')
            active.add(id(item)); mapping = type(item) is dict
            target = {} if mapping else []; parent[key] = target
            frames.append(('iterate', item, target, iter(item.items()) if mapping else enumerate(item), mapping))
        else:
            raise ValueError('Non-JSON value at final output boundary')
    return result[0]
