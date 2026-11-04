# SPDX-License-Identifier: (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0
# Copyright (c) Kiel University and others.
# Source sort adapter: Copyright 2008 Google Inc.; NOTICE-GWT-Ports.md.
# elkjs0.12.1 worker275e6caf, NodePromotion40185–40654.
"""Source node-promotion strategies, including model-order propagation."""
import math
from ...execution.diagnostics import BasicProgressMonitor
from .graph import Layer, set_layer
from .wrapping import incoming, outgoing, read
from .ports import _source_sort
from .integer_box_tokens import value_of_integer_box


class NodePromotion:
    source_name = 'NodePromotion'

    def get_layout_processor_configuration(self, graph):
        return None

    def _prepare(self, graph):
        self.node_size_affix = read(graph, 'SPACING_NODE_NODE')
        self.dummy_size = read(graph, 'SPACING_EDGE_NODE_BETWEEN_LAYERS')
        self.max_height = len(graph.layers)
        self.max_width = self.max_width_pixel = 0
        self.widths, self.width_pixels = [None] * self.max_height, [None] * self.max_height
        self.nodes, self.with_incoming = [], []
        count = 0
        for i, layer in enumerate(graph.layers):
            layer.id = self.max_height - 1 - i
            for node in layer.nodes:
                node.id = count
                count += 1
        self.layers = [0] * count
        self.degrees = [[0, 0, 0] for _ in range(count)]
        baggage = self.dummy_count = 0
        for layer in graph.layers:
            inc = out = 0
            pixels = 0.0
            for node in layer.nodes:
                self.layers[node.id] = node.layer.id
                pixels += node.size.y + self.node_size_affix
                ins, outs = sum(1 for _ in incoming(node)), sum(1 for _ in outgoing(node))
                self.degrees[node.id] = [outs - ins, ins, outs]
                inc += ins
                out += outs
                if ins > 0:
                    self.with_incoming.append(node)
                self.nodes.append(node)
            baggage -= inc
            width = len(layer.nodes) + baggage
            pixels += baggage * self.dummy_size
            self.widths[layer.id], self.width_pixels[layer.id] = width, pixels
            self.max_width = max(self.max_width, width)
            self.max_width_pixel = max(self.max_width_pixel, pixels)
            self.dummy_count += baggage
            baggage += out

    def _promote(self, node):
        def enter(current):
            position = self.layers[current.id]
            size = current.size.y + self.node_size_affix
            built = self.degrees[current.id][2]
            self.widths[position] = self.widths[position] - 1 + built
            self.width_pixels[position] = self.width_pixels[position] - size + built * self.dummy_size
            position += 1
            if position >= self.max_height:
                self.max_height += 1
                self.widths.append(1)
                self.width_pixels.append(size)
            else:
                reduced = self.degrees[current.id][1]
                self.widths[position] = self.widths[position] + 1 - reduced
                self.width_pixels[position] = self.width_pixels[position] + size - reduced * self.dummy_size
            allowed = True
            if self.strategy == 'NIKOLOV' and (self.widths[position] > self.max_width or self.widths[position - 1] > self.max_width):
                allowed = False
            if self.strategy == 'NIKOLOV_PIXEL' and (self.width_pixels[position] > self.max_width_pixel or self.width_pixels[position - 1] > self.max_width_pixel):
                allowed = False
            return [current, position, iter(incoming(current)), 0, allowed]
        stack = [enter(node)]
        while stack:
            frame = stack[-1]
            edge = next(frame[2], None)
            if edge is not None:
                master = edge.source.owner
                if self.layers[master.id] == frame[1]:
                    stack.append(enter(master))
                continue
            self.layers[frame[0].id] = frame[1]
            result = (frame[3] + self.degrees[frame[0].id][0], frame[4])
            stack.pop()
            if stack:
                stack[-1][3] += result[0]
                stack[-1][4] = stack[-1][4] and result[1]
        return result

    def _magic(self, continue_promotion):
        iteration = reduced = 0
        backup = list(self.layers)
        dummy_backup, height_backup = self.dummy_count, self.max_height
        widths_backup, pixels_backup = self.widths, self.width_pixels
        while True:
            promotions = 0
            for node in self.with_incoming:
                difference, allowed = self._promote(node)
                apply = allowed if self.strategy in ('NIKOLOV', 'NIKOLOV_PIXEL') else True
                if difference < 0 and apply:
                    promotions += 1
                    backup = list(self.layers)
                    self.dummy_count += difference
                    reduced += dummy_backup - self.dummy_count
                    # The literal source applies difference a second time here.
                    dummy_backup = self.dummy_count + difference
                    height_backup = self.max_height
                    widths_backup, pixels_backup = list(self.widths), list(self.width_pixels)
                else:
                    self.layers = list(backup)
                    self.dummy_count, self.max_height = dummy_backup, height_backup
                    self.widths, self.width_pixels = list(widths_backup), list(pixels_backup)
            iteration += 1
            if not (promotions != 0 and continue_promotion(reduced, iteration)):
                break

    def _new_layering(self, graph):
        layers = [Layer(graph, id=self.max_height - i) for i in range(self.max_height + 1)]
        for node in self.nodes:
            set_layer(node, layers[self.max_height - self.layers[node.id]])
        graph.layers[:] = [layer for layer in layers if layer.nodes]

    def _put(self, key, node):
        if node in self.node_keys:
            old = self.node_keys[node].value
            self.buckets[old].remove(node)
        self.buckets.setdefault(key, []).append(node)
        self.node_keys[node] = value_of_integer_box(key)
        if hasattr(self.graph, 'identity_hash'):
            self.graph.identity_hash(node)

    def _prepare_model(self, graph, left):
        self.buckets, self.node_keys = {}, {}
        count = 0
        def compare(first, second):
            if 'MODEL_ORDER' in first.properties and 'MODEL_ORDER' in second.properties:
                a, b = first.properties.get('MODEL_ORDER'), second.properties.get('MODEL_ORDER')
                return b - a if left else a - b
            return 0
        for i, layer in enumerate(graph.layers):
            layer.id = i
            for node in layer.nodes:
                node.id = count
                count += 1
        for layer in graph.layers:
            _source_sort(layer.nodes, compare)
            for node in layer.nodes:
                self._put(layer.id, node)

    def _promote_model(self, node, left):
        old = self.node_keys[node].value
        self._put(old + (1 if left else -1), node)
        result = []
        for edge in outgoing(node) if left else incoming(node):
            other = edge.target.owner if left else edge.source.owner
            if self.node_keys[other] is self.node_keys[node]:
                if hasattr(self.graph, 'identity_hash'):
                    self.graph.identity_hash(other)
                if other not in result:
                    result.append(other)
        return result

    def _model(self, left):
        self._prepare_model(self.graph, left)
        while True:
            changed = False
            layer_id = len(self.buckets) - 2 if left else 1
            while layer_id >= 0 if left else layer_id < len(self.buckets):
                current = self.buckets.get(layer_id, [])
                index = 0
                while index < len(current):
                    node = current[index]
                    index += 1
                    if 'MODEL_ORDER' not in node.properties:
                        continue
                    if (left and layer_id == max(self.buckets)) or (not left and layer_id == min(self.buckets)):
                        continue
                    model = node.properties.get('MODEL_ORDER')
                    promote = True
                    for other in current:
                        if 'MODEL_ORDER' in other.properties:
                            other_model = other.properties.get('MODEL_ORDER')
                            if (left and model < other_model) or (not left and model > other_model):
                                promote = False
                    if not promote:
                        continue
                    following = self.buckets.get(layer_id + (1 if left else -1), [])
                    allows, through, labels = False, True, False
                    for other in following:
                        if 'MODEL_ORDER' in other.properties:
                            if other.id != node.id:
                                allows = allows | (other.properties.get('MODEL_ORDER') < model if left else other.properties.get('MODEL_ORDER') > model)
                                through = False
                        elif not allows and through and other.type == 'LABEL':
                            labels = True
                            connected = next(incoming(other)).source.owner if left else next(outgoing(other)).target.owner
                            if connected is node:
                                far = next(outgoing(other)).target.owner if left else next(incoming(other)).source.owner
                                distance = self.node_keys[far].value - self.node_keys[connected].value if left else self.node_keys[connected].value - self.node_keys[far].value
                                if distance <= 2:
                                    through = False
                    if labels and through:
                        far = next(outgoing(node)).target.owner if left else next(incoming(node)).source.owner
                        distance = self.node_keys[far].value - self.node_keys[node].value if left else self.node_keys[node].value - self.node_keys[far].value
                        if distance <= 2 and far.type == 'NORMAL':
                            through = False
                    if allows or through:
                        pending = self._promote_model(node, left)
                        while pending:
                            item = pending.pop(0)
                            if hasattr(self.graph, 'identity_hash'):
                                self.graph.identity_hash(item)
                            for additional in self._promote_model(item, left):
                                if additional not in pending:
                                    pending.append(additional)
                        index -= 1
                        changed = True
                layer_id += -1 if left else 1
            if not changed:
                break
        self.graph.layers.clear()
        for key in sorted(self.buckets):
            nodes = self.buckets[key]
            if nodes:
                layer = Layer(self.graph, id=key)
                self.graph.layers.append(layer)
                for node in nodes:
                    set_layer(node, layer)

    def process(self, graph, monitor=None):
        monitor = monitor if monitor is not None else BasicProgressMonitor()
        monitor.begin('Node promotion heuristic', 1)
        self.graph = graph
        self.strategy = read(graph, 'LAYERING_NODE_PROMOTION_STRATEGY')
        if self.strategy in ('MODEL_ORDER_LEFT_TO_RIGHT', 'MODEL_ORDER_RIGHT_TO_LEFT'):
            self._model(self.strategy == 'MODEL_ORDER_LEFT_TO_RIGHT')
        else:
            self._prepare(graph)
            until = read(graph, 'LAYERING_NODE_PROMOTION_MAX_ITERATIONS')
            continuation = lambda reduced, iteration: True
            if self.strategy in ('NIKOLOV_IMPROVED', 'NIKOLOV_IMPROVED_PIXEL'):
                pixels = self.strategy == 'NIKOLOV_IMPROVED_PIXEL'
                self.strategy = 'NO_BOUNDARY'
                self._magic(continuation)
                if max(self.width_pixels if pixels else self.widths, default=0) > (self.max_width_pixel if pixels else self.max_width):
                    self.strategy = 'NIKOLOV_PIXEL' if pixels else 'NIKOLOV'
                    self._magic(continuation)
            else:
                if self.strategy == 'NODECOUNT_PERCENTAGE':
                    limit = math.ceil(len(self.layers) * until / 100)
                    continuation = lambda reduced, iteration: iteration < limit
                elif self.strategy == 'DUMMYNODE_PERCENTAGE':
                    limit = math.ceil(self.dummy_count * until / 100)
                    continuation = lambda reduced, iteration: reduced < limit
                self._magic(continuation)
            self._new_layering(graph)
        monitor.done()
