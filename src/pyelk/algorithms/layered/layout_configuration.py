# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others.
# Fixed elkjs0.12.1 worker SHA256:
# 275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P16A in references/e13-kernel-sources.json.
# Original native enum/identity-set/list view, no Java collection runtime copied.
"""Actual lazy configuration buckets and fluent before/after state."""
from enum import Enum


class LayeredPhase(Enum):
    P1_CYCLE_BREAKING = 0
    P2_LAYERING = 1
    P3_NODE_ORDERING = 2
    P4_NODE_PLACEMENT = 3
    P5_EDGE_ROUTING = 4

    @property
    def ordinal(self):
        return self.value


class RandomListAccessor:
    def __init__(self):
        self.list = []

    def provide_default(self):
        raise NotImplementedError

    def ensure_list_size(self, size):
        while len(self.list) < size:
            self.list.append(self.provide_default())

    def get_list_item(self, index):
        if index < 0:
            raise IndexError('Invalid index: ' + str(index))
        self.ensure_list_size(index + 1)
        return self.list[index]

    def set_list_item(self, index, value):
        if index < 0:
            raise IndexError('Invalid index: ' + str(index))
        if index < len(self.list):
            self.list[index] = value
        else:
            self.ensure_list_size(index)
            self.list.append(value)


class LayoutProcessorConfiguration(RandomListAccessor):
    def __init__(self):
        super().__init__()
        self.list.clear()
        self.current_index = -1

    def provide_default(self):
        return set()

    def _do_add(self, index, processor):
        self.get_list_item(index).add(processor)

    def add_before(self, phase, processor):
        self.current_index = -1
        self._do_add(phase.ordinal, processor)
        return self

    def add_after(self, phase, processor):
        self.current_index = -1
        self._do_add(phase.ordinal + 1, processor)
        return self

    def before(self, phase):
        self.current_index = phase.ordinal
        return self

    def after(self, phase):
        self.current_index = phase.ordinal + 1
        return self

    def add(self, processor):
        if self.current_index < 0:
            raise RuntimeError('Did not call before(...) or after(...) before calling add(...).')
        self._do_add(self.current_index, processor)
        return self

    def add_all(self, configuration):
        index = 0
        while index < len(configuration.list):
            self.get_list_item(index).update(configuration.get_list_item(index))
            index += 1
        return self

    def clear(self):
        self.list.clear()
        self.current_index = -1
        return self


def create_from(source):
    return LayoutProcessorConfiguration().add_all(source)
