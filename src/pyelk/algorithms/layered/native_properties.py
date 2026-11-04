# SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later
# Copyright (c) Kiel University and others; source Property id bindings.
# Native key/token mappings are original host adapters, not GWT collections.
# Fixed worker275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86.
# Component P16E in references/e13-kernel-sources.json.
"""Opt-in canonical stored-property map for the new full Layered importer.

This bag stores actual source ids, never chooses default owners or allocates
default objects. Old Layered graph dict fields are not changed globally.
"""
from collections.abc import Mapping, MutableMapping

from ...options._catalogue import KNOWN_OPTION_IDS
from .integer_box_tokens import IntegerBoxToken


_ALIAS_IDS = {
    'ALGORITHM': 'org.eclipse.elk.algorithm',
    'ALIGNMENT': 'org.eclipse.elk.alignment',
    'ALLOW_NON_FLOW_PORTS_TO_SWITCH_SIDES': 'org.eclipse.elk.layered.allowNonFlowPortsToSwitchSides',
    'ASPECT_RATIO': 'org.eclipse.elk.aspectRatio',
    'BARYCENTER_ASSOCIATES': 'barycenterAssociates',
    'BEND_POINTS': 'org.eclipse.elk.bendPoints',
    'BOTTOM_COMMENTS': 'BottomSideComments',
    'BOX_PACKING_MODE': 'org.eclipse.elk.box.packingMode',
    'BREAKING_POINT_INFO': 'breakingPoint.info',
    'CB_NUM_MODEL_ORDER_GROUPS': 'modelOrderGroups.cb.number',
    'CHILD_AREA_HEIGHT': 'org.eclipse.elk.childAreaHeight',
    'CHILD_AREA_WIDTH': 'org.eclipse.elk.childAreaWidth',
    'COMMENT_BOX': 'org.eclipse.elk.commentBox',
    'COMMENT_CONN_PORT': 'CommentConnectionPort',
    'COMPACTION_CONNECTED_COMPONENTS': 'org.eclipse.elk.layered.compaction.connectedComponents',
    'COMPACTION_POST_COMPACTION_CONSTRAINTS': 'org.eclipse.elk.layered.compaction.postCompaction.constraints',
    'COMPACTION_POST_COMPACTION_STRATEGY': 'org.eclipse.elk.layered.compaction.postCompaction.strategy',
    'COMPOUND_NODE': 'compoundNode',
    'CONSIDER_MODEL_ORDER_COMPONENTS': 'org.eclipse.elk.layered.considerModelOrder.components',
    'CONSIDER_MODEL_ORDER_CROSSING_COUNTER_NODE_INFLUENCE': 'org.eclipse.elk.layered.considerModelOrder.crossingCounterNodeInfluence',
    'CONSIDER_MODEL_ORDER_CROSSING_COUNTER_PORT_INFLUENCE': 'org.eclipse.elk.layered.considerModelOrder.crossingCounterPortInfluence',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CB_GROUP_ORDER_STRATEGY': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cbGroupOrderStrategy',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CB_PREFERRED_SOURCE_ID': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cbPreferredSourceId',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CB_PREFERRED_TARGET_ID': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cbPreferredTargetId',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_ENFORCED_GROUP_ORDERS': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cmEnforcedGroupOrders',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CM_GROUP_ORDER_STRATEGY': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cmGroupOrderStrategy',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_COMPONENT_GROUP_ID': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.componentGroupId',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CROSSING_MINIMIZATION_ID': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.crossingMinimizationId',
    'CONSIDER_MODEL_ORDER_GROUP_MODEL_ORDER_CYCLE_BREAKING_ID': 'org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cycleBreakingId',
    'CONSIDER_MODEL_ORDER_LONG_EDGE_STRATEGY': 'org.eclipse.elk.layered.considerModelOrder.longEdgeStrategy',
    'CONSIDER_MODEL_ORDER_NO_MODEL_ORDER': 'org.eclipse.elk.layered.considerModelOrder.noModelOrder',
    'CONSIDER_MODEL_ORDER_PORT_MODEL_ORDER': 'org.eclipse.elk.layered.considerModelOrder.portModelOrder',
    'CONSIDER_MODEL_ORDER_STRATEGY': 'org.eclipse.elk.layered.considerModelOrder.strategy',
    'CONTENT_ALIGNMENT': 'org.eclipse.elk.contentAlignment',
    'COORDINATE_SYSTEM_ORIGIN': 'coordinateOrigin',
    'CROSSING_HINT': 'crossingHint',
    'CROSSING_MINIMIZATION_FORCE_NODE_MODEL_ORDER': 'org.eclipse.elk.layered.crossingMinimization.forceNodeModelOrder',
    'CROSSING_MINIMIZATION_GREEDY_SWITCH_ACTIVATION_THRESHOLD': 'org.eclipse.elk.layered.crossingMinimization.greedySwitch.activationThreshold',
    'CROSSING_MINIMIZATION_GREEDY_SWITCH_HIERARCHICAL_TYPE': 'org.eclipse.elk.layered.crossingMinimization.greedySwitchHierarchical.type',
    'CROSSING_MINIMIZATION_GREEDY_SWITCH_TYPE': 'org.eclipse.elk.layered.crossingMinimization.greedySwitch.type',
    'CROSSING_MINIMIZATION_HIERARCHICAL_SWEEPINESS': 'org.eclipse.elk.layered.crossingMinimization.hierarchicalSweepiness',
    'CROSSING_MINIMIZATION_IN_LAYER_PRED_OF': 'org.eclipse.elk.layered.crossingMinimization.inLayerPredOf',
    'CROSSING_MINIMIZATION_IN_LAYER_SUCC_OF': 'org.eclipse.elk.layered.crossingMinimization.inLayerSuccOf',
    'CROSSING_MINIMIZATION_POSITION_CHOICE_CONSTRAINT': 'org.eclipse.elk.layered.crossingMinimization.positionChoiceConstraint',
    'CROSSING_MINIMIZATION_POSITION_ID': 'org.eclipse.elk.layered.crossingMinimization.positionId',
    'CROSSING_MINIMIZATION_SEMI_INTERACTIVE': 'org.eclipse.elk.layered.crossingMinimization.semiInteractive',
    'CROSSING_MINIMIZATION_STRATEGY': 'org.eclipse.elk.layered.crossingMinimization.strategy',
    'CROSS_HIERARCHY_MAP': 'crossHierarchyMap',
    'CYCLE_BREAKING_STRATEGY': 'org.eclipse.elk.layered.cycleBreaking.strategy',
    'CYCLIC': 'cyclic',
    'DEBUG_MODE': 'org.eclipse.elk.debugMode',
    'DIRECTION': 'org.eclipse.elk.direction',
    'DIRECTION_CONGRUENCY': 'org.eclipse.elk.layered.directionCongruency',
    'EDGE_CONSTRAINT': 'edgeConstraint',
    'EDGE_LABELS_CENTER_LABEL_PLACEMENT_STRATEGY': 'org.eclipse.elk.layered.edgeLabels.centerLabelPlacementStrategy',
    'EDGE_LABELS_INLINE': 'org.eclipse.elk.edgeLabels.inline',
    'EDGE_LABELS_PLACEMENT': 'org.eclipse.elk.edgeLabels.placement',
    'EDGE_LABELS_SIDE_SELECTION': 'org.eclipse.elk.layered.edgeLabels.sideSelection',
    'EDGE_ROUTING': 'org.eclipse.elk.edgeRouting',
    'EDGE_ROUTING_POLYLINE_SLOPED_EDGE_ZONE_WIDTH': 'org.eclipse.elk.layered.edgeRouting.polyline.slopedEdgeZoneWidth',
    'EDGE_ROUTING_SELF_LOOP_DISTRIBUTION': 'org.eclipse.elk.layered.edgeRouting.selfLoopDistribution',
    'EDGE_ROUTING_SELF_LOOP_ORDERING': 'org.eclipse.elk.layered.edgeRouting.selfLoopOrdering',
    'EDGE_ROUTING_SPLINES_MODE': 'org.eclipse.elk.layered.edgeRouting.splines.mode',
    'EDGE_ROUTING_SPLINES_SLOPPY_LAYER_SPACING_FACTOR': 'org.eclipse.elk.layered.edgeRouting.splines.sloppy.layerSpacingFactor',
    'EDGE_THICKNESS': 'org.eclipse.elk.edge.thickness',
    'END_LABELS': 'endLabels',
    'END_LABEL_EDGE': 'endLabel.origin',
    'EXPAND_NODES': 'org.eclipse.elk.expandNodes',
    'EXT_PORT_CONNECTIONS': 'externalPortConnections',
    'EXT_PORT_REPLACED_DUMMIES': 'externalPortReplacedDummies',
    'EXT_PORT_REPLACED_DUMMY': 'externalPortReplacedDummy',
    'EXT_PORT_SIDE': 'externalPortSide',
    'EXT_PORT_SIZE': 'externalPortSize',
    'FEEDBACK_EDGES': 'org.eclipse.elk.layered.feedbackEdges',
    'FIRST_TRY_WITH_INITIAL_ORDER': 'firstTryWithInitialOrder',
    'GENERATE_POSITION_AND_LAYER_IDS': 'org.eclipse.elk.layered.generatePositionAndLayerIds',
    'GRAPH_PROPERTIES': 'graphProperties',
    'HIDDEN_NODES': 'layerConstraints.hiddenNodes',
    'HIERARCHY_HANDLING': 'org.eclipse.elk.hierarchyHandling',
    'HIGH_DEGREE_NODES_THRESHOLD': 'org.eclipse.elk.layered.highDegreeNodes.threshold',
    'HIGH_DEGREE_NODES_TREATMENT': 'org.eclipse.elk.layered.highDegreeNodes.treatment',
    'HIGH_DEGREE_NODES_TREE_HEIGHT': 'org.eclipse.elk.layered.highDegreeNodes.treeHeight',
    'HYPERNODE': 'org.eclipse.elk.hypernode',
    'INPUT_COLLECT': 'inputCollect',
    'INSIDE_CONNECTIONS': 'insideConnections',
    'INSIDE_SELF_LOOPS_ACTIVATE': 'org.eclipse.elk.insideSelfLoops.activate',
    'INSIDE_SELF_LOOPS_YO': 'org.eclipse.elk.insideSelfLoops.yo',
    'INTERACTIVE': 'org.eclipse.elk.interactive',
    'INTERACTIVE_LAYOUT': 'org.eclipse.elk.interactiveLayout',
    'INTERACTIVE_REFERENCE_POINT': 'org.eclipse.elk.layered.interactiveReferencePoint',
    'IN_LAYER_CONSTRAINT': 'inLayerConstraint',
    'IN_LAYER_LAYOUT_UNIT': 'inLayerLayoutUnit',
    'IN_LAYER_SUCCESSOR_CONSTRAINTS': 'inLayerSuccessorConstraint',
    'IN_LAYER_SUCCESSOR_CONSTRAINTS_BETWEEN_NON_DUMMIES': 'inLayerSuccessorConstraintBetweenNonDummies',
    'IS_PART_OF_CYCLE': 'partOfCycle',
    'JSON_EDGE_COORDS': 'org.eclipse.elk.json.edgeCoords',
    'JSON_SHAPE_COORDS': 'org.eclipse.elk.json.shapeCoords',
    'JUNCTION_POINTS': 'org.eclipse.elk.junctionPoints',
    'LABEL_SIDE': 'labelSide',
    'LAYERING_COFFMAN_GRAHAM_LAYER_BOUND': 'org.eclipse.elk.layered.layering.coffmanGraham.layerBound',
    'LAYERING_LAYER_CHOICE_CONSTRAINT': 'org.eclipse.elk.layered.layering.layerChoiceConstraint',
    'LAYERING_LAYER_CONSTRAINT': 'org.eclipse.elk.layered.layering.layerConstraint',
    'LAYERING_LAYER_ID': 'org.eclipse.elk.layered.layering.layerId',
    'LAYERING_MIN_WIDTH_UPPER_BOUND_ON_WIDTH': 'org.eclipse.elk.layered.layering.minWidth.upperBoundOnWidth',
    'LAYERING_MIN_WIDTH_UPPER_LAYER_ESTIMATION_SCALING_FACTOR': 'org.eclipse.elk.layered.layering.minWidth.upperLayerEstimationScalingFactor',
    'LAYERING_NODE_PROMOTION_MAX_ITERATIONS': 'org.eclipse.elk.layered.layering.nodePromotion.maxIterations',
    'LAYERING_NODE_PROMOTION_STRATEGY': 'org.eclipse.elk.layered.layering.nodePromotion.strategy',
    'LAYERING_STRATEGY': 'org.eclipse.elk.layered.layering.strategy',
    'LAYER_CONSTRAINT': 'org.eclipse.elk.layered.layering.layerConstraint',
    'LAYER_UNZIPPING_LAYER_SPLIT': 'org.eclipse.elk.layered.layerUnzipping.layerSplit',
    'LAYER_UNZIPPING_MINIMIZE_EDGE_LENGTH': 'org.eclipse.elk.layered.layerUnzipping.minimizeEdgeLength',
    'LAYER_UNZIPPING_RESET_ON_LONG_EDGES': 'org.eclipse.elk.layered.layerUnzipping.resetOnLongEdges',
    'LAYER_UNZIPPING_STRATEGY': 'org.eclipse.elk.layered.layerUnzipping.strategy',
    'LONG_EDGE_BEFORE_LABEL_DUMMY': 'longEdgeBeforeLabelDummy',
    'LONG_EDGE_HAS_LABEL_DUMMIES': 'longEdgeHasLabelDummies',
    'LONG_EDGE_SOURCE': 'longEdgeSource',
    'LONG_EDGE_TARGET': 'longEdgeTarget',
    'LONG_EDGE_TARGET_NODE': 'longEdgeTargetNode',
    'MARGINS': 'org.eclipse.elk.margins',
    'MAX_EDGE_THICKNESS': 'maxEdgeThickness',
    'MAX_MODEL_ORDER_NODES': 'modelOrder.maximum',
    'MERGE_EDGES': 'org.eclipse.elk.layered.mergeEdges',
    'MERGE_HIERARCHY_EDGES': 'org.eclipse.elk.layered.mergeHierarchyEdges',
    'MODEL_ORDER': 'modelOrder',
    'NODE_LABELS_PADDING': 'org.eclipse.elk.nodeLabels.padding',
    'NODE_LABELS_PLACEMENT': 'org.eclipse.elk.nodeLabels.placement',
    'NODE_PLACEMENT_BK_EDGE_STRAIGHTENING': 'org.eclipse.elk.layered.nodePlacement.bk.edgeStraightening',
    'NODE_PLACEMENT_BK_FIXED_ALIGNMENT': 'org.eclipse.elk.layered.nodePlacement.bk.fixedAlignment',
    'NODE_PLACEMENT_FAVOR_STRAIGHT_EDGES': 'org.eclipse.elk.layered.nodePlacement.favorStraightEdges',
    'NODE_PLACEMENT_LINEAR_SEGMENTS_DEFLECTION_DAMPENING': 'org.eclipse.elk.layered.nodePlacement.linearSegments.deflectionDampening',
    'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY': 'org.eclipse.elk.layered.nodePlacement.networkSimplex.nodeFlexibility',
    'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY_DEFAULT': 'org.eclipse.elk.layered.nodePlacement.networkSimplex.nodeFlexibility.default',
    'NODE_PLACEMENT_NETWORK_SIMPLEX_NODE_FLEXIBILITY_RECOMPUTE_NODE_PLACEMENT': 'org.eclipse.elk.layered.nodePlacement.networkSimplex.nodeFlexibility.recomputeNodePlacement',
    'NODE_PLACEMENT_STRATEGY': 'org.eclipse.elk.layered.nodePlacement.strategy',
    'NODE_SIZE_CONSTRAINTS': 'org.eclipse.elk.nodeSize.constraints',
    'NODE_SIZE_FIXED_GRAPH_SIZE': 'org.eclipse.elk.nodeSize.fixedGraphSize',
    'NODE_SIZE_MINIMUM': 'org.eclipse.elk.nodeSize.minimum',
    'NODE_SIZE_OPTIONS': 'org.eclipse.elk.nodeSize.options',
    'NO_LAYOUT': 'org.eclipse.elk.noLayout',
    'OMIT_NODE_MICRO_LAYOUT': 'org.eclipse.elk.omitNodeMicroLayout',
    'ORIGIN': 'origin',
    'ORIGINAL_BENDPOINTS': 'originalBendpoints',
    'ORIGINAL_DUMMY_NODE_POSITION': 'originalDummyNodePosition',
    'ORIGINAL_LABEL_EDGE': 'originalLabelEdge',
    'ORIGINAL_OPPOSITE_PORT': 'layerConstraints.opposidePort',
    'ORIGINAL_PORT_CONSTRAINTS': 'originalPortConstraints',
    'OUTPUT_COLLECT': 'outputCollect',
    'PADDING': 'org.eclipse.elk.padding',
    'PARTITIONING_ACTIVATE': 'org.eclipse.elk.partitioning.activate',
    'PARTITIONING_PARTITION': 'org.eclipse.elk.partitioning.partition',
    'PARTITION_DUMMY': 'partitionConstraint',
    'PORT_ALIGNMENT_DEFAULT': 'org.eclipse.elk.portAlignment.default',
    'PORT_ALIGNMENT_EAST': 'org.eclipse.elk.portAlignment.east',
    'PORT_ALIGNMENT_NORTH': 'org.eclipse.elk.portAlignment.north',
    'PORT_ALIGNMENT_SOUTH': 'org.eclipse.elk.portAlignment.south',
    'PORT_ALIGNMENT_WEST': 'org.eclipse.elk.portAlignment.west',
    'PORT_ANCHOR': 'org.eclipse.elk.port.anchor',
    'PORT_BORDER_OFFSET': 'org.eclipse.elk.port.borderOffset',
    'PORT_CONSTRAINTS': 'org.eclipse.elk.portConstraints',
    'PORT_DUMMY': 'portDummy',
    'PORT_INDEX': 'org.eclipse.elk.port.index',
    'PORT_LABELS_NEXT_TO_PORT_IF_POSSIBLE': 'org.eclipse.elk.portLabels.nextToPortIfPossible',
    'PORT_LABELS_PLACEMENT': 'org.eclipse.elk.portLabels.placement',
    'PORT_LABELS_TREAT_AS_GROUP': 'org.eclipse.elk.portLabels.treatAsGroup',
    'PORT_RATIO_OR_POSITION': 'portRatioOrPosition',
    'PORT_SIDE': 'org.eclipse.elk.port.side',
    'PORT_SORTING_STRATEGY': 'org.eclipse.elk.layered.portSortingStrategy',
    'POSITION': 'org.eclipse.elk.position',
    'PRIORITY': 'org.eclipse.elk.priority',
    'PRIORITY_DIRECTION': 'org.eclipse.elk.layered.priority.direction',
    'PRIORITY_SHORTNESS': 'org.eclipse.elk.layered.priority.shortness',
    'PRIORITY_STRAIGHTNESS': 'org.eclipse.elk.layered.priority.straightness',
    'PROCESSORS': 'processors',
    'RANDOM': 'random',
    'RANDOM_SEED': 'org.eclipse.elk.randomSeed',
    'REPRESENTED_LABELS': 'representedLabels',
    'RESOLVED_ALGORITHM': 'org.eclipse.elk.resolvedAlgorithm',
    'REVERSED': 'reversed',
    'SCALE_FACTOR': 'org.eclipse.elk.scaleFactor',
    'SECOND_TRY_WITH_INITIAL_ORDER': 'firstTryWithInitialOrder',
    'SELF_LOOP_HOLDER': 'selfLoopHolder',
    'SEPARATE_CONNECTED_COMPONENTS': 'org.eclipse.elk.separateConnectedComponents',
    'SPACINGS': 'spacings',
    'SPACING_BASE_VALUE': 'org.eclipse.elk.layered.spacing.baseValue',
    'SPACING_COMMENT_COMMENT': 'org.eclipse.elk.spacing.commentComment',
    'SPACING_COMMENT_NODE': 'org.eclipse.elk.spacing.commentNode',
    'SPACING_COMPONENT_COMPONENT': 'org.eclipse.elk.spacing.componentComponent',
    'SPACING_EDGE_EDGE': 'org.eclipse.elk.spacing.edgeEdge',
    'SPACING_EDGE_EDGE_BETWEEN_LAYERS': 'org.eclipse.elk.layered.spacing.edgeEdgeBetweenLayers',
    'SPACING_EDGE_LABEL': 'org.eclipse.elk.spacing.edgeLabel',
    'SPACING_EDGE_NODE': 'org.eclipse.elk.spacing.edgeNode',
    'SPACING_EDGE_NODE_BETWEEN_LAYERS': 'org.eclipse.elk.layered.spacing.edgeNodeBetweenLayers',
    'SPACING_INDIVIDUAL': 'org.eclipse.elk.spacing.individual',
    'SPACING_LABEL_LABEL': 'org.eclipse.elk.spacing.labelLabel',
    'SPACING_LABEL_NODE': 'org.eclipse.elk.spacing.labelNode',
    'SPACING_LABEL_PORT_HORIZONTAL': 'org.eclipse.elk.spacing.labelPortHorizontal',
    'SPACING_LABEL_PORT_VERTICAL': 'org.eclipse.elk.spacing.labelPortVertical',
    'SPACING_NODE_NODE': 'org.eclipse.elk.spacing.nodeNode',
    'SPACING_NODE_NODE_BETWEEN_LAYERS': 'org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers',
    'SPACING_NODE_SELF_LOOP': 'org.eclipse.elk.spacing.nodeSelfLoop',
    'SPACING_PORTS_SURROUNDING': 'org.eclipse.elk.spacing.portsSurrounding',
    'SPACING_PORT_PORT': 'org.eclipse.elk.spacing.portPort',
    'SPLINE_EDGE_CHAIN': 'splines.edgeChain',
    'SPLINE_NS_PORT_Y_COORD': 'splines.nsPortY',
    'SPLINE_ROUTE_START': 'splines.route.start',
    'SPLINE_SURVIVING_EDGE': 'splines.survivingEdge',
    'TARGET_NODE_MODEL_ORDER': 'targetNode.modelOrder',
    'TARGET_OFFSET': 'targetOffset',
    'TARJAN_ID': 'tarjan.id',
    'TARJAN_LOWLINK': 'tarjan.lowlink',
    'TARJAN_ON_STACK': 'tarjan.onstack',
    'THICKNESS': 'org.eclipse.elk.edge.thickness',
    'THOROUGHNESS': 'org.eclipse.elk.layered.thoroughness',
    'TOPDOWN_HIERARCHICAL_NODE_ASPECT_RATIO': 'org.eclipse.elk.topdown.hierarchicalNodeAspectRatio',
    'TOPDOWN_HIERARCHICAL_NODE_WIDTH': 'org.eclipse.elk.topdown.hierarchicalNodeWidth',
    'TOPDOWN_LAYOUT': 'org.eclipse.elk.topdownLayout',
    'TOPDOWN_NODE_TYPE': 'org.eclipse.elk.topdown.nodeType',
    'TOPDOWN_SCALE_CAP': 'org.eclipse.elk.topdown.scaleCap',
    'TOPDOWN_SCALE_FACTOR': 'org.eclipse.elk.topdown.scaleFactor',
    'TOPDOWN_SIZE_APPROXIMATOR': 'org.eclipse.elk.topdown.sizeApproximator',
    'TOPDOWN_SIZE_CATEGORIES': 'org.eclipse.elk.topdown.sizeCategories',
    'TOPDOWN_SIZE_CATEGORIES_HIERARCHICAL_NODE_WEIGHT': 'org.eclipse.elk.topdown.sizeCategoriesHierarchicalNodeWeight',
    'TOP_COMMENTS': 'TopSideComments',
    'UNNECESSARY_BENDPOINTS': 'org.eclipse.elk.layered.unnecessaryBendpoints',
    'WEIGHT': 'medianHeuristic.weight',
    'WRAPPING_ADDITIONAL_EDGE_SPACING': 'org.eclipse.elk.layered.wrapping.additionalEdgeSpacing',
    'WRAPPING_CORRECTION_FACTOR': 'org.eclipse.elk.layered.wrapping.correctionFactor',
    'WRAPPING_CUTTING_CUTS': 'org.eclipse.elk.layered.wrapping.cutting.cuts',
    'WRAPPING_CUTTING_MSD_FREEDOM': 'org.eclipse.elk.layered.wrapping.cutting.msd.freedom',
    'WRAPPING_CUTTING_STRATEGY': 'org.eclipse.elk.layered.wrapping.cutting.strategy',
    'WRAPPING_MULTI_EDGE_DISTANCE_PENALTY': 'org.eclipse.elk.layered.wrapping.multiEdge.distancePenalty',
    'WRAPPING_MULTI_EDGE_IMPROVE_CUTS': 'org.eclipse.elk.layered.wrapping.multiEdge.improveCuts',
    'WRAPPING_MULTI_EDGE_IMPROVE_WRAPPED_EDGES': 'org.eclipse.elk.layered.wrapping.multiEdge.improveWrappedEdges',
    'WRAPPING_STRATEGY': 'org.eclipse.elk.layered.wrapping.strategy',
    'WRAPPING_VALIDIFY_FORBIDDEN_INDICES': 'org.eclipse.elk.layered.wrapping.validify.forbiddenIndices',
    'WRAPPING_VALIDIFY_STRATEGY': 'org.eclipse.elk.layered.wrapping.validify.strategy',
}

_SHORT_PUBLIC_IDS = {actual[len('org.eclipse.elk.'):]: actual
                     for actual in (*_ALIAS_IDS.values(), *KNOWN_OPTION_IDS)
                     if actual.startswith('org.eclipse.elk.')}
_ABSENT = object()


def canonical_property_key(key):
    if not isinstance(key, str):
        raise TypeError('A source Property id or explicit native alias is required')
    return _ALIAS_IDS.get(key, _SHORT_PUBLIC_IDS.get(key, key))


class _IntegerIdentities(MutableMapping):
    def __init__(self, properties):
        self.properties = properties
        self._values = {}

    def __getitem__(self, key):
        return self._values[canonical_property_key(key)]

    def __setitem__(self, key, token):
        key = canonical_property_key(key)
        value = self.properties._values.get(key, _ABSENT)
        if (not isinstance(token, IntegerBoxToken) or type(token.value) is not int or type(value) is not int
                or value != token.value):
            raise TypeError('Integer identity must describe the actual stored Integer value')
        self._values[key] = token

    def __delitem__(self, key):
        del self._values[canonical_property_key(key)]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)


class CanonicalPropertyMap(MutableMapping):
    def __init__(self, source=None, integer_boxes=None):
        self._values = {}
        self.integer_boxes = _IntegerIdentities(self)
        if source is not None:
            self.update(source)
        if integer_boxes is not None:
            self.integer_boxes.update(integer_boxes)

    def __getitem__(self, key):
        return self._values[canonical_property_key(key)]

    def __setitem__(self, key, value):
        key = canonical_property_key(key)
        self.integer_boxes._values.pop(key, None)
        if value is None:
            self._values.pop(key, None)
        else:
            self._values[key] = value

    def __delitem__(self, key):
        key = canonical_property_key(key)
        del self._values[key]
        self.integer_boxes._values.pop(key, None)

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def set_property(self, key, value, *, integer_box=_ABSENT):
        self[key] = value
        if value is not None and integer_box is not _ABSENT:
            self.integer_boxes[key] = integer_box
        return self

    def update(self, source=(), **kwargs):
        # Explicit shallow source-copy retains Integer identity; ordinary new
        # assignments do not inherit an old token just because numbers match.
        tokens = dict(source.integer_boxes) if isinstance(source, CanonicalPropertyMap) else None
        pairs = source.items() if isinstance(source, Mapping) else source
        for key, value in pairs:
            self[key] = value
        if tokens is not None:
            self.integer_boxes.update(tokens)
        for key, value in kwargs.items():
            self[key] = value

    def clear(self):
        self._values.clear()
        self.integer_boxes._values.clear()

    def copy(self):
        return CanonicalPropertyMap(self)


def bind_native_properties(holder, snapshot):
    """Copy only present Snapshot keys, with the same values and box tokens."""
    properties = CanonicalPropertyMap(snapshot.values, snapshot.integer_boxes)
    holder.properties = properties
    holder.integer_box_identities = properties.integer_boxes
    return properties
