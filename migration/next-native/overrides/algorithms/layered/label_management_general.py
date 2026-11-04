# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 LabelManagementProcessor39428-39442, actual compiled callback.
"""The fixed Source's null-only label-manager callback."""
from ...execution.diagnostics import BasicProgressMonitor
from .native_adapters import _read_property


def label_management_processor(graph, *, monitor=None):
    if monitor is None:
        monitor = BasicProgressMonitor()
    monitor.begin('Label management', 1)
    manager = _read_property(graph, 'org.eclipse.elk.labels.labelManager')
    if manager is not None:
        raise TypeError('The fixed Layered label-manager callback only accepts null')
    monitor.done()
