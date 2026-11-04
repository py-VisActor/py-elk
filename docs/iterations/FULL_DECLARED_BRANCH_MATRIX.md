# Layered 声明分支证据矩阵

首版固定 90 个工厂：59 个中间处理器、P1/P2 各 9、P3 4、P4 5、P5 4。P5 的 UNDEFINED 与 ORTHOGONAL 共用同一数学实现。

本次仅离线读取既存记录；没有运行布局、Source 或旧测试。任务名称必须同时出现在原版与候选的同一日志上下文：平面流程结合对应工厂类，层级流程只接受全局唯一任务名；共享任务按真实配置槽顺序绑定不同事件。配置槽、输入提及和类存在各自不能证明运行分支。

## 核心计数

| 状态 | 行数 |
|---|---:|
| witnessed_scoped | 79 |
| no_runtime_witness | 9 |
| body_witnessed_factory_alias_unresolved | 2 |

## 核心逐行

| 工厂 | 状态 | 真任务见证数 | 首个案例 | 实现 |
|---|---|---:|---|---|
| CrossingMinimizationStrategy.INTERACTIVE | witnessed_scoped | 1 | crossing-interactive | interactive_order.py:80 |
| CrossingMinimizationStrategy.LAYER_SWEEP | witnessed_scoped | 60 | direction-right | layer_sweep.py:34 |
| CrossingMinimizationStrategy.MEDIAN_LAYER_SWEEP | witnessed_scoped | 1 | crossing-median-layer-sweep | layer_sweep.py:34 |
| CrossingMinimizationStrategy.NONE | witnessed_scoped | 1 | crossing-none | interactive_order.py:130 |
| CycleBreakingStrategy.BFS_NODE_ORDER | witnessed_scoped | 1 | logged-bfs_node_order--network_simplex | cycles_general.py:398 |
| CycleBreakingStrategy.DEPTH_FIRST | witnessed_scoped | 0 | factory:CycleBreakingStrategy:DEPTH_FIRST:historical-object | cycles_general.py:77 |
| CycleBreakingStrategy.DFS_NODE_ORDER | witnessed_scoped | 1 | logged-dfs_node_order--network_simplex | cycles_general.py:438 |
| CycleBreakingStrategy.GREEDY | witnessed_scoped | 60 | direction-right | cycles_general.py:231 |
| CycleBreakingStrategy.GREEDY_MODEL_ORDER | no_runtime_witness | 0 | — | cycles_general.py:302 |
| CycleBreakingStrategy.INTERACTIVE | no_runtime_witness | 0 | — | cycles_general.py:317 |
| CycleBreakingStrategy.MODEL_ORDER | witnessed_scoped | 1 | logged-model_order--stretch_width | cycles_general.py:352 |
| CycleBreakingStrategy.SCC_CONNECTIVITY | witnessed_scoped | 1 | logged-scc_connectivity--bf_model_order | cycles_general.py:581 |
| CycleBreakingStrategy.SCC_NODE_TYPE | witnessed_scoped | 1 | logged-scc_node_type--df_model_order | cycles_general.py:596 |
| EdgeRouting.ORTHOGONAL | body_witnessed_factory_alias_unresolved | 59 | direction-right | orthogonal_general.py:692 |
| EdgeRouting.POLYLINE | witnessed_scoped | 1 | polyline-ports | polyline_general.py:60 |
| EdgeRouting.SPLINES | witnessed_scoped | 0 | historical-spline-p5-to-final | spline_general.py:272 |
| EdgeRouting.UNDEFINED | body_witnessed_factory_alias_unresolved | 59 | direction-right | orthogonal_general.py:692 |
| IntermediateProcessorStrategy.ALTERNATING_LAYER_UNZIPPER | no_runtime_witness | 0 | — | wrapping.py:118 |
| IntermediateProcessorStrategy.BREAKING_POINT_INSERTER | witnessed_scoped | 2 | wrapping-multi-edge-ard | breaking_points.py:186 |
| IntermediateProcessorStrategy.BREAKING_POINT_PROCESSOR | witnessed_scoped | 2 | wrapping-multi-edge-ard | breaking_points.py:305 |
| IntermediateProcessorStrategy.BREAKING_POINT_REMOVER | witnessed_scoped | 2 | wrapping-multi-edge-ard | breaking_points.py:346 |
| IntermediateProcessorStrategy.CENTER_LABEL_MANAGEMENT_PROCESSOR | no_runtime_witness | 0 | — | label_management_general.py:9 |
| IntermediateProcessorStrategy.COMMENT_NODE_MARGIN_CALCULATOR | witnessed_scoped | 1 | comments-context | comments_general.py:60 |
| IntermediateProcessorStrategy.COMMENT_POSTPROCESSOR | witnessed_scoped | 1 | comments-context | comments_general.py:133 |
| IntermediateProcessorStrategy.COMMENT_PREPROCESSOR | witnessed_scoped | 1 | comments-context | comments_general.py:241 |
| IntermediateProcessorStrategy.CONSTRAINTS_POSTPROCESSOR | witnessed_scoped | 1 | position-layer-identifiers | utility_processors.py:30 |
| IntermediateProcessorStrategy.DIRECTION_POSTPROCESSOR | witnessed_scoped | 4 | direction-left | directions_general.py:197 |
| IntermediateProcessorStrategy.DIRECTION_PREPROCESSOR | witnessed_scoped | 4 | direction-left | directions_general.py:197 |
| IntermediateProcessorStrategy.EDGE_AND_LAYER_CONSTRAINT_EDGE_REVERSER | witnessed_scoped | 63 | direction-right | constraint_processors.py:105 |
| IntermediateProcessorStrategy.END_LABEL_POSTPROCESSOR | witnessed_scoped | 2 | compound-cross-labels-down | end_label_placement.py:8 |
| IntermediateProcessorStrategy.END_LABEL_PREPROCESSOR | witnessed_scoped | 2 | compound-cross-labels-down | end_label_placement.py:180 |
| IntermediateProcessorStrategy.END_LABEL_SORTER | witnessed_scoped | 63 | direction-right | end_labels_general.py:90 |
| IntermediateProcessorStrategy.END_NODE_PORT_LABEL_MANAGEMENT_PROCESSOR | no_runtime_witness | 0 | — | label_management_general.py:9 |
| IntermediateProcessorStrategy.FINAL_SPLINE_BENDPOINTS_CALCULATOR | witnessed_scoped | 0 | historical-spline-p5-to-final | spline_final.py:160 |
| IntermediateProcessorStrategy.HIERARCHICAL_NODE_RESIZER | witnessed_scoped | 3 | compound-cross-hierarchy | hierarchical_resize.py:89 |
| IntermediateProcessorStrategy.HIERARCHICAL_PORT_CONSTRAINT_PROCESSOR | witnessed_scoped | 3 | compound-cross-hierarchy | hierarchical_port_constraints.py:158 |
| IntermediateProcessorStrategy.HIERARCHICAL_PORT_DUMMY_SIZE_PROCESSOR | witnessed_scoped | 3 | compound-cross-hierarchy | hierarchical_port_size.py:23 |
| IntermediateProcessorStrategy.HIERARCHICAL_PORT_ORTHOGONAL_EDGE_ROUTER | witnessed_scoped | 3 | compound-cross-hierarchy | hierarchical_port_ortho.py:258 |
| IntermediateProcessorStrategy.HIERARCHICAL_PORT_POSITION_PROCESSOR | witnessed_scoped | 3 | compound-cross-hierarchy | hierarchical_port_position.py:38 |
| IntermediateProcessorStrategy.HIGH_DEGREE_NODE_LAYER_PROCESSOR | no_runtime_witness | 0 | — | high_degree.py:30 |
| IntermediateProcessorStrategy.HORIZONTAL_COMPACTOR | witnessed_scoped | 6 | compact-left | horizontal_graph_compactor.py:586 |
| IntermediateProcessorStrategy.HYPEREDGE_DUMMY_MERGER | witnessed_scoped | 1 | hypernode-collector | hyperedge_merger.py:77 |
| IntermediateProcessorStrategy.HYPERNODE_PROCESSOR | witnessed_scoped | 1 | hypernode-collector | hypernodes.py:79 |
| IntermediateProcessorStrategy.INNERMOST_NODE_MARGIN_CALCULATOR | witnessed_scoped | 60 | direction-right | native_adapters.py:463 |
| IntermediateProcessorStrategy.INTERACTIVE_EXTERNAL_PORT_POSITIONER | no_runtime_witness | 0 | — | utility_processors.py:84 |
| IntermediateProcessorStrategy.INVERTED_PORT_PROCESSOR | witnessed_scoped | 10 | ports-fixed-side | inverted_ports_general.py:84 |
| IntermediateProcessorStrategy.IN_LAYER_CONSTRAINT_PROCESSOR | witnessed_scoped | 63 | direction-right | simple_processors.py:13 |
| IntermediateProcessorStrategy.LABEL_AND_NODE_SIZE_PROCESSOR | witnessed_scoped | 63 | direction-right | native_adapters.py:448 |
| IntermediateProcessorStrategy.LABEL_DUMMY_INSERTER | witnessed_scoped | 7 | compound-cross-labels-down | center_label_dummies.py:50 |
| IntermediateProcessorStrategy.LABEL_DUMMY_REMOVER | witnessed_scoped | 7 | compound-cross-labels-down | center_label_dummies.py:113 |
| IntermediateProcessorStrategy.LABEL_DUMMY_SWITCHER | witnessed_scoped | 7 | compound-cross-labels-down | center_label_switcher.py:106 |
| IntermediateProcessorStrategy.LABEL_SIDE_SELECTOR | witnessed_scoped | 8 | compound-cross-labels-down | label_side_selector.py:217 |
| IntermediateProcessorStrategy.LAYER_CONSTRAINT_POSTPROCESSOR | witnessed_scoped | 63 | direction-right | constraint_processors.py:299 |
| IntermediateProcessorStrategy.LAYER_CONSTRAINT_PREPROCESSOR | witnessed_scoped | 63 | direction-right | constraint_processors.py:216 |
| IntermediateProcessorStrategy.LAYER_SIZE_AND_GRAPH_HEIGHT_CALCULATOR | witnessed_scoped | 63 | direction-right | simple_processors.py:49 |
| IntermediateProcessorStrategy.LONG_EDGE_JOINER | witnessed_scoped | 63 | direction-right | long_edges_general.py:163 |
| IntermediateProcessorStrategy.LONG_EDGE_SPLITTER | witnessed_scoped | 63 | direction-right | long_edges_general.py:106 |
| IntermediateProcessorStrategy.NODE_PLACEMENT_REPEATER | witnessed_scoped | 1 | flexibility-recompute | utility_processors.py:49 |
| IntermediateProcessorStrategy.NODE_PROMOTION | witnessed_scoped | 9 | promotion-nikolov | node_promotion.py:14 |
| IntermediateProcessorStrategy.NORTH_SOUTH_PORT_POSTPROCESSOR | witnessed_scoped | 4 | ports-fixed-side | north_south_ports.py:233 |
| IntermediateProcessorStrategy.NORTH_SOUTH_PORT_PREPROCESSOR | witnessed_scoped | 4 | ports-fixed-side | north_south_ports.py:156 |
| IntermediateProcessorStrategy.ONE_SIDED_GREEDY_SWITCH | witnessed_scoped | 0 | historical-greedy-one-phase | layer_sweep.py:34 |
| IntermediateProcessorStrategy.PARTITION_MIDPROCESSOR | witnessed_scoped | 1 | partition-reversal | partition_processors.py:85 |
| IntermediateProcessorStrategy.PARTITION_POSTPROCESSOR | witnessed_scoped | 1 | partition-reversal | partition_processors.py:105 |
| IntermediateProcessorStrategy.PARTITION_PREPROCESSOR | witnessed_scoped | 1 | partition-reversal | partition_processors.py:46 |
| IntermediateProcessorStrategy.PORT_LIST_SORTER | witnessed_scoped | 62 | direction-right | processors.py:151 |
| IntermediateProcessorStrategy.PORT_SIDE_PROCESSOR | witnessed_scoped | 63 | direction-right | processors.py:144 |
| IntermediateProcessorStrategy.REVERSED_EDGE_RESTORER | witnessed_scoped | 63 | direction-right | reversed_edges_general.py:9 |
| IntermediateProcessorStrategy.SELF_LOOP_PORT_RESTORER | witnessed_scoped | 3 | loops-north | self_loops_general.py:499 |
| IntermediateProcessorStrategy.SELF_LOOP_POSTPROCESSOR | witnessed_scoped | 3 | loops-north | self_loops_general.py:230 |
| IntermediateProcessorStrategy.SELF_LOOP_PREPROCESSOR | witnessed_scoped | 3 | loops-north | self_loops_general.py:301 |
| IntermediateProcessorStrategy.SELF_LOOP_ROUTER | witnessed_scoped | 3 | loops-north | self_loops_general.py:889 |
| IntermediateProcessorStrategy.SEMI_INTERACTIVE_CROSSMIN_PROCESSOR | witnessed_scoped | 1 | semi-interactive-positions | semi_interactive.py:10 |
| IntermediateProcessorStrategy.SINGLE_EDGE_GRAPH_WRAPPER | witnessed_scoped | 1 | wrapping-single-edge-ard | wrapping.py:360 |
| IntermediateProcessorStrategy.SORT_BY_INPUT_ORDER_OF_MODEL | witnessed_scoped | 1 | model-order-forced | input_model_sort.py:62 |
| IntermediateProcessorStrategy.TWO_SIDED_GREEDY_SWITCH | witnessed_scoped | 58 | direction-right | layer_sweep.py:34 |
| LayeringStrategy.BF_MODEL_ORDER | witnessed_scoped | 1 | logged-scc_connectivity--bf_model_order | model_order_layering.py:50 |
| LayeringStrategy.COFFMAN_GRAHAM | witnessed_scoped | 0 | factory:LayeringStrategy:COFFMAN_GRAHAM:historical-object | coffman_graham_general.py:106 |
| LayeringStrategy.DF_MODEL_ORDER | witnessed_scoped | 1 | logged-scc_node_type--df_model_order | model_order_layering.py:85 |
| LayeringStrategy.INTERACTIVE | no_runtime_witness | 0 | — | interactive_layering.py:19 |
| LayeringStrategy.LONGEST_PATH | witnessed_scoped | 0 | factory:LayeringStrategy:LONGEST_PATH:historical-object | longest_path_general.py:96 |
| LayeringStrategy.LONGEST_PATH_SOURCE | witnessed_scoped | 0 | factory:LayeringStrategy:LONGEST_PATH_SOURCE:historical-object | longest_path_general.py:100 |
| LayeringStrategy.MIN_WIDTH | no_runtime_witness | 0 | — | width_layering.py:18 |
| LayeringStrategy.NETWORK_SIMPLEX | witnessed_scoped | 65 | direction-right | network_simplex_general.py:164 |
| LayeringStrategy.STRETCH_WIDTH | witnessed_scoped | 1 | logged-model_order--stretch_width | width_layering.py:94 |
| NodePlacementStrategy.BRANDES_KOEPF | witnessed_scoped | 58 | direction-right | brandes_koepf_general.py:318 |
| NodePlacementStrategy.INTERACTIVE | witnessed_scoped | 1 | placement-interactive | interactive_placement.py:24 |
| NodePlacementStrategy.LINEAR_SEGMENTS | witnessed_scoped | 1 | placement-linear-segments | linear_segments_placement.py:63 |
| NodePlacementStrategy.NETWORK_SIMPLEX | witnessed_scoped | 2 | placement-network-simplex | network_simplex_placement.py:156 |
| NodePlacementStrategy.SIMPLE | witnessed_scoped | 1 | placement-simple | simple_placement.py:24 |

## 解释与后续

未找到任务见证不等于未实现。本版扫描既有 72 例中的 66 个正常返回匹配结果，合入 4 个 P1/P2 实际 owner.process 对象见证、2 个 Spline→Final 准备图及 ONE_SIDED 真阶段状态；另合入新授权 7 个日志调用中的 5 个正常对，具名任务证明 8 个策略行。另两对 Source/native 同为 NPE，无结果树，不升级其中 4 个策略。历史执行保其原模块 SHA，不重绑当前模块。另 16 条 P1/P2 公开返回关联单列，不凭输入策略升级。

`body_witnessed_factory_alias_unresolved` 只证明共享正交路由体，不声称区分两个工厂别名。无任务名的 FinalSpline / HighDegree 需要已有对象或因果输出证据；不为它们补造日志。两个 LabelManagement 工厂的实际非空 raw-manager 选择受原版 cast 限制，需区分 API 可构造性与回调数学。

附加枚举层逐项保留有限分母：21 行已有真实因果几何或明确命名任务见证，其余仍未映射。不能用同一通用任务加输入提及替代内部分支证据；不要求数值无限取值或所有选项组合。JSON 保留完整路径、SHA、JSONPointer、静态锚及限制。

## 附加枚举有限缺项

| 选项 | 已证值 | 尚无本表见证的值 |
|---|---|---|
| org.eclipse.elk.direction |  | UNDEFINED, RIGHT, LEFT, DOWN, UP |
| org.eclipse.elk.portConstraints | FIXED_RATIO, FIXED_POS | UNDEFINED, FREE, FIXED_SIDE, FIXED_ORDER |
| org.eclipse.elk.port.side |  | UNDEFINED, NORTH, EAST, SOUTH, WEST |
| org.eclipse.elk.layered.directionCongruency |  | READING_DIRECTION, ROTATION |
| org.eclipse.elk.layered.interactiveReferencePoint |  | CENTER, TOP_LEFT |
| org.eclipse.elk.layered.portSortingStrategy |  | INPUT_ORDER, PORT_DEGREE |
| org.eclipse.elk.layered.layering.layerConstraint |  | NONE, FIRST, FIRST_SEPARATE, LAST, LAST_SEPARATE |
| org.eclipse.elk.layered.layering.nodePromotion.strategy |  | NONE, NIKOLOV, NIKOLOV_PIXEL, NIKOLOV_IMPROVED, NIKOLOV_IMPROVED_PIXEL, DUMMYNODE_PERCENTAGE, NODECOUNT_PERCENTAGE, NO_BOUNDARY, MODEL_ORDER_LEFT_TO_RIGHT, MODEL_ORDER_RIGHT_TO_LEFT |
| org.eclipse.elk.layered.crossingMinimization.greedySwitch.type | TWO_SIDED | ONE_SIDED, OFF |
| org.eclipse.elk.layered.crossingMinimization.greedySwitchHierarchical.type |  | ONE_SIDED, TWO_SIDED, OFF |
| org.eclipse.elk.layered.nodePlacement.bk.edgeStraightening | NONE, IMPROVE_STRAIGHTNESS |  |
| org.eclipse.elk.layered.nodePlacement.bk.fixedAlignment | LEFTUP, RIGHTDOWN | NONE, RIGHTUP, LEFTDOWN, BALANCED |
| org.eclipse.elk.layered.nodePlacement.networkSimplex.nodeFlexibility | NODE_SIZE | NONE, PORT_POSITION, NODE_SIZE_WHERE_SPACE_PERMITS |
| org.eclipse.elk.layered.nodePlacement.networkSimplex.nodeFlexibility.default | NONE, NODE_SIZE | PORT_POSITION, NODE_SIZE_WHERE_SPACE_PERMITS |
| org.eclipse.elk.layered.nodePlacement.networkSimplex.nodeFlexibility.recomputeNodePlacement | SIMPLE | INTERACTIVE, LINEAR_SEGMENTS, BRANDES_KOEPF, NETWORK_SIMPLEX |
| org.eclipse.elk.layered.edgeRouting.selfLoopDistribution |  | EQUALLY, NORTH, NORTH_SOUTH |
| org.eclipse.elk.layered.edgeRouting.selfLoopOrdering |  | STACKED, REVERSE_STACKED, SEQUENCED |
| org.eclipse.elk.layered.edgeRouting.splines.mode | CONSERVATIVE, SLOPPY | CONSERVATIVE_SOFT |
| org.eclipse.elk.layered.compaction.postCompaction.strategy | NONE, LEFT, EDGE_LENGTH | RIGHT, LEFT_RIGHT_CONSTRAINT_LOCKING, LEFT_RIGHT_CONNECTION_LOCKING |
| org.eclipse.elk.layered.compaction.postCompaction.constraints |  | QUADRATIC, SCANLINE |
| org.eclipse.elk.layered.wrapping.strategy |  | OFF, SINGLE_EDGE, MULTI_EDGE |
| org.eclipse.elk.layered.wrapping.cutting.strategy | ARD, MSD | MANUAL |
| org.eclipse.elk.layered.wrapping.validify.strategy |  | NO, GREEDY, LOOK_BACK |
| org.eclipse.elk.layered.layerUnzipping.strategy |  | NONE, ALTERNATING |
| org.eclipse.elk.layered.edgeLabels.sideSelection | SMART_UP, SMART_DOWN | ALWAYS_UP, ALWAYS_DOWN, DIRECTION_UP, DIRECTION_DOWN |
| org.eclipse.elk.layered.edgeLabels.centerLabelPlacementStrategy |  | MEDIAN_LAYER, TAIL_LAYER, HEAD_LAYER, SPACE_EFFICIENT_LAYER, WIDEST_LAYER, CENTER_LAYER |
| org.eclipse.elk.layered.considerModelOrder.strategy | NODES_AND_EDGES | NONE, PREFER_EDGES, PREFER_NODES |
| org.eclipse.elk.layered.considerModelOrder.components |  | NONE, INSIDE_PORT_SIDE_GROUPS, GROUP_MODEL_ORDER, MODEL_ORDER |
| org.eclipse.elk.layered.considerModelOrder.longEdgeStrategy |  | DUMMY_NODE_OVER, DUMMY_NODE_UNDER, EQUAL |
| org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cbGroupOrderStrategy |  | ONLY_WITHIN_GROUP, MODEL_ORDER, ENFORCED |
| org.eclipse.elk.layered.considerModelOrder.groupModelOrder.cmGroupOrderStrategy |  | ONLY_WITHIN_GROUP, MODEL_ORDER, ENFORCED |

## 核心尚无直接见证

| 工厂 | 明确分类 | 最小后续动作 |
|---|---|---|
| CycleBreakingStrategy.GREEDY_MODEL_ORDER | normal-unlogged-public-return-plus-logged-upstream-error | If a direct body witness is required, one actual owner.process state or function-entry observation is enough; do not replay the 81 strategy matrix. |
| CycleBreakingStrategy.INTERACTIVE | normal-unlogged-public-return-plus-logged-upstream-error | If a direct body witness is required, one actual owner.process state or function-entry observation is enough; do not replay the 81 strategy matrix. |
| IntermediateProcessorStrategy.ALTERNATING_LAYER_UNZIPPER | normal-unlogged-output-exists-body-not-isolated | Reuse saved Source output/effects first; only a direct body-state observation remains if those cannot isolate the consumer. |
| IntermediateProcessorStrategy.CENTER_LABEL_MANAGEMENT_PROCESSOR | upstream-nonnull-raw-manager-unavailable | Retain compiled Source null-only cast boundary; no successful nonnull raw callback can be manufactured. |
| IntermediateProcessorStrategy.END_NODE_PORT_LABEL_MANAGEMENT_PROCESSOR | upstream-nonnull-raw-manager-unavailable | Retain compiled Source null-only cast boundary; no successful nonnull raw callback can be manufactured. |
| IntermediateProcessorStrategy.HIGH_DEGREE_NODE_LAYER_PROCESSOR | normal-unlogged-output-exists-body-not-isolated | Reuse saved Source output/effects first; only a direct body-state observation remains if those cannot isolate the consumer. |
| IntermediateProcessorStrategy.INTERACTIVE_EXTERNAL_PORT_POSITIONER | no-current-direct-body-observation | One applicable actual object-state or public function-entry witness; no known missing implementation inferred. |
| LayeringStrategy.INTERACTIVE | normal-unlogged-public-return-plus-logged-upstream-error | If a direct body witness is required, one actual owner.process state or function-entry observation is enough; do not replay the 81 strategy matrix. |
| LayeringStrategy.MIN_WIDTH | normal-unlogged-public-return-plus-logged-upstream-error | If a direct body witness is required, one actual owner.process state or function-entry observation is enough; do not replay the 81 strategy matrix. |

## 干净检出复核

`python scripts/iteration/declared_branch_matrix.py --check` 仅读取版本化源码、请求和 `references/full-native-closure/branches.zip` 的精确成员；SHA 与清单逐个核对，不回退本机 ignored 路径。原始观察字节不改写。
