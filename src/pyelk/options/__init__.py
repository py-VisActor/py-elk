"""Internal option schemas and parsing; no executable layout registry."""
from ._catalogue import KNOWN_OPTION_IDS
from .resolution import ResolvedOptions, resolve_options
from .schema import OPTION_SPECS, OptionSpec, Padding

__all__ = ["KNOWN_OPTION_IDS", "OPTION_SPECS", "OptionSpec", "Padding", "ResolvedOptions", "resolve_options"]
