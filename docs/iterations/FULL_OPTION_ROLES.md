# 243 项选项的角色与有限见证映射

此表独立于冻结 option-coverage 账本。它映射有限的 243 个声明，不要求无限数值或组合；静态读取、默认值和输入出现不当作运行证明。

保留原账本：73 项限定几何、15 项限定状态，去重 82 项；其余 161 项没有登记运行消费见证。8 项 raw factory 不可构造与 typed/internal 合同分别列示。完整选项语义通过数仍为 0。

角色列是静态候选分类：只给已定位的 accessor 加真实函数/行号，字面量与声明另列 reference。实际已观察角色只来自冻结账本的具体断言。API 元数据注册不自动证明每项的消费或布局效果。

本次现仓库定位 174 个 ID 的显式属性 accessor，其中 169 个有读取消费者；写入/移除生产者另列。既存 Source 包定位 7 个 ID 的读取 accessor。未定位是扫描范围内的缺口，不能声称编译后未使用。

复核命令：`python scripts/iteration/option_roles.py --check`。工具只读 tracked 账本、元数据、Python AST 与既存 Source 字节；不导入产品、不运行布局、也不重放原版。可在 A 的分支矩阵冻结后用 `--build --branch-matrix docs/iterations/FULL_DECLARED_BRANCH_MATRIX.json` 接入交叉引用；分支配置不会提升几何效果。

## 逐项映射

| ID | 静态角色候选 | 已有断言角色 | 原生消费者锚 / 现有 Source 锚 | 有限见证状态 |
| --- | --- | --- | --- | --- |
| `algorithm` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/native_import_hierarchical.py:20` (HierarchicalElkGraphImporter._uses_layered) | 待最小状态/效果见证 |
| `resolvedAlgorithm` | api_metadata | runtime_state | `src/pyelk/execution/recursive.py:73` (RecursiveLayoutEngine._node) | 限定见证；raw factory 不可用 |
| `alignment` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/directions.py:110` (_nodes) | 待最小状态/效果见证 |
| `aspectRatio` | geometry | geometry, runtime_state | `src/pyelk/algorithms/box.py:341` (_layout)；Source `references/e19-packing-sources.json` worker:25929 | 限定见证 |
| `bendPoints` | geometry | runtime_state | `src/pyelk/algorithms/fixed.py:238` (_process_edge) | 限定见证 |
| `contentAlignment` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/resize_general.py:37` (resize_graph_no_really) | 待最小状态/效果见证 |
| `debugMode` | diagnostic | 无运行消费见证 | `src/pyelk/algorithms/mrtree.py:663` (pack_components)；Source `references/e17-tree-sources.json` worker:60548 | 待最小状态/效果见证 |
| `direction` | layout_strategy | geometry | `src/pyelk/algorithms/box.py:43` (_micro_resize) | 限定见证 |
| `edgeRouting` | layout_strategy | geometry | `src/pyelk/algorithms/fixed.py:326` (_layout) | 限定见证 |
| `expandNodes` | layout_strategy | geometry | `src/pyelk/algorithms/box.py:344` (_layout) | 限定见证 |
| `hierarchyHandling` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/crossing.py:61` (_guard) | 待最小状态/效果见证 |
| `padding` | geometry | geometry, runtime_state | `src/pyelk/algorithms/disco.py:689` (DisCoPolyominoCompactor.apply_to_graph) | 限定见证 |
| `interactive` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/box.py:332` (_layout) | 待最小状态/效果见证 |
| `interactiveLayout` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `omitNodeMicroLayout` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/force.py:526` (_layout) | 待最小状态/效果见证 |
| `portConstraints` | layout_strategy | geometry | `src/pyelk/algorithms/box.py:40` (_micro_resize) | 限定见证 |
| `position` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/directions.py:112` (_nodes) | 待最小状态/效果见证 |
| `priority` | geometry | runtime_state | `src/pyelk/algorithms/box.py:334` (_layout.compare) | 限定见证 |
| `randomSeed` | runtime_state | geometry | `src/pyelk/algorithms/force.py:533` (_layout) | 限定见证 |
| `separateConnectedComponents` | layout_strategy | geometry | `src/pyelk/algorithms/force.py:253` (split_components) | 限定见证 |
| `junctionPoints` | geometry | runtime_state | `src/pyelk/algorithms/box.py:69` (_translate) | 限定见证 |
| `commentBox` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/comments_general.py:19` (_is_comment) | 待最小状态/效果见证 |
| `hypernode` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/hypernodes.py:85` (hypernodes_processor) | 待最小状态/效果见证 |
| `labelManager` | callback | 无运行消费见证 | `src/pyelk/algorithms/layered/graph_configurator.py:90` (GraphConfigurator.phase_independent_configuration)；Source `references/e13-kernel-sources.json` worker:28414 | 待最小状态/效果见证；raw factory 不可用 |
| `softwrappingFuzziness` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `margins` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/utility_processors.py:112` (InteractiveExternalPortPositioner._north_south_x) | 待最小状态/效果见证 |
| `noLayout` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/model_order_import.py:54` (transform_ordered_ports) | 待最小状态/效果见证 |
| `scaleFactor` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive_helpers.py:80` (apply_configured_node_scaling) | 待最小状态/效果见证 |
| `childAreaWidth` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive.py:145` (RecursiveLayoutEngine._topdown) | 待最小状态/效果见证 |
| `childAreaHeight` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive.py:146` (RecursiveLayoutEngine._topdown) | 待最小状态/效果见证 |
| `topdownLayout` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive.py:83` (RecursiveLayoutEngine._node) | 待最小状态/效果见证 |
| `animate` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `animTimeFactor` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layoutAncestors` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `maxAnimTime` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `minAnimTime` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `progressBar` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `validateGraph` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `validateOptions` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `zoomToFit` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `box.packingMode` | layout_strategy | geometry | `src/pyelk/algorithms/box.py:331` (_layout) | 限定见证 |
| `json.shapeCoords` | runtime_state | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `json.edgeCoords` | runtime_state | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `spacing.commentComment` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `spacing.commentNode` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `spacing.componentComponent` | geometry | geometry | `src/pyelk/algorithms/disco.py:708` (_layout) | 限定见证 |
| `spacing.edgeEdge` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/hierarchical_port_ortho.py:302` (HierarchicalPortOrthogonalEdgeRouter.route_edges) | 待最小状态/效果见证 |
| `spacing.edgeLabel` | geometry | 无运行消费见证 | `src/pyelk/algorithms/force.py:127` (FLabel.refresh_position) | 待最小状态/效果见证 |
| `spacing.edgeNode` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/wrapping.py:140` (alternating_layer_unzipper) | 待最小状态/效果见证 |
| `spacing.labelLabel` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/center_label_dummies.py:56` (label_dummy_inserter) | 待最小状态/效果见证 |
| `spacing.labelNode` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/native_adapters.py:375` (NodeMarginCalculator.process) | 待最小状态/效果见证 |
| `spacing.labelPortHorizontal` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/hierarchical_port_ortho.py:177` (restore_dummy) | 待最小状态/效果见证 |
| `spacing.labelPortVertical` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/hierarchical_port_ortho.py:178` (restore_dummy) | 待最小状态/效果见证 |
| `spacing.nodeNode` | geometry | geometry | `src/pyelk/algorithms/box.py:343` (_layout) | 限定见证 |
| `spacing.nodeSelfLoop` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `spacing.portPort` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/hierarchical_port_ortho.py:68` (assign_ascending_coordinates) | 待最小状态/效果见证 |
| `spacing.individual` | geometry | runtime_state | `src/pyelk/algorithms/layered/network_simplex_placement.py:45` (_individual_surrounding) | 限定见证 |
| `spacing.portsSurrounding` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/network_simplex_placement.py:51` (_individual_surrounding) | 待最小状态/效果见证 |
| `partitioning.partition` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/partition_processors.py:18` (_partition) | 待最小状态/效果见证 |
| `partitioning.activate` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/native_import_full.py:46` (FullElkGraphImporter.import_graph) | 待最小状态/效果见证 |
| `nodeLabels.padding` | geometry | runtime_state | `src/pyelk/algorithms/layered/directions.py:55` (get_node_labels_padding) | 限定见证 |
| `nodeLabels.placement` | layout_strategy | geometry | `src/pyelk/algorithms/layered/directions.py:143` (_nodes) | 限定见证 |
| `portAlignment.default` | layout_strategy | geometry | `src/pyelk/algorithms/layered/node_size.py:51` (get_port_alignment) | 限定见证 |
| `portAlignment.north` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `portAlignment.south` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `portAlignment.west` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `portAlignment.east` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `nodeSize.constraints` | layout_strategy | geometry, runtime_state | `src/pyelk/algorithms/fixed.py:146` (_minimum) | 限定见证 |
| `nodeSize.options` | layout_strategy | geometry, runtime_state | `src/pyelk/algorithms/fixed.py:150` (_minimum) | 限定见证 |
| `nodeSize.minimum` | geometry | geometry, runtime_state | `src/pyelk/algorithms/box.py:317` (_place_grouped) | 限定见证 |
| `nodeSize.fixedGraphSize` | layout_strategy | geometry | `src/pyelk/algorithms/fixed.py:337` (_layout) | 限定见证 |
| `edgeLabels.placement` | layout_strategy | geometry | `src/pyelk/algorithms/layered/center_label_dummies.py:19` (_placement) | 限定见证 |
| `edgeLabels.inline` | layout_strategy | geometry | `src/pyelk/algorithms/force.py:123` (FLabel.refresh_position) | 限定见证 |
| `font.name` | api_metadata | runtime_state | 未定位原生 accessor | 限定见证 |
| `font.size` | api_metadata | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `port.anchor` | geometry | geometry | `src/pyelk/algorithms/layered/external_port_dummy.py:37` (create_external_port_dummy) | 限定见证 |
| `port.index` | geometry | geometry | `src/pyelk/algorithms/layered/directions.py:124` (_nodes) | 限定见证 |
| `port.side` | layout_strategy | geometry | `src/pyelk/algorithms/box.py:45` (_micro_resize) | 限定见证 |
| `port.borderOffset` | geometry | geometry, runtime_state | `src/pyelk/algorithms/layered/external_port_dummy.py:25` (create_external_port_dummy) | 限定见证 |
| `portLabels.placement` | layout_strategy | geometry | `src/pyelk/algorithms/layered/compound_pre.py:27` (_read) | 限定见证 |
| `portLabels.nextToPortIfPossible` | runtime_state | geometry | `src/pyelk/execution/deprecated.py:10` (replace_deprecated_options) | 限定见证 |
| `portLabels.treatAsGroup` | layout_strategy | geometry | `src/pyelk/algorithms/layered/native_adapters.py:455` (label_and_node_size_processor) | 限定见证 |
| `topdown.sizeCategories` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `topdown.sizeCategoriesHierarchicalNodeWeight` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `topdown.scaleFactor` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `topdown.sizeApproximator` | callback | 无运行消费见证 | `src/pyelk/execution/recursive.py:125` (RecursiveLayoutEngine._topdown) | 待最小状态/效果见证；raw factory 不可用 |
| `topdown.hierarchicalNodeWidth` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive.py:132` (RecursiveLayoutEngine._topdown) | 待最小状态/效果见证 |
| `topdown.hierarchicalNodeAspectRatio` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive.py:134` (RecursiveLayoutEngine._topdown) | 待最小状态/效果见证 |
| `topdown.nodeType` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive.py:114` (RecursiveLayoutEngine._topdown) | 待最小状态/效果见证 |
| `topdown.scaleCap` | runtime_state | 无运行消费见证 | `src/pyelk/execution/recursive.py:159` (RecursiveLayoutEngine._topdown) | 待最小状态/效果见证 |
| `insideSelfLoops.activate` | runtime_state | 无运行消费见证 | `src/pyelk/execution/inside_self_loops.py:53` (gather_inside_self_loops) | 待最小状态/效果见证 |
| `insideSelfLoops.yo` | runtime_state | 无运行消费见证 | `src/pyelk/execution/inside_self_loops.py:57` (gather_inside_self_loops) | 待最小状态/效果见证 |
| `edge.thickness` | geometry | 无运行消费见证 | `src/pyelk/algorithms/disco.py:537` (ElkGraphTransformer.import_edge) | 待最小状态/效果见证 |
| `edge.type` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.directionCongruency` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/directions.py:94` (_nodes) | 待最小状态/效果见证 |
| `layered.feedbackEdges` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/phase_factories.py:162` (_orthogonal_configuration) | 待最小状态/效果见证 |
| `layered.interactiveReferencePoint` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/interactive_order.py:21` (interactive_reference_point) | 待最小状态/效果见证 |
| `layered.mergeEdges` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/native_import.py:366` (ElkGraphImporter.create_port) | 待最小状态/效果见证 |
| `layered.mergeHierarchyEdges` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.allowNonFlowPortsToSwitchSides` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/north_south_ports.py:184` (north_south_port_preprocessor) | 待最小状态/效果见证 |
| `layered.portSortingStrategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/processors.py:155` (port_list_sorter) | 待最小状态/效果见证 |
| `layered.thoroughness` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/layering.py:34` (_admit) | 待最小状态/效果见证 |
| `layered.unnecessaryBendpoints` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/compound_post.py:62` (compound_postprocessor) | 待最小状态/效果见证 |
| `layered.generatePositionAndLayerIds` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.cycleBreaking.strategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layering.strategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layering.layerConstraint` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/constraint_processors.py:14` (_layer_constraint) | 待最小状态/效果见证 |
| `layered.layering.layerChoiceConstraint` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layering.layerId` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/native_transfer.py:97` (ElkGraphLayoutTransferrer.apply_node_layout) | 待最小状态/效果见证 |
| `layered.layering.minWidth.upperBoundOnWidth` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/width_layering.py:59` (MinWidthLayerer.process) | 待最小状态/效果见证 |
| `layered.layering.minWidth.upperLayerEstimationScalingFactor` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/width_layering.py:60` (MinWidthLayerer.process) | 待最小状态/效果见证 |
| `layered.layering.nodePromotion.strategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layering.nodePromotion.maxIterations` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layering.coffmanGraham.layerBound` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/coffman_graham_general.py:174` (CoffmanGrahamLayerer.process) | 待最小状态/效果见证 |
| `layered.crossingMinimization.strategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/hierarchical_driver.py:60` (hierarchical_layout) | 待最小状态/效果见证 |
| `layered.crossingMinimization.forceNodeModelOrder` | layout_strategy | geometry | `src/pyelk/algorithms/layered/barycenter_order.py:91` (BarycenterHeuristic.minimize_layer) | 限定见证 |
| `layered.crossingMinimization.hierarchicalSweepiness` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/sweep_type.py:60` (LayerSweepTypeDecider.use_bottom_up) | 待最小状态/效果见证 |
| `layered.crossingMinimization.semiInteractive` | unclassified_no_static_consumer_anchor | runtime_state | 未定位原生 accessor | 限定见证 |
| `layered.crossingMinimization.inLayerPredOf` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.crossingMinimization.inLayerSuccOf` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.crossingMinimization.positionChoiceConstraint` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.crossingMinimization.positionId` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/native_transfer.py:96` (ElkGraphLayoutTransferrer.apply_node_layout) | 待最小状态/效果见证 |
| `layered.crossingMinimization.greedySwitch.activationThreshold` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.crossingMinimization.greedySwitch.type` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.crossingMinimization.greedySwitchHierarchical.type` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/hierarchical_driver.py:70` (hierarchical_layout) | 待最小状态/效果见证 |
| `layered.nodePlacement.strategy` | layout_strategy | geometry | `src/pyelk/algorithms/layered/native_import.py:334` (ElkGraphImporter.transform_edge) | 限定见证 |
| `layered.nodePlacement.favorStraightEdges` | layout_strategy | geometry | `src/pyelk/algorithms/layered/brandes_koepf_general.py:323` (bk_node_placer) | 限定见证 |
| `layered.nodePlacement.bk.edgeStraightening` | layout_strategy | geometry | `src/pyelk/algorithms/layered/brandes_koepf_general.py:205` (_Compactor.__init__) | 限定见证 |
| `layered.nodePlacement.bk.fixedAlignment` | layout_strategy | geometry | `src/pyelk/algorithms/layered/brandes_koepf_general.py:322` (bk_node_placer) | 限定见证 |
| `layered.nodePlacement.linearSegments.deflectionDampening` | geometry | geometry | `src/pyelk/algorithms/layered/linear_segments_placement.py:223` (LinearSegmentsNodePlacer.balance_placement) | 限定见证 |
| `layered.nodePlacement.networkSimplex.nodeFlexibility` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.nodePlacement.networkSimplex.nodeFlexibility.default` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.nodePlacement.networkSimplex.nodeFlexibility.recomputeNodePlacement` | layout_strategy | geometry | `src/pyelk/algorithms/layered/utility_processors.py:54` (node_placement_repeater) | 限定见证 |
| `layered.edgeRouting.selfLoopDistribution` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/self_loops_general.py:252` (assign_port_sides) | 待最小状态/效果见证 |
| `layered.edgeRouting.selfLoopOrdering` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/self_loops_general.py:472` (PortRestorer.restore_ports) | 待最小状态/效果见证 |
| `layered.edgeRouting.splines.mode` | layout_strategy | geometry | `src/pyelk/algorithms/layered/spline_final.py:213` (FinalSplineBendpointsCalculator.process) | 限定见证 |
| `layered.edgeRouting.splines.sloppy.layerSpacingFactor` | geometry | geometry | `src/pyelk/algorithms/layered/spline_general.py:417` (SplineEdgeRouter.process) | 限定见证 |
| `layered.edgeRouting.polyline.slopedEdgeZoneWidth` | geometry | geometry | `src/pyelk/algorithms/layered/polyline_general.py:125` (PolylineEdgeRouter.process) | 限定见证 |
| `layered.spacing.baseValue` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/native_import_full.py:58` (FullElkGraphImporter.apply_base_spacing) | 待最小状态/效果见证 |
| `layered.spacing.edgeNodeBetweenLayers` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/center_label_switcher.py:133` (LabelDummySwitcher.width_sums) | 待最小状态/效果见证 |
| `layered.spacing.edgeEdgeBetweenLayers` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/hierarchical_port_size.py:26` (hierarchical_port_dummy_size_processor) | 待最小状态/效果见证 |
| `layered.spacing.nodeNodeBetweenLayers` | geometry | geometry | `src/pyelk/algorithms/layered/center_label_switcher.py:135` (LabelDummySwitcher.width_sums) | 限定见证 |
| `layered.priority.direction` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/cycles.py:133` (_before_layering) | 待最小状态/效果见证 |
| `layered.priority.shortness` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/layering.py:65` (_admit) | 待最小状态/效果见证 |
| `layered.priority.straightness` | geometry | 无运行消费见证 | `src/pyelk/algorithms/layered/brandes_koepf_general.py:73` (_Neighborhood._neighbors) | 待最小状态/效果见证 |
| `layered.compaction.connectedComponents` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/components.py:275` (combine_components) | 待最小状态/效果见证 |
| `layered.compaction.postCompaction.strategy` | layout_strategy | geometry | `src/pyelk/algorithms/layered/spline_final.py:214` (FinalSplineBendpointsCalculator.process) | 限定见证 |
| `layered.compaction.postCompaction.constraints` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.highDegreeNodes.treatment` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.highDegreeNodes.threshold` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.highDegreeNodes.treeHeight` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.wrapping.strategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.wrapping.additionalEdgeSpacing` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.wrapping.correctionFactor` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.wrapping.cutting.strategy` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.wrapping.cutting.cuts` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证；raw factory 不可用 |
| `layered.wrapping.cutting.msd.freedom` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.wrapping.validify.strategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.wrapping.validify.forbiddenIndices` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证；raw factory 不可用 |
| `layered.wrapping.multiEdge.improveCuts` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.wrapping.multiEdge.distancePenalty` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.wrapping.multiEdge.improveWrappedEdges` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.layerUnzipping.strategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layerUnzipping.minimizeEdgeLength` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layerUnzipping.layerSplit` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.layerUnzipping.resetOnLongEdges` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.edgeLabels.sideSelection` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/directions.py:100` (_nodes) | 待最小状态/效果见证 |
| `layered.edgeLabels.centerLabelPlacementStrategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/center_label_switcher.py:92` (LabelDummyInfo.__init__) | 待最小状态/效果见证 |
| `layered.considerModelOrder.strategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/input_model_sort.py:29` (_strategy) | 待最小状态/效果见证 |
| `layered.considerModelOrder.portModelOrder` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/input_model_sort.py:51` (sort_by_input_model) | 待最小状态/效果见证 |
| `layered.considerModelOrder.noModelOrder` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/model_order_import.py:52` (transform_ordered_ports) | 待最小状态/效果见证 |
| `layered.considerModelOrder.components` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/components.py:52` (_nodes) | 待最小状态/效果见证 |
| `layered.considerModelOrder.longEdgeStrategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/input_model_sort.py:34` (_node_comparator) | 待最小状态/效果见证 |
| `layered.considerModelOrder.crossingCounterNodeInfluence` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.considerModelOrder.crossingCounterPortInfluence` | unclassified_no_static_consumer_anchor | geometry | 未定位原生 accessor | 限定见证 |
| `layered.considerModelOrder.groupModelOrder.cycleBreakingId` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.considerModelOrder.groupModelOrder.crossingMinimizationId` | unclassified_no_static_consumer_anchor | runtime_state | 未定位原生 accessor | 限定见证 |
| `layered.considerModelOrder.groupModelOrder.componentGroupId` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.considerModelOrder.groupModelOrder.cbGroupOrderStrategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/cycles_general.py:199` (_group_enforced) | 待最小状态/效果见证 |
| `layered.considerModelOrder.groupModelOrder.cbPreferredSourceId` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.considerModelOrder.groupModelOrder.cbPreferredTargetId` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `layered.considerModelOrder.groupModelOrder.cmGroupOrderStrategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/layered/input_model_sort.py:35` (_node_comparator) | 待最小状态/效果见证 |
| `layered.considerModelOrder.groupModelOrder.cmEnforcedGroupOrders` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证；raw factory 不可用 |
| `stress.fixed` | layout_strategy | geometry | `src/pyelk/algorithms/stress.py:175` (StressMajorization.execute) | 限定见证 |
| `stress.desiredEdgeLength` | geometry | geometry | `src/pyelk/algorithms/stress.py:87` (StressMajorization.initialize) | 限定见证 |
| `stress.dimension` | layout_strategy | geometry | `src/pyelk/algorithms/stress.py:84` (StressMajorization.initialize) | 限定见证 |
| `stress.epsilon` | geometry | geometry | `src/pyelk/algorithms/stress.py:86` (StressMajorization.initialize) | 限定见证 |
| `stress.iterationLimit` | geometry | geometry | `src/pyelk/algorithms/stress.py:85` (StressMajorization.initialize) | 限定见证 |
| `mrtree.compaction` | layout_strategy | geometry | `src/pyelk/algorithms/mrtree.py:903` (compact_graph) | 限定见证 |
| `mrtree.edgeEndTextureLength` | geometry | geometry | `src/pyelk/algorithms/mrtree.py:1220` (route_edges) | 限定见证 |
| `mrtree.treeLevel` | geometry | 无运行消费见证 | `src/pyelk/algorithms/mrtree.py:731` (_tree_level) | 待最小状态/效果见证 |
| `mrtree.positionConstraint` | geometry | 无运行消费见证 | `src/pyelk/algorithms/mrtree.py:300` (order_nodes) | 待最小状态/效果见证 |
| `mrtree.weighting` | layout_strategy | geometry | `src/pyelk/algorithms/mrtree.py:259` (order_nodes) | 限定见证 |
| `mrtree.edgeRoutingMode` | layout_strategy | geometry | `src/pyelk/algorithms/mrtree.py:936` (compact_graph) | 限定见证 |
| `mrtree.searchOrder` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/mrtree.py:126` (treeify) | 待最小状态/效果见证 |
| `radial.centerOnRoot` | layout_strategy | geometry | `src/pyelk/algorithms/radial.py:612` (calculate_graph_size) | 限定见证 |
| `radial.orderId` | geometry | 无运行消费见证 | `src/pyelk/algorithms/radial.py:244` (IDSorter.sort.compare) | 待最小状态/效果见证 |
| `radial.radius` | geometry | geometry | `src/pyelk/algorithms/radial.py:157` (eades_layout) | 限定见证 |
| `radial.rotate` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/radial.py:719` (_assemble) | 待最小状态/效果见证 |
| `radial.compactor` | layout_strategy | geometry | `src/pyelk/algorithms/radial.py:541` (compact_graph) | 限定见证 |
| `radial.compactionStepSize` | geometry | 无运行消费见证 | `src/pyelk/algorithms/radial.py:445` (RadiusExtension.configure) | 待最小状态/效果见证 |
| `radial.sorter` | layout_strategy | geometry | `src/pyelk/algorithms/radial.py:158` (eades_layout) | 限定见证 |
| `radial.wedgeCriteria` | layout_strategy | geometry | `src/pyelk/algorithms/radial.py:160` (eades_layout) | 限定见证 |
| `radial.optimizationCriteria` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/radial.py:159` (eades_layout) | 待最小状态/效果见证 |
| `radial.rotation.targetAngle` | geometry | 无运行消费见证 | `src/pyelk/algorithms/radial.py:635` (rotate_graph) | 待最小状态/效果见证 |
| `radial.rotation.computeAdditionalWedgeSpace` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/radial.py:636` (rotate_graph) | 待最小状态/效果见证 |
| `radial.rotation.outgoingEdgeAngles` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/radial.py:721` (_assemble) | 待最小状态/效果见证 |
| `force.model` | layout_strategy | geometry | `src/pyelk/algorithms/force.py:536` (_layout) | 限定见证 |
| `force.iterations` | geometry | geometry | `src/pyelk/algorithms/force.py:461` (EadesModel.initialize) | 限定见证 |
| `force.repulsivePower` | geometry | geometry | `src/pyelk/algorithms/force.py:414` (AbstractForceModel.initialize) | 限定见证 |
| `force.temperature` | geometry | geometry | `src/pyelk/algorithms/force.py:489` (FruchtermanReingoldModel.initialize) | 限定见证 |
| `force.repulsion` | geometry | 无运行消费见证 | `src/pyelk/algorithms/force.py:463` (EadesModel.initialize) | 待最小状态/效果见证 |
| `polyomino.traversalStrategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor；Source `references/e19-packing-sources.json` worker:24490 | 待最小状态/效果见证 |
| `polyomino.lowLevelSort` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor；Source `references/e19-packing-sources.json` worker:24473 | 待最小状态/效果见证 |
| `polyomino.highLevelSort` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor；Source `references/e19-packing-sources.json` worker:24480 | 待最小状态/效果见证 |
| `polyomino.fill` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/disco.py:670` (DisCoPolyominoCompactor.compact)；Source `references/e19-packing-sources.json` worker:25928 | 待最小状态/效果见证 |
| `disco.componentCompaction.strategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/disco.py:714` (_layout) | 待最小状态/效果见证 |
| `disco.componentCompaction.componentLayoutAlgorithm` | geometry | geometry | `src/pyelk/algorithms/disco.py:709` (_layout) | 限定见证 |
| `disco.debug.discoGraph` | diagnostic | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证；raw factory 不可用 |
| `disco.debug.discoPolys` | diagnostic | 无运行消费见证 | `src/pyelk/algorithms/disco.py:717` (_layout) | 待最小状态/效果见证；raw factory 不可用 |
| `underlyingLayoutAlgorithm` | geometry | 无运行消费见证 | `src/pyelk/algorithms/spore.py:624` (_layout_overlap) | 待最小状态/效果见证 |
| `structure.structureExtractionStrategy` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `processingOrder.treeConstruction` | layout_strategy | geometry | `src/pyelk/algorithms/spore.py:228` (SporeImporter.import_graph) | 限定见证 |
| `processingOrder.spanningTreeCostFunction` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/spore.py:227` (SporeImporter.import_graph) | 待最小状态/效果见证 |
| `processingOrder.preferredRoot` | geometry | 无运行消费见证 | `src/pyelk/algorithms/spore.py:226` (SporeImporter.import_graph) | 待最小状态/效果见证 |
| `processingOrder.rootSelection` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/spore.py:230` (SporeImporter.import_graph) | 待最小状态/效果见证 |
| `compaction.compactionStrategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/spore.py:229` (SporeImporter.import_graph) | 待最小状态/效果见证 |
| `compaction.orthogonal` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/spore.py:239` (SporeImporter.import_graph) | 待最小状态/效果见证 |
| `overlapRemoval.maxIterations` | geometry | 无运行消费见证 | `src/pyelk/algorithms/spore.py:631` (_layout_overlap) | 待最小状态/效果见证 |
| `overlapRemoval.runScanline` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/spore.py:643` (_layout_overlap) | 待最小状态/效果见证 |
| `rectpacking.trybox` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:1104` (prepare_provider) | 待最小状态/效果见证 |
| `rectpacking.currentPosition` | unclassified_no_static_consumer_anchor | 无运行消费见证 | 未定位原生 accessor | 待最小状态/效果见证 |
| `rectpacking.desiredPosition` | geometry | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:1121` (interactive_reorder_phase) | 待最小状态/效果见证 |
| `rectpacking.inNewRow` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:500` (initial_place) | 待最小状态/效果见证 |
| `rectpacking.orderBySize` | layout_strategy | geometry | `src/pyelk/algorithms/rectpacking.py:1189` (_layout) | 限定见证 |
| `rectpacking.widthApproximation.strategy` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:1194` (_layout) | 待最小状态/效果见证 |
| `rectpacking.widthApproximation.targetWidth` | geometry | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:1060` (target_width_phase) | 待最小状态/效果见证 |
| `rectpacking.widthApproximation.optimizationGoal` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:1073` (greedy_width_phase) | 待最小状态/效果见证 |
| `rectpacking.widthApproximation.lastPlaceShift` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:1074` (greedy_width_phase) | 待最小状态/效果见证 |
| `rectpacking.packing.strategy` | layout_strategy | geometry | `src/pyelk/algorithms/rectpacking.py:1202` (_layout) | 限定见证 |
| `rectpacking.packing.compaction.rowHeightReevaluation` | layout_strategy | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:510` (initial_place) | 待最小状态/效果见证 |
| `rectpacking.packing.compaction.iterations` | geometry | 无运行消费见证 | `src/pyelk/algorithms/rectpacking.py:863` (compaction_phase) | 待最小状态/效果见证 |
| `rectpacking.whiteSpaceElimination.strategy` | layout_strategy | geometry | `src/pyelk/algorithms/rectpacking.py:1208` (_layout) | 限定见证 |

## 仍须最小见证的声明

JSON 每行都有 `minimalRemainingWitness` 与具体既有断言指针，下面仅按家族列有限缺口。几何/策略应使用真实适用输入的数值或执行后状态；callback 要真实调用；diagnostic/API metadata 要日志、presence、目标覆盖或查询状态，不强求几何变化。若 Source 仅提供 typed/internal 路径，就明确该通道，不伪造 raw factory。

- **core** (44): `algorithm`, `alignment`, `contentAlignment`, `debugMode`, `hierarchyHandling`, `interactive`, `interactiveLayout`, `omitNodeMicroLayout`, `position`, `commentBox`, `hypernode`, `labelManager`, `softwrappingFuzziness`, `margins`, `noLayout`, `scaleFactor`, `childAreaWidth`, `childAreaHeight`, `topdownLayout`, `animate`, `animTimeFactor`, `layoutAncestors`, `maxAnimTime`, `minAnimTime`, `progressBar`, `validateGraph`, `validateOptions`, `zoomToFit`, `partitioning.partition`, `partitioning.activate`, `font.size`, `insideSelfLoops.activate`, `insideSelfLoops.yo`, `edge.thickness`, `edge.type`, `underlyingLayoutAlgorithm`, `structure.structureExtractionStrategy`, `processingOrder.spanningTreeCostFunction`, `processingOrder.preferredRoot`, `processingOrder.rootSelection`, `compaction.compactionStrategy`, `compaction.orthogonal`, `overlapRemoval.maxIterations`, `overlapRemoval.runScanline`
- **disco** (3): `disco.componentCompaction.strategy`, `disco.debug.discoGraph`, `disco.debug.discoPolys`
- **force** (1): `force.repulsion`
- **json** (2): `json.shapeCoords`, `json.edgeCoords`
- **layered.allowNonFlowPortsToSwitchSides** (1): `layered.allowNonFlowPortsToSwitchSides`
- **layered.compaction** (2): `layered.compaction.connectedComponents`, `layered.compaction.postCompaction.constraints`
- **layered.considerModelOrder** (13): `layered.considerModelOrder.strategy`, `layered.considerModelOrder.portModelOrder`, `layered.considerModelOrder.noModelOrder`, `layered.considerModelOrder.components`, `layered.considerModelOrder.longEdgeStrategy`, `layered.considerModelOrder.crossingCounterNodeInfluence`, `layered.considerModelOrder.groupModelOrder.cycleBreakingId`, `layered.considerModelOrder.groupModelOrder.componentGroupId`, `layered.considerModelOrder.groupModelOrder.cbGroupOrderStrategy`, `layered.considerModelOrder.groupModelOrder.cbPreferredSourceId`, `layered.considerModelOrder.groupModelOrder.cbPreferredTargetId`, `layered.considerModelOrder.groupModelOrder.cmGroupOrderStrategy`, `layered.considerModelOrder.groupModelOrder.cmEnforcedGroupOrders`
- **layered.crossingMinimization** (9): `layered.crossingMinimization.strategy`, `layered.crossingMinimization.hierarchicalSweepiness`, `layered.crossingMinimization.inLayerPredOf`, `layered.crossingMinimization.inLayerSuccOf`, `layered.crossingMinimization.positionChoiceConstraint`, `layered.crossingMinimization.positionId`, `layered.crossingMinimization.greedySwitch.activationThreshold`, `layered.crossingMinimization.greedySwitch.type`, `layered.crossingMinimization.greedySwitchHierarchical.type`
- **layered.cycleBreaking** (1): `layered.cycleBreaking.strategy`
- **layered.directionCongruency** (1): `layered.directionCongruency`
- **layered.edgeLabels** (2): `layered.edgeLabels.sideSelection`, `layered.edgeLabels.centerLabelPlacementStrategy`
- **layered.edgeRouting** (2): `layered.edgeRouting.selfLoopDistribution`, `layered.edgeRouting.selfLoopOrdering`
- **layered.feedbackEdges** (1): `layered.feedbackEdges`
- **layered.generatePositionAndLayerIds** (1): `layered.generatePositionAndLayerIds`
- **layered.highDegreeNodes** (1): `layered.highDegreeNodes.treeHeight`
- **layered.interactiveReferencePoint** (1): `layered.interactiveReferencePoint`
- **layered.layerUnzipping** (4): `layered.layerUnzipping.strategy`, `layered.layerUnzipping.minimizeEdgeLength`, `layered.layerUnzipping.layerSplit`, `layered.layerUnzipping.resetOnLongEdges`
- **layered.layering** (9): `layered.layering.strategy`, `layered.layering.layerConstraint`, `layered.layering.layerChoiceConstraint`, `layered.layering.layerId`, `layered.layering.minWidth.upperBoundOnWidth`, `layered.layering.minWidth.upperLayerEstimationScalingFactor`, `layered.layering.nodePromotion.strategy`, `layered.layering.nodePromotion.maxIterations`, `layered.layering.coffmanGraham.layerBound`
- **layered.mergeEdges** (1): `layered.mergeEdges`
- **layered.mergeHierarchyEdges** (1): `layered.mergeHierarchyEdges`
- **layered.portSortingStrategy** (1): `layered.portSortingStrategy`
- **layered.priority** (3): `layered.priority.direction`, `layered.priority.shortness`, `layered.priority.straightness`
- **layered.spacing** (3): `layered.spacing.baseValue`, `layered.spacing.edgeNodeBetweenLayers`, `layered.spacing.edgeEdgeBetweenLayers`
- **layered.thoroughness** (1): `layered.thoroughness`
- **layered.unnecessaryBendpoints** (1): `layered.unnecessaryBendpoints`
- **layered.wrapping** (8): `layered.wrapping.strategy`, `layered.wrapping.additionalEdgeSpacing`, `layered.wrapping.cutting.cuts`, `layered.wrapping.cutting.msd.freedom`, `layered.wrapping.validify.strategy`, `layered.wrapping.validify.forbiddenIndices`, `layered.wrapping.multiEdge.improveCuts`, `layered.wrapping.multiEdge.distancePenalty`
- **mrtree** (3): `mrtree.treeLevel`, `mrtree.positionConstraint`, `mrtree.searchOrder`
- **polyomino** (4): `polyomino.traversalStrategy`, `polyomino.lowLevelSort`, `polyomino.highLevelSort`, `polyomino.fill`
- **radial** (7): `radial.orderId`, `radial.rotate`, `radial.compactionStepSize`, `radial.optimizationCriteria`, `radial.rotation.targetAngle`, `radial.rotation.computeAdditionalWedgeSpace`, `radial.rotation.outgoingEdgeAngles`
- **rectpacking** (10): `rectpacking.trybox`, `rectpacking.currentPosition`, `rectpacking.desiredPosition`, `rectpacking.inNewRow`, `rectpacking.widthApproximation.strategy`, `rectpacking.widthApproximation.targetWidth`, `rectpacking.widthApproximation.optimizationGoal`, `rectpacking.widthApproximation.lastPlaceShift`, `rectpacking.packing.compaction.rowHeightReevaluation`, `rectpacking.packing.compaction.iterations`
- **spacing** (12): `spacing.commentComment`, `spacing.commentNode`, `spacing.edgeEdge`, `spacing.edgeLabel`, `spacing.edgeNode`, `spacing.labelLabel`, `spacing.labelNode`, `spacing.labelPortHorizontal`, `spacing.labelPortVertical`, `spacing.nodeSelfLoop`, `spacing.portPort`, `spacing.portsSurrounding`
- **topdown** (8): `topdown.sizeCategories`, `topdown.sizeCategoriesHierarchicalNodeWeight`, `topdown.scaleFactor`, `topdown.sizeApproximator`, `topdown.hierarchicalNodeWidth`, `topdown.hierarchicalNodeAspectRatio`, `topdown.nodeType`, `topdown.scaleCap`

编译源包中的角色/默认声明与 getter 行只定位实现，不证明任何具体请求消费了值。已失败或无变化的尝试保留在 JSON；表中未获见证项不被提升为“已完成”，也不被归为算法缺失。
