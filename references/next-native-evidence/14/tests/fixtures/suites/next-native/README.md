# 下一迁移批次的独立原始参考

这里只保存 elkjs 0.12.1 的研究输入、实际原输出和必要开发探针。E13/E16 仍为 planned；这些材料不代表当前安装包、完整 ports/labels、完整算法或发行验收通过。Python 私有实现没有参与定义预期结果。

## 官方单请求路径

`tools/platform/capture_next_reference.py` 原样调用既有 `tools/reference/capture_layout.cjs`。每个请求启动一个独立 Node 进程，记录 Node 二进制 SHA/版本、12 个 npm 文件 SHA、原请求、argv/cwd/PID、日志、退出码及原 observation 字节。新输出目录必须不存在。

```powershell
python tools/platform/capture_next_reference.py --node 'C:\Program Files\nodejs\node.exe' --package .local/npm-elkjs/package --suite tests/fixtures/suites/next-native --out test-runs/new-next-reference
```

省略 `--suite` 时也是本目录。不需要重采已经存在的无关输入。各子目录可单独传给 `--suite`。

| 原请求集 | 已保存收据 | 目的 |
| --- | --- | --- |
| 本目录 6 项 | `references/next-native-reference.json` | fixed、box、seed7 random、FIXED_SIDE/FIXED_POS ports、给定尺寸 node/edge labels |
| `fixed-branches/` 6 项 | 该目录 `oracle.json` | position/minimum、port/label、bend chain、shared-port junction、真实缺 section 错误、固定 root 尺寸 |
| `box-random-branches/` 10 项 | 该目录 `oracle.json` | 三 GROUP 模式/equal-area heap、priority/interactive、expand/minimum/content、非整数、random edge/ports/负 seed |
| `random-unseeded/` 1 项 | `oracle.json` 与 `clock-window.json` | 真 seed0，实际系统时钟窗口；坐标不是确定性黄金值 |
| `provider-state/` 1 项 | 该目录 `oracle.json` | child fixed → parent box 共享已导入状态；不能重新从原 JSON 恢复已清除的约束 |
| `json-transfer/` 4 项 | 该目录 `oracle.json` | 嵌套 fixed 的原 JSON owner 与当前 edge container、保留 section id/业务字段、INHERIT/PARENT/ROOT/CONTAINER 坐标 |
| `mrtree-first/` 4 项 | 该目录 `oracle.json` | 树/star/forest/cyclic，四方向及 DFS/BFS 的首批独立原输出；完整私有算法尚未验收 |
| `mrtree-diagnostics/` 1 项 | 该目录 `oracle.json` | 原 tree-right 图仅开启 measureExecutionTime，真实上游返回 TypeError/java.lang.NullPointerException；没有推断其他 flags 组合 |
| `radial-first/` 3 项 | 该目录 `oracle.json` | 默认给定标签、RADIAL_COMPACTION/ID/port labels、WEDGE/POLAR/rotation；第三项的原输出坐标是 JSON null，不能当有限几何正本或删除失败记录 |

`oracle.json` 中的 Base64 解码后才是原始请求/观测字节；SHA 和 stdout/stderr 均须保留。官方输出中的 `$H`、container、section ID 等原差异没有被剔除。私有 provider 数学对照仍有中央 JSON/递归/错误类接入义务，不能把只有数学一致写成整图完全一致。

## 局部函数与只读导入探针

这些局部观察与上面的普通 API 收据分开：

- `ports-helper-probe.cjs`：原 worker P01 函数，在只提供字段/属性容器的脚手架中执行；`ports-helper-request.json`/`ports-helper-oracle.json` 保存 12 项输入与真实 Node 输出。一进程 12 项，不是 12 次公开布局。
- `ports-order-probe.cjs`：执行原 P02 和真实 GWT insertion/merge sort；8 项保存在 `ports-order-request.json`/`ports-order-oracle.json`。混合缺省 index 的循环比较器不能替换为 Python Timsort。三份 `*-source-original.json` 保留当时源码提案原字节。
- `ports-import-probe.cjs`：对固定完整 worker 内存插入只读 import-return 钩子，原 JSON/EMF/算法全部执行。`ports-import-oracle.json` 保留 2 个导入状态和未改变的官方 API 结果；它没有证明私有 transfer 手动设置的位置是布局坐标。原 pretty Worker 缺少 terminate 方法时真实错误也保留，不伪造关闭成功。
- `cells-probe.cjs`：完整原 worker 的真实 Cell/Atomic/Grid/Strip/Label 类，8 组对象级输入。只把 JSON 输入映射到真实对象字段；标签使用原 `LLabelAdapter`。`cells-oracle.json` 是原结果，`cells-oracle.command.json` 是实际命令记录。
- `ports-placement-probe.cjs`：9 组原 placement primitive，使用调用方给定的 cell 矩形/尺寸/margin，不计算完整节点尺寸。原 NodeContext 有序容器准备 SOUTH/WEST 反向顺序；缺省 alignment 原值是 DISTRIBUTED。原结果与命令分别在 `ports-placement-oracle.json`、`ports-placement-oracle.command.json`。
- `port-context-adapter-probe.cjs`：单个原透明 adapter 对象控。NORTH_SOUTH_PORT 的 raw outgoing 非空时，原 `transparentNorthSouthEdges=true` 视图仍先返回空，因而 NEXT 标签规则为 true。它没有替代完整 NS/self-loop 预处理；原结果和实际命令均保留。

新局部采集的参数均为 npm 包目录、请求文件、新输出文件。输出文件必须不存在。例如：

```powershell
node tests/fixtures/suites/next-native/cells-probe.cjs .local/npm-elkjs/package tests/fixtures/suites/next-native/cells-request.json test-runs/new-cells.json
python tests/fixtures/suites/next-native/compare_cells.py .local/migration-next/src tests/fixtures/suites/next-native/cells-request.json tests/fixtures/suites/next-native/cells-oracle.json test-runs/new-cells-comparison.json
node tests/fixtures/suites/next-native/ports-placement-probe.cjs .local/npm-elkjs/package tests/fixtures/suites/next-native/ports-placement-request.json test-runs/new-placement.json
python tests/fixtures/suites/next-native/compare_placement.py .local/migration-next/src tests/fixtures/suites/next-native/ports-placement-request.json tests/fixtures/suites/next-native/ports-placement-oracle.json test-runs/new-placement-comparison.json
```

比较脚本只读取已保存的原 Node 结果，不用候选生成预期。对象级一致不代表完整 NodeContext、label/port 尺寸或端到端布局已经接通。

新增小批次可按需单独重核，不重复上面的旧样例：

| 探针 / 请求 / 原结果前缀 | 比较入口 | 范围 |
| --- | --- | --- |
| `size-math-*` | `compare_size_math.py` | 6 个真实前序 cell 对象输入：free/ratio/fixed-position、标签 margin、minimum/padding、fixedGraph 尺寸与 cell 矩形分离；没有执行完整 cell 创建或节点尺寸流水线 |
| `node-size-process-*` | `compare_node_size_process.py` | 3 个真实 LGraph adapter standalone process：INSIDE 约束标签重叠、OUTSIDE 三端口且 apply=false、给定内外节点标签/负 offset/计算 padding；generic ElkGraph adapter 与完整 layered 仍分开 |
| `generic-micro-*` | `compare_generic_micro.py` | 2 个真实 JsonImporter→ElkGraphAdapter→NodeMicroLayout 输入，覆盖 equal-index 回落排序/标签 HEAD-TAIL/margin，以及 incoming same-owner+YO 不等于 compound connection；额外 CASE_ID 可只重核修复项 |
| `mrtree-stages-*` | `compare_mrtree_stages.py` | 已保存的 treeify/root/Walker/方向显式阶段与 12 个原 rounding 边界；不等于完整 assembled provider |
| `mrtree-routing-*` | `compare_mrtree_routing.py` | 3 个给定位置/层次图的 compaction/router，127/128 装箱身份及补偿均值；不调用公共 provider 或 NodeMicroLayout |
| `options-parser-*` | `compare_options_parser.py` | 15 个实际原 LayoutOptionData parser 输入；额外 CASE_ID 参数可只复核受修改的单项，宿主严格拒绝非有限值等差异明确保留 |

例如读取既有原始结果，只执行当前私有函数：

```powershell
python tests/fixtures/suites/next-native/compare_size_math.py .local/migration-next/src tests/fixtures/suites/next-native/size-math-request.json tests/fixtures/suites/next-native/size-math-oracle.json test-runs/new-size-math-comparison.json
python tests/fixtures/suites/next-native/compare_node_size_process.py .local/migration-next/src tests/fixtures/suites/next-native/node-size-process-request.json tests/fixtures/suites/next-native/node-size-process-oracle.json test-runs/new-size-process-comparison.json
python tests/fixtures/suites/next-native/compare_generic_micro.py .local/migration-next/src tests/fixtures/suites/next-native/generic-micro-request.json tests/fixtures/suites/next-native/generic-micro-oracle.json test-runs/new-generic-micro-comparison.json
python tests/fixtures/suites/next-native/compare_mrtree_routing.py .local/migration-next/src tests/fixtures/suites/next-native/mrtree-routing-request.json tests/fixtures/suites/next-native/mrtree-routing-oracle.json test-runs/new-routing-comparison.json
python tests/fixtures/suites/next-native/compare_radial.py .local/migration-next/src tests/fixtures/suites/next-native/radial-first/oracle.json test-runs/new-radial-comparison.json radial-default-labels
```

这些新比较器使用既有严格 JSON 类型/数值差异函数，记录源码前后 SHA。MrTree 与 standalone process 比较器记录实际导入的私有模块闭包，避免把其他 agent 正在编写但未导入的算法误认为本次执行依赖。保留原始 Node 进程记录；离线比较不会重新执行 Node，也不会将旧源码 SHA 改绑到新实现。

`radial-hashset-*` 单独保存实际 ElkNode 的已有 hash 与径向 next-level 集合观察。两个普通对象控证明既有 hash 的数值大小不会改变 ES Map 桶首次插入顺序；第三项明确是人为覆盖私有 `$H` 的运行时支持探针，展示 32 位碰撞时桶内分组顺序。它不是公共布局、不是新的图数量限制，也没有给任意 HashSet 赋予全局插入有序保证。

`compare_radial.py` 执行当前私有 provider 的真实默认 generic micro 路径；可用末尾 CASE_ID 只复核本次修改项。原 strict 差异完整保留，已有几何容差通过 `/result` 包装选择，业务字段仍严格。源生成 `$H` 缺项仅在原请求未提供该字段的 node/port 路径单列；不会全局删除同名业务字段。报告分别列 `sourceWireParity`、`validFiniteGeometry` 和 `upstreamNonfiniteGeometry`，不把包含上游 null 坐标的输出一致解释成有效几何通过。它不认证安装包、公开入口或完整算法迁移。

`json-wire-probe.cjs` 原样调用固定 worker 的 JSONNumber/JSONObject helper，再执行与参考 collector 相同的最终 `JSON.stringify`。三项 NaN/+Infinity/-Infinity 在内部仍是非有限 Number，只在最终 wire 变为 null；`json-wire-sources.json`、原请求/观察/命令保留这条独立证据。它不允许非有限输入，也不允许修改算法内部数值或几何容差。

这些 `.cjs` 探针的参数和边界写在文件头。只有原 worker 的函数体定义算法；脚手架不提供 Python 预期结果。实现、独立比较和首败保存在 `test-runs/20261104-E13-01/{A,V}` 与 `test-runs/20261104-E16-01/{B,V}`。正式产品仍由 root 控制；可恢复的私有代码入口见 `migration/next-native/manifest.json` 和 root 的 workspace 工具。

## Force / Stress independent initial cases

The four requests in `force-stress-first/` were constructed independently, then captured from fixed elkjs with one actual Node process per request. `oracle.json` retains original request/observation bytes, commands and logs. The original worker's terminate TypeError is preserved; a returned graph does not prove successful termination.

- Force: EADES with weights, ports, labels and repulsive bendpoints; FR with three components and a shared RNG.
- Stress: interactive X with a fixed node and explicit edge length; noninteractive real Force initialization followed by Y updates.

Run only the provider affected by the current change:

```powershell
python tests/fixtures/suites/next-native/compare_force_stress.py .local/migration-next/src tests/fixtures/suites/next-native/force-stress-first/oracle.json test-runs/new-force-comparison.json force
python tests/fixtures/suites/next-native/compare_force_stress.py .local/migration-next/src tests/fixtures/suites/next-native/force-stress-first/oracle.json test-runs/new-stress-comparison.json stress
```

An optional final CASE_ID selects one affected case. The comparator calls the native provider and real default generic micro, retaining source hashes, full strict differences, `sourceWireParity` and finite-geometry counts. It does not certify the public API, complete algorithm or installed package. It only classifies generated node/port `$H` absences where the request supplied no such field; user business fields remain strict.

`stress-inline-default/` adds one original interactive request with two fixed nodes and no explicit inline option. `check_stress_inline.py ORACLE REPORT` recomputes original evidence only: property-false placement is `(101,68.5)`, whereas true-inline placement would be `(91,76.5)`. Metadata support true is separate from the runtime property default. This does not replay the four successful provider cases.

`port-dummy-kernels-*` uses one actual original Node process for three supplied intermediate object graphs: two-layer Inverted HEAD-marker asymmetry and zero-size dummies; Merger component-only matching, label eligibility and NORMAL barriers. Exact adjacency, scratch IDs, junction identity and the retained layer pointer of a removed dummy are compared. No full layout, crossing or scheduler runs.

```powershell
python tests/fixtures/suites/next-native/compare_port_dummy_kernels.py .local/migration-next/src tests/fixtures/suites/next-native/port-dummy-kernels-request.json tests/fixtures/suites/next-native/port-dummy-kernels-oracle.json test-runs/new-port-dummy-comparison.json
```

An optional final CASE_ID selects one affected case. Original commands, logs, inputs, observations and imported-module hashes are retained. Supplied intermediate state is not claimed as calculated layout geometry.

`spore-foundation-*` covers six original object inputs for E19's five approved data/scalar leaves: separated rectangles, equal centers, equal X, equal Y, two-axis overlap and zero-size touching. It also checks original-reference ownership, working copies, translate/setCenter and fresh Graph container identity. One actual Node process executes six object cases, not six public layouts.

```powershell
python tests/fixtures/suites/next-native/compare_spore_foundation.py .local/migration-next/src tests/fixtures/suites/next-native/spore-foundation-request.json tests/fixtures/suites/next-native/spore-foundation-oracle.json test-runs/new-spore-foundation.json
```

This does not run the importer, margin hook, jitter, Delaunay, tree or complete packing provider. An optional final CASE_ID selects one affected case.

`margin-only-*` runs original JsonImporter -> generic ElkGraphAdapter -> NodeMarginCalculator only. Its new input deliberately lists East before North despite FIXED_ORDER, includes a large minimum and size constraints, and supplies overflowing labels. Original order and all shape positions/sizes must remain unchanged. The source caller does not run NodeMicroLayout, so the complete micro pipeline cannot substitute for this margin-only operation.

```powershell
python tests/fixtures/suites/next-native/compare_margin_only.py .local/migration-next/src tests/fixtures/suites/next-native/margin-only-request.json tests/fixtures/suites/next-native/margin-only-oracle.json test-runs/new-margin-only.json
```

An optional final CASE_ID selects one affected case. This input's margin is top3/right22/bottom0/left4. Original observations, commands and module hashes remain available; this is not complete Spore layout acceptance.

`barycenter-forster-*` contains three new original object cases: same-layer partial recursion with duplicate/self associates; two-pass Forster constraints with duplicate successors and singleton-group zero weights; and the base calculate -> unknown fill -> source sort -> real Forster caller. Supplied port ranks and initial states are explicit intermediate inputs, not results from a rank producer. Exact states, order, shared identities and the next seeded random draw are compared.

```powershell
python tests/fixtures/suites/next-native/compare_barycenter_forster.py .local/migration-next/src tests/fixtures/suites/next-native/barycenter-forster-request.json tests/fixtures/suites/next-native/barycenter-forster-oracle.json test-runs/new-barycenter-forster.json
```

An optional final CASE_ID selects one affected case. This runs no ModelOrder subtype, complete rank producer, crossing counter, scheduler or full layout. Original raw bytes and actual process commands are retained separately from the private comparison.

`model-order-boxes-*` records three actual source comparator controls: cached 127, independently boxed 129 and one shared 129 box. Equal numerical group IDs do not imply the same source Integer object. The comparator also preserves the original repeated-comparison sign changes. These are local source observations, not a new numerical group limit.

`spore-import-*` provides two new local import/cost/update/transfer fixtures. Intermediate translations are supplied explicitly. The collision fixture controls four entropy draws `[0.5,0.5,0.75,0.25]` to verify a zero-delta collision round followed by X/Y updates and a fresh key lookup; it is labelled instrumented and does not assert matching V8 random trajectories.

The initial oracle and failed comparison retain the original input-policy mismatch. The additional `spore-import-recorded-*` oracle stores actual source input before/after, including generated `$H` additions. The native comparator requires its owned input to remain unchanged and retains raw differences; source mutation diagnostics are kept separate from the strict cost/geometry comparison.

```powershell
python tests/fixtures/suites/next-native/compare_spore_import.py .local/migration-next/src tests/fixtures/suites/next-native/spore-import-request.json tests/fixtures/suites/next-native/spore-import-recorded-oracle.json test-runs/new-spore-import.json
```

An optional final CASE_ID selects one affected case. This does not run Delaunay, Grow/Depth phases or complete packing providers. Tagged nonfinite directional scalar observations are not presented as valid finite layout geometry.

`host-boundaries-*` separately records numeric-ID string selection, real same-session Box invocation and the parent-adapter minimum query. The first minimum request has no active node-label placement and returns zero; it is retained without claiming a nonzero size proof. `host-minimum-active-*` adds one active-placement request: original and native return 70 by 20, ignore the 1000 by 1000 inside port label and leave geometry unchanged.

```powershell
python -I tests/fixtures/suites/next-native/compare_host_boundaries.py PRIVATE_SRC tests/fixtures/suites/next-native/host-minimum-active-request.json tests/fixtures/suites/next-native/host-minimum-active-oracle.json test-runs/new-host-minimum.json
```

`triangulation-*` contains six new object cases for signed32 scalar hashing, collision-bucket delete/reinsert order, asymmetric degenerate triangle lookup, actual four-point and collinear triangulation, and tied-cost naive tree ordering. Nonfinite intermediate values are explicitly tagged in this object protocol; they are not finite-layout acceptance.

```powershell
python -I tests/fixtures/suites/next-native/compare_triangulation.py PRIVATE_SRC tests/fixtures/suites/next-native/triangulation-request.json tests/fixtures/suites/next-native/triangulation-oracle.json test-runs/new-triangulation.json
```

`spore-providers/` contains two new complete original provider requests, each captured in an independent Node process: four overlapping nodes and four spread nodes with an overflowing node label. The private comparison observes the actual margin-only importer call and requires zero full-Micro substitutions. It keeps strict differences, original termination errors, finite-geometry status and source wire parity separate.

```powershell
python -I tests/fixtures/suites/next-native/compare_spore_providers.py PRIVATE_SRC tests/fixtures/suites/next-native/spore-providers/oracle.json test-runs/new-spore-overlap.json sporeOverlap
python -I tests/fixtures/suites/next-native/compare_spore_providers.py PRIVATE_SRC tests/fixtures/suites/next-native/spore-providers/oracle.json test-runs/new-spore-compaction.json sporeCompaction
```

These commands compare saved independent source facts. They do not recapture old successful cases or certify public registration, recursive coordination, installed packages or lifecycle behavior.

`compare_model_order_boxes.py PRIVATE_SRC REQUEST ORACLE REPORT` compares the saved three `model-order-boxes-*` scalar controls with the native subtype and its explicit box tokens. It does not recapture Node. Central parse/assignment provenance is a separate integration obligation.

`port-distribution-*` supplies a new two-layer object graph containing mixed and parallel incidences, an empty node, in-layer connections, an NS dummy and unconnected ports with retained scratch values. Four operations run the actual NodeRelative and LayerTotal rank producers and forward port sweeps. Every rank/barycenter slot, position and port order is compared; rank values are not supplied by the fixture. The initial original bridge failure used the wrong lexical setter name and is retained separately.

```powershell
python -I tests/fixtures/suites/next-native/compare_port_distribution.py PRIVATE_SRC tests/fixtures/suites/next-native/port-distribution-request.json tests/fixtures/suites/next-native/port-distribution-oracle.json test-runs/new-port-distribution.json
```

`enumset-identity-*` records only original scalar behavior: Core EnumSet defaults are shared, are not type4 Cloneable and do not materialize on read. A single `optsToCfg` global value is shared across configured nodes and does materialize. These facts do not imply the same policy for cloneable Insets/Vec2 values or for independent local parses.

```powershell
python -I tests/fixtures/suites/next-native/compare_enumset_identity.py PRIVATE_SRC tests/fixtures/suites/next-native/enumset-identity-request.json tests/fixtures/suites/next-native/enumset-identity-oracle.json test-runs/new-enumset-identity.json
```

The comparator keeps the source's pre-configurator snapshot and the native session's pre-read snapshot separate: selected globals already belong to the native session at construction. Source type4 remains an upstream cast observation rather than a fabricated Python flag.

`disco-data-*` contains two new original object cases for polygon reference versus cached bounds, extension offsets, dirty/reused cache identities, duplicate add and reparent effects, global component order and the literal cell-size recommendation. Empty extrema stay tagged diagnostics. No polygon intersection, rasterization or packing provider runs.

```powershell
python -I tests/fixtures/suites/next-native/compare_disco_data.py PRIVATE_SRC tests/fixtures/suites/next-native/disco-data-request.json tests/fixtures/suites/next-native/disco-data-oracle.json test-runs/new-disco-data.json
```

`sweep-copy-*` records one new original constructor-alias object: node-order rows copy independently, while the copy constructor shares inner captured port-list objects. `sweep-transfer-*` records two original restore objects with supplied order: explicit north-to-south anchor Y becomes 8, while south-to-north becomes -8. Existing FIXED_RATIO survives and FREE becomes FIXED_ORDER. These are local restore facts, not calculated crossing scores or a complete sweep.

`disco-polygon-*` records four new original boolean observations. A strictly contained path or a proper crossing yields component intersection. A polygon enclosing the entire cell, or a path exactly on its boundary, returns false in these source predicates. The literal scalar tolerance is 1e-5; it is algorithm behavior and does not replace the unchanged comparison tolerances. No generic point-in-polygon or bounding-box substitute is implied.

Primitive original probes accept three arguments: the locked npm package, their matching request JSON and a new observation filename. For a genuinely new affected input, a direct example is:

```powershell
node tests/fixtures/suites/next-native/disco-polygon-probe.cjs .local/npm-elkjs/package tests/fixtures/suites/next-native/disco-polygon-request.json test-runs/new-disco-polygon.json
```

The saved `.oracle.command.json` files retain actual commands from the original captures. Existing successful original inputs should normally be compared from their saved facts rather than recaptured. Source-only observations do not certify a future candidate implementation.

The first native SweepCopy comparison uses the saved copy and transfer observations independently:

```powershell
python -I tests/fixtures/suites/next-native/compare_sweep_copy.py PRIVATE_SRC tests/fixtures/suites/next-native/sweep-copy-request.json tests/fixtures/suites/next-native/sweep-copy-oracle.json test-runs/new-sweep-copy.json copy
python -I tests/fixtures/suites/next-native/compare_sweep_copy.py PRIVATE_SRC tests/fixtures/suites/next-native/sweep-transfer-request.json tests/fixtures/suites/next-native/sweep-transfer-oracle.json test-runs/new-sweep-transfer.json transfer
```

These compare alias depth and actual local restore behavior. Neither command runs a crossing score, complete sweep scheduler or old successful layout group.

`basic-crossings-*` contains three new original objects: Fenwick multiplicity/exclusive-prefix ranks and fresh clear buffers; actual between-layer counting with parallel/mixed/in-layer incidences; and in-layer open-arc multiplicity times between-layer degree. The two source scores are 8 and 1. Position buffers, cardinalities, persistent empty endings, stale cache flags and live port order are compared as well as the score.

```powershell
python -I tests/fixtures/suites/next-native/compare_basic_crossings.py PRIVATE_SRC tests/fixtures/suites/next-native/basic-crossings-request.json tests/fixtures/suites/next-native/basic-crossings-oracle.json test-runs/new-basic-crossings.json
```

This is the real basic score kernel on supplied intermediate state. It does not execute NS/Hyperedge dispatch, local swaps, complete sweep scheduling or a layout provider.

The saved four DisCo polygon booleans can now be compared with the actual native predicate implementation:

```powershell
python -I tests/fixtures/suites/next-native/compare_disco_polygon.py PRIVATE_SRC tests/fixtures/suites/next-native/disco-polygon-request.json tests/fixtures/suites/next-native/disco-polygon-oracle.json test-runs/new-disco-polygon.json
```

This keeps the source tolerance as a separate recorded fact, compares strict boolean types and runs no rasterizer or layout provider.

`generic-targets-*` is one new original JsonImporter plus global LayoutConfigurator object witness across nine holders. It records label-only global font targets while preserving an explicitly local node font, local priority0 over global129, explicit false presence, and global empty-EnumSet sharing versus a distinct local set. Original input strings retain runtime identity additions separately from the native owned-input policy.

```powershell
python -I tests/fixtures/suites/next-native/compare_generic_targets.py PRIVATE_SRC tests/fixtures/suites/next-native/generic-targets-request.json tests/fixtures/suites/next-native/generic-targets-oracle.json test-runs/new-generic-targets.json
```

This invokes property import/configuration only. It does not rerun the old ten scalar inputs, a Box request, complete micro layout or a provider group.

`polyomino-grid-*` contains two new original foundation objects: two-bit states across word boundaries and logical-width padding; and center/weak-area/reinitialize behavior. Original invalid accesses distinguish Java bounds exceptions from JavaScript TypeError. The native comparison preserves full raw error differences and separately compares values plus declared Python error-family mapping. It explicitly reports `strictRawParity: false` when engine error text differs.

```powershell
python -I tests/fixtures/suites/next-native/compare_polyomino_grid.py PRIVATE_SRC tests/fixtures/suites/next-native/polyomino-grid-request.json tests/fixtures/suites/next-native/polyomino-grid-oracle.json test-runs/new-polyomino-grid.json
```

This runs no rasterizer, overlay/extension collision logic, traversal, packing or layout provider. A value/error-family match must not be relabelled as exact raw exception protocol parity.

`ns-crossings-*` adds two new original NS counter objects. One combines weighted target degrees, a degree-zero endpoint that still enters the queue, and repeated LONG-owner stack entries that overwrite the same first-EAST slot. The other places a LABEL between layout units to check the actual remembered-unit flush rule. Scores are 2 and 0; full position, endpoint-add order and BIT scratch are compared, not only scores.

```powershell
python -I tests/fixtures/suites/next-native/compare_ns_crossings.py PRIVATE_SRC tests/fixtures/suites/next-native/ns-crossings-request.json tests/fixtures/suites/next-native/ns-crossings-oracle.json test-runs/new-ns-crossings.json
```

Observers delegate actual init/add methods without modifying their math. These supplied intermediate objects do not execute old basic cases, NS pre/post layout, Hyperedge dispatch or a complete sweep.
# Polyomino raster and overlay objects

`polyomino-raster-request.json` defines two independent original-worker object
cases. Run `node polyomino-raster-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_polyomino_raster.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
The saved original observation covers the actual DCPolyomino constructor,
strict polygon rasterization, fractional cell dimensions, extension rays,
center-based overlay/collision and filled bounds. The aligned boundary case
intentionally has an empty raster and retains the original empty-bound
sentinels. These are object-level observations, not complete packing layouts.

# RectPacking drawing and row objects

`rectpacking-objects-request.json` is an independent object request, with no
candidate-generated expected values. Run `node rectpacking-objects-probe.cjs
PACKAGE REQUEST NEW_OBSERVATION`, then `python compare_rectpacking_objects.py
PRIVATE_SRC REQUEST ORACLE NEW_REPORT`. It observes DrawingData's positive-size
cache updates and retention, IEEE scale results, dimensions/reset, BlockRow's
setters followed by refresh, and RectRow's different empty sentinels and absent
block removal. The observation does not execute packing or width search.

# Hyperedge crossing objects

Run `node hyperedge-crossings-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_hyperedge_crossings.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
The two new prepared-row cases preserve parallel edges inside bundles, skip
same-layer incidences, retain unused position slots, and exercise a later
source bundle surviving a union with an earlier target bundle. The original
and native observers delegate the actual algorithm and retain references to
its bundles; they do not calculate replacement scores. Complete sweep and
dispatcher activation remain separate work.

# Polyomino traversal and fill objects

`polyomino-traversal-*` captures one new original object probe. Run its probe
with `node PROBE PACKAGE REQUEST NEW_OBSERVATION`, then run
`python compare_polyomino_traversal.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
It records the four deterministic successor sequences, same-object quadrant
cache retention after extension mutation, refresh on a different poly object,
normal/external dispatch, strong-cell fill, and actual Polyominoes list/grid
construction. The supplied intermediate cell contents are explicit inputs;
the probe does not execute the common packer or a layout provider.

# RectPacking width approximation objects

Run `node rectpacking-width-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_rectpacking_width.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
Two new ordered-node cases observe real width candidates, filters, shifts,
positions and final DrawingData for asymmetric padding and fractional spacing.
They do not execute the complete packing provider, inject phase defaults or
reuse expected values from native output.

# AllCrossings traversal and dispatch object

Run `node all-crossings-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_all_crossings.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
The new graph uses two actual initializer receivers, parallel edges, an exact
source-port self-loop and a final-row NS dummy. It observes receiver-specific
edge indices, Boolean-to-number flag changes, duplicate incidence metadata,
the shared child-counter buffer and real delegated Hyper/Basic/NS dispatch.
It does not execute a complete minimization sweep or replace scores with
observer callbacks.

# Saved Polyomino corner observations

`python compare_polyomino_corners.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`
provides the first native counterpart of the seven saved original corner
comparator cases. It does not run Node again or execute the common packer.
The real collector ignores its stream item and adds Long one; the original
cases therefore return ordinary corner flags rather than cast errors.

# GraphInfo initialization object

Run `node graph-info-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_graph_info.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
The new Barycenter graph exercises the real single receiver traversal,
single-bit distributor selection, live resolver/rank sharing, copied row
arrays and reference-only snapshot setters. Its internal GRAPH_PROPERTIES
EnumSet default is shared and does not materialize a property. Source-only
cloneability facts are kept separate from native observations. No complete
crossing sweep or forced integer-box parsing is claimed by this object.

# Local swap query objects

Run `node local-crossings-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_local_crossings.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
The new objects compare port and node swap scores, exact collector order,
restored positions, scratch identity and delegated clear/switch order. A third
object checks that UNDEFINED side does not acquire or mutate a cached view.
The DTO explicitly unboxes only the source Pair's two Integer payloads while
retaining its raw boxed observation. No complete minimization sweep is run.

# First complete private DisCo request

Capture `disco-components-request.json` with the existing
`tools/reference/capture_layout.cjs`, then run
`python compare_disco.py PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT`.
This new connected pair and isolated node exercise real component discovery,
edge contour, raster, common packing and coordinate transfer with asymmetric
padding. No underlying provider is selected, so Micro is correctly absent.
The checker preserves raw strict differences and original termination; it
reports source wire parity and finite geometry separately. One private
request does not establish whole-algorithm or public-package acceptance.

# TypeDecider influence objects

Run `node sweep-type-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_sweep_type.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT [CASE_ID]`.
Three new intermediate objects exercise deferred NS propagation, external
paths, the zero-path Infinity decision and 61 live self transfers. The
strategy's non-determinism is an explicit supplied fact. Only declared
NodeInfo Number fields are decoded as binary64 from the original shortest
JSON decimals; raw wire values remain available. This does not run layout or
establish a complete GraphInfo/sweep execution.

# Block and Stack mutable objects

Run `node rectpacking-block-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_rectpacking_blocks.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
Four new objects compare limits after add/remove, simulated versus real row
placement, strict fixed-height search, absolute stack Y, move/expand and IEEE
values after final removal. List identities and all child/row coordinates are
observed. The original objects use the real JsonImporter; this is not a full
RectPacking provider or a replay of earlier Drawing/Row/width cases.

# Complete Barycenter crossing phase

Run `node sweep-phase-probe.cjs PACKAGE REQUEST NEW_OBSERVATION`, then
`python compare_sweep_phase.py PRIVATE_SRC REQUEST ORACLE NEW_REPORT`.
A new K3,3 intermediate graph executes real Barycenter, rank distribution,
Forster, counting, restart/snapshot and final transfer consumers. It records
all score calls, sweep directions, RNG bit requests and both best and last
working matrices. This executes a crossing phase, not full JSON layout.

The separate `sweep-weighted-probe.cjs` and `compare_sweep_weighted.py` use the
same command forms for one weighted-NONE score leaf. Delegated observers
check that the four actual property reads precede AllCounter and its scratch
materialization. No model-order cost callback is substituted.

# Complete private RectPacking requests

Capture `rectpacking-default-request.json` and
`rectpacking-simple-request.json` individually with the existing
`tools/reference/capture_layout.cjs`, then run
`python compare_rectpacking_provider.py PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT`.
The first new request uses real Compactor iterations and the second uses
height/interactive source sorting, SIMPLE and TO_ASPECT_RATIO. Both execute
two real default Micro passes. The checker retains original termination and
strict generated-hash differences, and reports finite geometry separately.
These two paths do not establish fallback, cancellation, full recursive or
public-package behavior.

# Model-order targets and real weighted consumers

`model-order-cost-request.json` is a new working-graph witness with supplied
internal MODEL_ORDER/MAX values. Its original worker observation and
`compare_model_order_cost.py` compare both real pair-cost consumers, the actual
AllCrossings counter, weighted score, target memo identity and port self-cache.
They do not claim complete JSON import or a full layout.

`model-order-targets-request.json` and `compare_model_order_targets.py` cover
explicit LONG_EDGE_TARGET before NORMAL, the first physical branch, reversed
edges, null removal, fresh Integer boxes and an already memoized empty map.
`model-order-feedback-request.json` and `compare_model_order_feedback.py` cover
the real shared-port feedback path, its cyclic/reflexive cache memberships, and
a recursive node-comparator continuation. Membership is projected in input
order; no general hash-set iteration contract is asserted.

Each comparator accepts `PRIVATE_SRC REQUEST ORACLE NEW_REPORT`. The original
`*-probe.cjs`, request, unmodified `*-oracle.json` and command receipt are kept
alongside it. The private-source tree is hashed before and after execution;
strict comparisons retain boolean/number and missing/null differences.

`median-order-*` and `compare_median_order.py` cover the actual Median
constructor and two ordering methods with separate host and seeded random
streams, repeated adjacency, the upper median and the source isolated-node
weight. They do not replay the Barycenter phase.

`two-node-crossings-*`, `greedy-ports-*`, and `ns-neighbor-crossings-*` each
contain one new original object witness and a matching `compare_*.py` entry.
They cover real lazy adjacency cursors and stale cache capture, actual nested
TwoNode costs causing a live reversed WEST port swap, and the separate local
NS-neighbour counter. All observed scoring/swap calls delegate to the real
implementation. Dummy/origin objects in the NS witness are supplied internal
objects, not proof of complete NS layout preparation or Greedy scheduling.

`greedy-phase-{one,two}-*`, `greedy-phase-probe.cjs`, and
`compare_greedy_phase.py` add two source-defined permutation-graph phases.
They exercise actual ONE counted and TWO no-counter strategies through
GraphInfo, Matrix, SwitchDecider, snapshots and final transfer. Recorded RNG
requests and count/sweep sequences remain part of the strict comparison.
These are working-graph crossing phases, not full JSON layout acceptance.

`input-model-sort-*` and `compare_input_model_sort.py` cover the actual
two-pass SortByInputModel phase over a new six-node working graph. They retain
both insertion snapshots, association-cache replacement, all six port
constraints, real edge-target port ordering and eager monitor text. Internal
model-order values and label objects are supplied; this is not a complete
JSON importer, dynamic configuration or Layered layout witness.

`layout-configuration-*` / `compare_layout_configuration.py` and
`algorithm-assembler-*` / `compare_algorithm_assembler.py` exercise the source
object protocols: lazy independent sets, shallow copies, fluent cursor,
ordered creation/configuration, cached nulls and reset/cache transitions.
Assembler callbacks are supplied interface fixtures; no phase layout body or
complete factory registry is certified by these observations.

`canonical-properties-*` and `compare_canonical_properties.py` use a genuine
source importer and shallow property copy, compared with a genuine native
Session snapshot binding. A registered foreign option retains its full source
ID and shared value. The comparator also checks the separately declared native
Integer-token policy. Its first failed candidate and corrected result remain
separate receipts; no source observation was changed for the correction.

`simple-layer-processors-*` and `compare_simple_layer_processors.py` execute
the actual InLayer reordering followed by LayerSize calculation on four new
prepared native graphs. They check original row ordering, first/last vertical
bounds, empty-layer resets, conditional surrounding-spacing reads and object
identity. Geometry is supplied internal input; this is not full JSON layout.

`orthogonal-general-*`, `orthogonal-scalars-*` and
`compare_orthogonal_general.py` retain a new finite working-graph routing phase
with critical splitting, nonzero anchors, external boundaries and a typed
junction chain, plus separate internal numeric leaves. The scalar NaN cases
are source-semantic observations and do not count as valid finite geometry.

`phase-factory-configurations-*` and `compare_phase_factory_configurations.py`
use real default phase constructors and configuration callbacks, covering
static/fresh configuration references, conditional processor memberships and
feedback getter short circuits. No phase mathematics is executed here.

`global-options-*` and `compare_global_options.py` cover actual selected global
configuration parsing and class application. `global-long-key-*` adds one
independent unknown 5000-digit key case using the same probe and checker.
Saved observer corrections and first failed comparisons retain separate
records; `verify_global_options_saved.py` performs data-only rechecking.

`spacings-*` and `compare_spacings.py` retain both nullable 8x8 source Property
matrices, all assigned type getters, individual-node values and graph/layer
fallbacks. Sparse unassigned source cells are represented as null in the DTO;
the first observer failure and corrected source run remain separate records.

`general-constraints-*` and `compare_general_constraints.py` exercise actual
edge reversal and separate-layer hide/restore helpers. Intermediate layer
membership is explicitly supplied for the hide/restore object. The live-cursor
self-loop object supplies hidden nodes and executes only the postprocessor;
it does not claim a complete Layered or self-loop preprocessing run.

`layered-processor-classes-*` records actual class names from 90 real factory
constructions (84 distinct classes). It runs no processor body. The build-only
`generate_layered_processor_classes.py` checks exact source declaration hashes
and emits attributed static logging metadata; runtime code does not read fixtures.

`end-label-sorter-*` and `compare_end_label_sorter.py` compare the actual sorter
over explicitly prepared real LabelCells and label adapters. They retain label
references, list identity, repeated full-graph id initialization and geometry.
This evidence does not implement or certify the cell producer or full layout.

`general-long-edge-*` and `compare_general_long_edges.py` compare actual splitting
and joining of four-layer edges with negative and fractional thickness. Dummy
coordinates and segment bends/junction points between stages are supplied inputs;
the checks cover labels, target adjacency, typed chain references and fresh point
copies, without claiming placement, routing or a complete Layered layout.

