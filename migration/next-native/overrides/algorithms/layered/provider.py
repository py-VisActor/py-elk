# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf; P19A actual flat driver.
"""Persistent Layered controller over actual configured processor bodies.

Native import/transfer and compound orchestration are separate source closures.
This controller does not delegate to the old bounded layout entry point.
"""
from ...execution.diagnostics import BasicProgressMonitor
from .components_general import ComponentsProcessor
from .graph_configurator import GraphConfigurator
from .input_model_sort import SortByInputModelProcessor
from .phase_factories import FactoryRegistry
from .ports import _divide
from .processor_class_names import PROCESSOR_CLASS_NAMES
from .resize_general import clear_layers, resize_graph
from .compound_pre import CompoundGraphPreprocessor


def _source_class_name(processor):
    # source_name is an explicit factory construction fact, never the Python
    # wrapper class name or the intermediate factory enum name.
    if isinstance(processor, SortByInputModelProcessor):
        name = 'SortByInputModelProcessor'
    else:
        name = processor.source_name
    return PROCESSOR_CLASS_NAMES[name]


class LayeredProvider:
    def __init__(self):
        self.graph_configurator = GraphConfigurator(FactoryRegistry())
        self.components_processor = ComponentsProcessor()
        self.compound_graph_preprocessor = CompoundGraphPreprocessor()

    @staticmethod
    def layout_component(graph, monitor):
        was_running = monitor.is_running()
        if not was_running:
            monitor.begin('Component Layout', 1)
        algorithm = graph.properties['PROCESSORS']
        progress = _divide(1.0, len(algorithm))
        if monitor.record_logs:
            monitor.log('ELK Layered uses the following ' + str(len(algorithm)) + ' modules:')
            for slot, processor in enumerate(algorithm):
                number = ('0' if slot < 10 else '') + str(slot)
                monitor.log('   Slot ' + number + ': ' + _source_class_name(processor))
        for processor in algorithm:
            if monitor.is_canceled():
                return
            processor.process(graph, monitor.sub_task(progress))
        clear_layers(graph)
        if not was_running:
            monitor.done()

    def do_layout(self, graph, monitor=None):
        the_monitor = monitor
        if the_monitor is None:
            the_monitor = BasicProgressMonitor()
            the_monitor._max_levels = 0
        the_monitor.begin('Layered layout', 1)
        self.graph_configurator.prepare_graph_for_layout(graph)
        components = self.components_processor.split(graph)
        if len(components) == 1:
            self.layout_component(components[0], the_monitor)
        else:
            progress = _divide(1.0, len(components))
            for component in components:
                # Fixed source reads the original argument here, including its
                # null-monitor failure. Public provider callers pass a monitor.
                if monitor.is_canceled():
                    return
                self.layout_component(component, the_monitor.sub_task(progress))
        self.components_processor.combine(components, graph)
        resize_graph(graph)
        the_monitor.done()

    def __call__(self, state, node, monitor=None):
        from .native_import_hierarchical import HierarchicalElkGraphImporter
        from .native_transfer import ElkGraphLayoutTransferrer
        graph = HierarchicalElkGraphImporter(state).import_graph(node)
        if state.read_owner_scalar_property(node, 'LayeredOptions', 'HIERARCHY_HANDLING') == 'INCLUDE_CHILDREN':
            from .hierarchical_driver import do_compound_layout
            from .compound_post import compound_postprocessor
            do_compound_layout(self, graph, monitor,
                               preprocessor=self.compound_graph_preprocessor,
                               postprocessor=compound_postprocessor)
        else:
            self.do_layout(graph, monitor)
        if not monitor.is_canceled():
            ElkGraphLayoutTransferrer(state).apply_layout(graph)
