# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Fixed worker resolver/lookup and node-path/Java trim support, source proposal:
# references/next-algorithm-resolver-sources.json. Worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Actual per-node resolver; registry loading and recursive traversal separate.

Descriptors identify actual registered algorithms. They are not provider pools
or evidence that a native algorithm body has been integrated.
"""
from dataclasses import dataclass
from ..metadata._data import REFERENCE_ALGORITHM_IDS
from ..metadata._feature_data import ALGORITHM_FEATURES,GRAPH_FEATURES
from .._errors import UnknownAlgorithmError,UnsupportedAlgorithmError

_JAVA_TRIM=''.join(map(chr,range(33)))
_CONFIGURATION_ERROR='org.eclipse.elk.core.UnsupportedConfigurationException: '


@dataclass(frozen=True,eq=False)
class AlgorithmDescriptor:
    id:str
    supported_features:object=None

    def __post_init__(self):
        # Constructor source uses a new empty EnumSet when the builder has no
        # features, and otherwise retains the explicitly supplied set object.
        if self.supported_features is None:
            object.__setattr__(self,'supported_features',set())

    @property
    def features(self):return self.supported_features

    @property
    def feature_names(self):
        return tuple(feature for feature in GRAPH_FEATURES if self.supports_feature(feature))

    def supports_feature(self,feature):
        # Canonical names project the eight actual GraphFeature enum members.
        return type(feature)is str and feature in GRAPH_FEATURES and feature in self.supported_features

    def __eq__(self,other):
        return isinstance(other,AlgorithmDescriptor)and self.id==other.id

    def __hash__(self):return hash(self.id)


class AlgorithmRegistry:
    """Registered descriptor identities and unambiguous dotted suffix cache."""
    def __init__(self,identifiers=None):
        self.algorithms={name:AlgorithmDescriptor(name,set(ALGORITHM_FEATURES.get(name,())))for name in
                         (REFERENCE_ALGORITHM_IDS if identifiers is None else identifiers)}
        self._suffix_cache={}

    def lookup(self,identifier):
        if identifier is None or identifier=='':return None
        if type(identifier)is not str:raise TypeError('Algorithm identifier must be a string')
        if identifier in self._suffix_cache:return self._suffix_cache[identifier]
        found=None
        for name,data in self.algorithms.items():
            if name==identifier or name.endswith('.'+identifier):
                if found is not None:return None
                found=data
        if found is not None:self._suffix_cache[identifier]=found
        return found


def node_path_text(state,node):
    """Source node-only printElementPath, retaining identifier/label fallback."""
    parts=[]
    while node is not None:
        text=state.identifier_text(node)
        if not text:
            text=next((label['text']for label in node.get('labels',[])
                       if type(label.get('text'))is str and label['text']),None)
        parts.append('Node'+(' '+text if text else ''))
        node=state.parents[id(node)]
    return 'Root '+' > '.join(reversed(parts))


def _resolve_and_set(state,node,identifier,registry):
    data=registry.lookup(identifier)
    if data is None:return False
    state.set_option(node,'resolvedAlgorithm',data)
    return True


def resolve_algorithm(state,node,registry):
    """Resolve a known configured id first, then actual absent fallback guard."""
    if state.kinds.get(id(node))!='node':raise ValueError('Resolver requires an owned node')
    identifier=state.get_native_property(node,'algorithm')
    if _resolve_and_set(state,node,identifier,registry):return
    if (not state.has_option(node,'resolvedAlgorithm')
            and (node.get('children')or state.get_native_property(node,'insideSelfLoops.activate'))):
        if identifier is None or not identifier.strip(_JAVA_TRIM):
            if not _resolve_and_set(state,node,'org.eclipse.elk.layered',registry):
                raise UnsupportedAlgorithmError('UNSUPPORTED_ALGORITHM',state.paths[id(node)],
                    _CONFIGURATION_ERROR+'Unable to load default layout algorithm org.eclipse.elk.layered for unconfigured node '+node_path_text(state,node))
        else:
            raise UnknownAlgorithmError('UNKNOWN_ALGORITHM',state.paths[id(node)],
                _CONFIGURATION_ERROR+"Layout algorithm '"+identifier+"' not found for "+node_path_text(state,node))


def visit_algorithm(state,element,registry):
    """Actual visitor leaf; graph traversal/pruning is not implemented here."""
    if state.kinds.get(id(element))=='node' and not state.get_native_property(element,'noLayout'):
        resolve_algorithm(state,element,registry)
