# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P16B in references/e13-kernel-sources.json.
# Native enum/identity containers; existing Apache-noticed source sort reused.
"""Actual ordered phase realization, processor configurations and cached bodies."""
from .layout_configuration import LayeredPhase, LayoutProcessorConfiguration, RandomListAccessor
from .ports import _source_sort


class EnumBasedFactoryComparator:
    def compare(self, first, second):
        return first.ordinal - second.ordinal


class AlgorithmAssembler(RandomListAccessor):
    def __init__(self, phase_enum=LayeredPhase):
        super().__init__()
        self.processor_comparator = EnumBasedFactoryComparator()
        self.phases = tuple(phase_enum)
        self.number_of_phases = len(self.phases)
        if self.number_of_phases == 0:
            raise ValueError('There must be at least one phase in the phase enumeration.')
        self.configured_phases = set()
        self.additional_processors = LayoutProcessorConfiguration()
        self.cache = {}
        self.enable_caching = True
        self.fail_on_missing_phase = True

    def provide_default(self):
        return None

    def set_phase(self, phase, phase_factory):
        self.set_list_item(phase.ordinal, phase_factory)
        self.configured_phases.add(phase)
        return self

    def add_processor_configuration(self, configuration):
        self.additional_processors.add_all(configuration)
        return self

    def reset(self):
        self.list.clear()
        self.configured_phases.clear()
        self.additional_processors.clear()
        return self

    def retrieve_processor(self, factory):
        if self.enable_caching:
            if factory in self.cache:
                return self.cache[factory]
            processor = factory.create()
            self.cache[factory] = processor
            return processor
        return factory.create()

    def retrieve_processors(self, factories):
        ordered = list(factories)
        _source_sort(ordered, self.processor_comparator.compare)
        return [self.retrieve_processor(factory) for factory in ordered]

    def build(self, graph):
        if self.fail_on_missing_phase and len(self.configured_phases) < self.number_of_phases:
            raise RuntimeError('Expected ' + str(self.number_of_phases) + ' phases to be configured; only found ' + str(len(self.configured_phases)))
        implementations = []
        for phase in self.phases:
            factory = self.get_list_item(phase.ordinal)
            implementations.append(self.retrieve_processor(factory) if factory is not None else None)
        combined = LayoutProcessorConfiguration()
        for implementation in implementations:
            if implementation is not None:
                configuration = implementation.get_layout_processor_configuration(graph)
                if configuration is not None:
                    combined.add_all(configuration)
        combined.add_all(self.additional_processors)
        algorithm = []
        for phase in self.phases:
            algorithm.extend(self.retrieve_processors(set(combined.get_list_item(phase.ordinal))))
            implementation = implementations[phase.ordinal]
            if implementation is not None:
                algorithm.append(implementation)
        algorithm.extend(self.retrieve_processors(set(combined.get_list_item(self.phases[-1].ordinal + 1))))
        return algorithm
