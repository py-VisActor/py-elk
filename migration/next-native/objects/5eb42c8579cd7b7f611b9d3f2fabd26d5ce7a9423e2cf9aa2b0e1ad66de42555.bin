# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker275e6caf: P17C raw error-string source closure.
"""Actual imported nonproxy ELK shapes, independent of native designations."""
from ...execution.diagnostics import number_text


def _designation(state, raw):
    identifier = state.identifier_text(raw)
    if identifier:
        return ' "' + identifier + '"'
    labels = raw.get('labels', [])
    if labels and labels[0].get('text'):
        return ' "' + labels[0]['text'] + '"'
    return ''


def raw_shape_text(state, raw):
    kind = state.kinds[id(raw)]
    if kind not in ('node', 'port'):
        raise TypeError('Expected an actual imported node or port')
    text = ('ElkNode' if kind == 'node' else 'ElkPort') + _designation(state, raw)
    return (text + ' (' + number_text(raw.get('x', 0.0)) + ','
            + number_text(raw.get('y', 0.0)) + ' | '
            + number_text(raw.get('width', 0.0)) + ','
            + number_text(raw.get('height', 0.0)) + ')')


def raw_edge_text(state, raw):
    if state.kinds[id(raw)] != 'edge':
        raise TypeError('Expected an actual imported edge')
    sources, targets = raw.get('sources', []), raw.get('targets', [])
    hyperedge = len(sources) > 1 or len(targets) > 1
    def endpoints(identifiers):
        text = ', '.join(raw_shape_text(state, state.shapes[(type(value), value)])
                         for value in identifiers)
        return '[' + text + ']' if hyperedge else text
    return ('ElkEdge' + _designation(state, raw) + ' ' + endpoints(sources)
            + ' -> ' + endpoints(targets))
