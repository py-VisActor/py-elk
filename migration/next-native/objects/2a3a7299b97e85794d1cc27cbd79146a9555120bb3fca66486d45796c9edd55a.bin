# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Fixed worker DeprecatedLayoutOptionReplacer two-rule closure, source review
# HOST11/V/pool-deprecated-source-review-01.json; worker SHA256
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
"""Actual per-element replacement, without whole-graph visitor traversal."""


def replace_deprecated_options(state,element):
    # Source rule is presence based, even for an explicit false legacy value.
    if state.has_option(element,'portLabels.nextToPortIfPossible'):
        state.get_native_property(element,'portLabels.placement').add('NEXT_TO_PORT_IF_POSSIBLE')
        state.remove_option(element,'portLabels.nextToPortIfPossible')
    if state.has_option(element,'nodeSize.options'):
        options=state.get_native_property(element,'nodeSize.options')
        if 'SPACE_EFFICIENT_PORT_LABELS'in options:
            state.get_native_property(element,'portLabels.placement').add('SPACE_EFFICIENT')
            options.remove('SPACE_EFFICIENT_PORT_LABELS')
