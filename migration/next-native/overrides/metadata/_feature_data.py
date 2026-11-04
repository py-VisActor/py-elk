# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Fixed elkjs0.12.1 registration declarations and GraphFeature enum.
# Source: references/next-recursive-coordinator-sources.json, worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Declared metadata features; these do not certify native body availability."""

GRAPH_FEATURES = (
    'SELF_LOOPS', 'INSIDE_SELF_LOOPS', 'MULTI_EDGES', 'EDGE_LABELS',
    'PORTS', 'COMPOUND', 'CLUSTERS', 'DISCONNECTED',
)

ALGORITHM_FEATURES = {
    'org.eclipse.elk.fixed': (),
    'org.eclipse.elk.box': (),
    'org.eclipse.elk.random': (),
    'org.eclipse.elk.layered': (
        'SELF_LOOPS', 'INSIDE_SELF_LOOPS', 'MULTI_EDGES', 'EDGE_LABELS',
        'PORTS', 'COMPOUND', 'CLUSTERS',
    ),
    'org.eclipse.elk.force': ('MULTI_EDGES', 'EDGE_LABELS'),
    'org.eclipse.elk.stress': (),
    'org.eclipse.elk.mrtree': ('DISCONNECTED',),
    'org.eclipse.elk.radial': (),
    'org.eclipse.elk.disco': (),
    'org.eclipse.elk.sporeOverlap': (),
    'org.eclipse.elk.sporeCompaction': (),
    'org.eclipse.elk.rectpacking': (),
}
