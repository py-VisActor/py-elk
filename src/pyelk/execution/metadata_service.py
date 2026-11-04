# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright Kiel University and others. Fixed worker275e6caf metadata service;
# source review HOST-12/B/metadata-registration-source-review-01.json.
"""Native provider-selected metadata, without certifying executable bodies.

One service owns descriptor references and their provider pools. Share it with
the Session and RecursiveLayoutEngine for one configured native runtime.
Descriptions are compiled static declarations; no reference files are loaded.
"""
from .._json import clone_json
from ..metadata._feature_data import ALGORITHM_FEATURES
from ..metadata._registration_data import (DEFAULT_PROVIDERS,CORE_ALGORITHMS,
    CORE_OPTIONS,CATEGORY_IDS,PROVIDER_MEMBERSHIP,LEGACY_IDS,
    ALGORITHM_DESCRIPTIONS,OPTION_DESCRIPTIONS,CATEGORY_DESCRIPTIONS)
from .resolver import AlgorithmRegistry,AlgorithmDescriptor
from .pools import ProviderPools


class NativeMetadataService:
    def __init__(self,providers=None):
        self.registry=AlgorithmRegistry(())
        self.pools=ProviderPools()
        self.option_ids={}
        self._option_suffix_cache={}
        self.register(DEFAULT_PROVIDERS if providers is None else providers)

    def _add(self,algorithm_ids,option_ids):
        for name in algorithm_ids:
            self.registry.algorithms[name]=AlgorithmDescriptor(name,set(ALGORITHM_FEATURES[name]))
        for name in option_ids:self.option_ids[name]=None

    def register(self,providers):
        """Register Core and selected exact short names, preserving id order.

        Repeated registration replaces descriptor objects. Source resets only
        option suffix caches; successful algorithm suffix cache references stay.
        """
        if type(providers)not in(list,tuple):raise TypeError('Provider registration requires a list or tuple')
        self._add(CORE_ALGORITHMS,CORE_OPTIONS)
        self._option_suffix_cache.clear()
        for name in providers:
            if type(name)is not str:raise TypeError('Provider selector must be a string')
            key='spore'if name in('sporeOverlap','sporeCompaction')else name
            membership=PROVIDER_MEMBERSHIP.get(key)
            # Only the two actual Spore selectors select its metadata provider.
            if name=='spore':membership=None
            if membership is not None:
                self._add(membership['algorithms'],membership['options'])
                self._option_suffix_cache.clear()

    def lookup_algorithm(self,suffix):return self.registry.lookup(suffix)

    def lookup_option(self,suffix):
        if type(suffix)is not str or not suffix:return None
        if suffix in self._option_suffix_cache:return self._option_suffix_cache[suffix]
        found=None
        for name in self.option_ids:
            if name==suffix or name.endswith('.'+suffix):
                if found is not None:return None
                found=name
        if found is None:
            for name in self.option_ids:
                for legacy in LEGACY_IDS.get(name,()):
                    if legacy==suffix or legacy.endswith('.'+suffix):
                        if found is not None:return None
                        found=name
        if found is not None:self._option_suffix_cache[suffix]=found
        return found

    def algorithms(self):
        rows=[]
        for name,descriptor in self.registry.algorithms.items():
            row=clone_json(ALGORITHM_DESCRIPTIONS[name])
            row.pop('supportedFeatures',None)
            features=descriptor.feature_names
            if features:row['supportedFeatures']=list(features)
            rows.append(row)
        return rows

    def options(self):return [clone_json(OPTION_DESCRIPTIONS[name])for name in self.option_ids]

    def categories(self):
        rows=[]
        for name in CATEGORY_IDS:
            row=clone_json(CATEGORY_DESCRIPTIONS[name]);row.pop('knownLayouters',None)
            algorithms=[identifier for identifier in self.registry.algorithms
                        if ALGORITHM_DESCRIPTIONS[identifier].get('category','')==name]
            if algorithms:row['knownLayouters']=algorithms
            rows.append(row)
        return rows
