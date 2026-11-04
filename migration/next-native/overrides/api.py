"""Full native async ELK wiring; implementation awaits unified acceptance."""
from collections.abc import Mapping

from ._errors import (OptionValidationError, ResourceClosedError,
                      UnsupportedAlgorithmError, UnsupportedFeatureError,
                      UnsupportedWorkerError)
from ._json import clone_json, pointer
from .execution.metadata_service import NativeMetadataService


class ELK:
    """Native recursive layout with isolated, cancellable execution.

    ``max_pending`` includes the running task; ``timeout`` covers submission
    through result, including queueing and process startup. The full reference
    metadata and provider caches belong to a persistent worker per instance.
    The complete wiring is in migration and has not passed unified acceptance.
    """

    def __init__(self, options=None, *, max_pending=16, timeout=None):
        options = {} if options is None else options
        if not isinstance(options, Mapping):
            raise OptionValidationError("INVALID_OPTION_CONTAINER", "/constructor", "Expected a mapping")
        for key in options:
            if type(key) is not str:
                raise OptionValidationError("INVALID_JSON", "/constructor", "JSON object keys must be strings")
            if key in ("workerUrl", "workerFactory"):
                raise UnsupportedWorkerError("UNSUPPORTED_WORKER", pointer("/constructor", key),
                                             "JavaScript worker construction is unavailable in the native host")
            if key not in ("defaultLayoutOptions", "algorithms"):
                raise UnsupportedFeatureError("UNSUPPORTED_SLICE", pointer("/constructor", key),
                                              "Unknown native constructor option")
        if "algorithms" in options and type(options["algorithms"]) is not list:
            raise OptionValidationError("INVALID_OPTION_VALUE", "/constructor/algorithms", "Expected a list of algorithm strings")
        self._options = clone_json(options, path="/constructor", error_type=OptionValidationError)
        if "algorithms" in self._options and any(type(name)is not str for name in self._options['algorithms']):
            raise OptionValidationError('INVALID_OPTION_VALUE','/constructor/algorithms','Expected algorithm strings')
        self._registry = NativeMetadataService(self._options.get("algorithms"))
        from .execution.full_lifecycle import FullExecutionController

        self._controller = FullExecutionController(self._options, max_pending=max_pending, timeout=timeout)
        self._closed = False
        self._last_trace = []
        self._submission = 0

    @property
    def last_trace(self):
        """An independent development trace, never part of returned ELK JSON."""
        return clone_json(self._last_trace)

    async def layout(self, graph, args=None):
        self._last_trace = []
        self._submission += 1
        submission = self._submission
        self._require_open()
        result = await self._controller.execute(graph, args)
        if submission == self._submission and not self._closed:
            self._last_trace = clone_json(result.trace)
        return result.graph

    def _require_open(self):
        if self._closed:
            raise ResourceClosedError("RESOURCE_CLOSED", "", "The native instance is closed")

    async def knownLayoutAlgorithms(self):
        """Return independent descriptions of algorithms registered here."""
        self._require_open()
        return self._registry.algorithms()

    async def knownLayoutOptions(self):
        """Return the selected real metadata option declarations."""
        self._require_open()
        return self._registry.options()

    async def knownLayoutCategories(self):
        """Return categories related to this instance's registered algorithms."""
        self._require_open()
        return self._registry.categories()

    def terminateWorker(self):
        """Close idempotently and synchronously reclaim native execution work."""
        self._closed = True
        self._submission += 1
        self._last_trace = []
        self._controller.close()

    def close(self):
        self.terminateWorker()

    def __enter__(self):
        self._require_open()
        return self

    def __exit__(self,*exc):
        self.terminateWorker()

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self,*exc):
        self.terminateWorker()
