"""Instance-local registered native metadata, separate from reference catalogues."""
from .._errors import OptionValidationError, UnknownAlgorithmError, UnsupportedAlgorithmError
from .._json import clone_json, pointer
from ._data import ALGORITHMS, CATEGORIES, OPTIONS, REFERENCE_ALGORITHM_IDS


LAYERED_ID = "org.eclipse.elk.layered"
_ALIASES = {"layered": LAYERED_ID, **{name.removeprefix("org.eclipse.elk."): name
                                      for name in REFERENCE_ALGORITHM_IDS}}


def classify_algorithm(value, path):
    """Validate a selector without silently mapping another algorithm to layered."""
    if type(value) is not str:
        raise OptionValidationError("INVALID_OPTION_VALUE", path, "Algorithm must be a string")
    canonical = value if value in REFERENCE_ALGORITHM_IDS else _ALIASES.get(value)
    if canonical is None:
        raise UnknownAlgorithmError("UNKNOWN_ALGORITHM", path, "Unknown algorithm identifier: " + value)
    if canonical != LAYERED_ID:
        raise UnsupportedAlgorithmError("UNSUPPORTED_ALGORITHM", path, "Known algorithm is not implemented: " + canonical)
    return canonical


class MetadataRegistry:
    """Only the implemented layered provider can be registered by an instance."""

    def __init__(self, algorithms=None):
        if algorithms is None:
            algorithms = ["layered"]
        if type(algorithms) is not list:
            raise OptionValidationError("INVALID_OPTION_VALUE", "/constructor/algorithms", "Expected a list of algorithm strings")
        selected = []
        for index, name in enumerate(algorithms):
            algorithm = classify_algorithm(name, pointer("/constructor/algorithms", index))
            if algorithm not in selected:
                selected.append(algorithm)
        self._registered = tuple(selected)

    @property
    def has_layered(self):
        return LAYERED_ID in self._registered

    def algorithms(self):
        return clone_json(ALGORITHMS if self.has_layered else [])

    def options(self):
        return clone_json(OPTIONS)

    def categories(self):
        return clone_json(CATEGORIES if self.has_layered else [])


__all__ = ["MetadataRegistry"]
