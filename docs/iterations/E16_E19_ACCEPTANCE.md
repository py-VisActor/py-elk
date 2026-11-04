# E16–E19 明示退出条件核对

这是既有保存材料的离线核对，不改变机器计划、选项账本或发布状态。

| 批次 | 独立算法 | 结论 |
| --- | --- | --- |
| E16 | fixed, box, random | met_scoped |
| E17 | mrtree, radial | met_scoped_with_numeric_diagnostics |
| E18 | force, stress | met_scoped |
| E19 | disco, sporeOverlap, sporeCompaction, rectpacking | met_scoped |

“met_scoped”表示明示能力已有真实、限定输入/数值政策的证据；不表示无限输入或所有选项值已穷尽。
E17 原七个有限声明缺项已由新的真实 prepared phase/factory/evaluate 见证补齐；两个长度目标保留内部数值诊断，不宣称全标量 exact。

| 条件 | 状态 | 证据及范围 |
| --- | --- | --- |
| E16-provenance-metadata: Three separate implementations/provenance/metadata/applicable options | met_scoped | Fixed, Box and Random each have a fixed Source inventory, distinct public calls, typed parser/accounting and actual published runtime modules. Registered/parsed options are not full effect coverage; frozen ledger preserves all unverified options. |
| E16-fixed: Given geometry, transfer, options, inputs/errors, coordinates | met_scoped | Fixed supplied geometry, sizes/minimum/ports/labels/bends/junctions and missing-section Source error have individual calls. No claim that Source error paths are successful geometry.  |
| E16-box: Packing and independent options/positions | met_scoped | Four packing modes, priority/interactive/expansion/minimum cases and independent SIMPLE/GROUP_DEC containment/nonoverlap predicates exist.  |
| E16-random: Random stream, coordinates/seed, input and entropy boundaries | met_scoped | Seeded and negative-seed/edge/port paths have deterministic coordinate witnesses; unseeded case remains NONDETERMINISTIC_OBSERVATION. No V8 entropy trajectory equality or nonoverlap guarantee. |
| E16-performance: Per-algorithm performance evidence | met_scoped | Each of the three has actual n8/32/96, warm1/formal5 wall/OS CPU/memory observations. Windows CPython3.13 only, pre-MrTree-repair 0.1 payload; no all-platform or universal resource bound. |
| E17-tree-semantics: Forests/roots/levels/subtrees/directions/non-tree input | met_scoped | Zero/one/many roots, DFS/BFS cycle/parallel inputs, depth/subtree state, asymmetric directions and prepared routing have saved assertions. Cyclic sibling path now fails promptly under an explicit native policy; legal revisit/deep chain remain valid. Source RangeError and native RecursionError are different and are not declared exception parity. Independent depth-band predicate applies to a simple unique-rooted tree with compaction=false. |
| E17-radial-semantics: Circular/radial geometry and non-tree semantics | met_scoped | Default and explicit radius have independent depth-ring/minimum-increment predicates; compactor/sorter/wedge/rotation cases retain their Source outcomes. WEDGE/POLAR/rotation has an upstream nonfinite wire observation, not valid finite geometry PASS. No assertion of radial rectangle nonoverlap or an exactly depth*radius formula. |
| E17-declared-branches: All declared branch differentials | met_scoped_with_numeric_diagnostics | Seven formerly unmapped values now have actual prepared phase/factory/evaluate witnesses, supplementing the existing public calls. Final geometry/control/chosen offset match exactly. These seven are actual private prepared phases, not seven new public whole-API calls. Two length objectives retain 11 exact scalar differences (maximum2ULP). Source/native expression/accumulation order matches; precise libm primitive cause is not proven. No profile/tolerance upgrade. |
| E18-initialization-iteration: Initial values/seed/iterations/convergence/termination | met_scoped | Both Force models, supplied interactive coordinates, seeded initialization, Stress X/Y/fixed/edge-length/epsilon and iteration limits have real calls/effect assertions. Force/Stress iteration1/25/150 quality and real host CPU timeout/recovery are measured. An epsilon causal final-geometry assertion does not reveal the exact inner-loop termination iteration. No Force monotone-stress claim or unconstrained-input termination theorem. |
| E18-numeric-quality: Pointwise error/resources and independently decided numeric profiles | met_scoped | Saved whole-result pointwise differences and strict effect pointers remain separate; existing coordinate1e-6/1e-9 policy was not widened. Quality includes overlaps/edge lengths/normalized graph stress and actual worker resources. Force repulsion strict effect parity remains unverified where a small floating difference exists; not silently promoted. Normalized shortest-path stress is a descriptive metric, not every algorithm objective. |
| E19-separate-providers: Four algorithms separately accepted with actual dependencies indexed | met_scoped | Each has its own real public calls/performance rows/module; Source index records shared triangulation, polyomino, typed state, generic margin and optional underlying-provider dependencies.  |
| E19-disco: Components/shapes/input positions/constraints/quality | met_scoped | Inter-component leaf-rectangle separation and component-spacing effects are witnessed; component interior layout is preserved unless a real underlying algorithm is explicitly invoked. Interlocking component bounding boxes may overlap; no false bbox-separation or packing-optimality requirement. |
| E19-sporeOverlap: Overlap removal, initial positions, objective/constraints | met_scoped | Real initially overlapping geometry, cost/update/transfer object assertions and scanline-enabled independent no-overlap/containment predicates exist. Scanline-disabled observation is NOT_ASSESSED by that independent predicate; no all-option overlap theorem. |
| E19-sporeCompaction: Compaction, initial positions, objective/constraints/quality | met_scoped | Distinct contraction provider, original/working-coordinate and numeric objective transitions plus actual public effects/performance are saved. ShrinkTree is not an overlap-removal guarantee; no demand for universal area decrease or global optimum. |
| E19-rectpacking: Packing strategies/objectives/constraints/quality | met_scoped | Real packing provider, strategy/target-width/optimization effects and independent COMPACTION/SIMPLE containment/nonoverlap predicates exist. NONE placement is not asserted nonoverlapping, no packing-optimality claim. |
| cross-release-boundary: Current deliverable, host lifecycle and actual payload identity | met_scoped | Actual uploaded/downloaded 0.1.0 wheel runtime208 equals current src; actual Windows wheel/sdist and Linux wheel observations bind imports196/metadata12,243,8 and real20node calls. Historical source/native/performance runs retain their executed source hashes and are not relabelled as published-package reruns. E12 publication is complete separately; E20/E21 all-branch acceptance is not implied. |

## 必要剩余项

| 选项 | 值 | 状态 |
| --- | --- | --- |

本次明示有限见证缺项为0；这不等于243选项或无限输入组合完成。新增七个是私有准备对象中的实际 Source/native phase，不能冒称七次公共API整调用。
EDGE_LENGTH 内部9个目标值最大2ULP，BY_POSITION内部2值最大1ULP；全部最终节点/控制状态和所选角度index exact。原数组差异仍 exact=false，不调容差/不升profile。
两个实现公式和顺序一致，但保存的总和不足以唯一定位三角函数还是sqrt的宿主舍入；EDGE_LENGTH最优/次优仅隔2.84e-14，不外推任意近似平局稳定。

数值边界决定见 [ADR0016](../decisions/0016-radial-private-objective-observations.md)；既有严格失败不被改成标量通过。

## 新补证与边界

- 原39个性能配置：195次正式、39次预热，另6次 Force/Stress 迭代质量观察；实际 Windows/CPython3.13，旧执行字节不回绑发布包。随后仅发布版 MrTree 追加3配置/15正式/3预热，其 wheel SHA 及208运行字节严格等实际发布包；其余36配置的算法字节未变，未重跑。
- 独立几何14个请求、Source/native各14：20个 PASS、8个 NOT_ASSESSED，无已适用谓词失败；本工具重新从冻结 options.zip 的原始 JSON 求值。
- MrTree 源 RangeError/旧候选不终止保留。active-path 修复明确返回 native RecursionError；合法8node、重复child返回后再访及1500深链回归独立保存。
- Force/Stress 逐点差异、严格效果与既有坐标容差分开；Force repulsion 的严格效果未证保持原状。Stress epsilon 已有因果几何变化，不凭耗时猜具体终止迭代。
- SPOrE 原始/工作位置、cost/update/transfer 准备对象和真实整调用互不混称；SporeCompaction 无移除全部重叠的承诺，DisCo 不要求 interlocking 组件包围盒互不交叠。
- 发布 wheel 的208运行文件逐字节对当前 src 重核；Windows wheel/sdist 和实际 GitHub Linux wheel 安装范围分别保留。发布成功只关闭独立 E12，不关闭 E20/E21。

## 复核方式

`python scripts/iteration/e16_e19_acceptance.py --check --root-map C:/code/py-visactor/py-elk=.`

纯读保存证据及独立几何求值，不导入 pyelk、不运行 Source/布局/安装/性能。严格核对需要 JSON 内引用的保存文件；缺失/SHA错误直接失败，不借原工作区隐式外援。
所需 ignored 原材料原字节位于 `references/full-native-closure/algorithms.zip`，成员及SHA由同目录 `algorithms.manifest.json` 明列；已跟踪文件仍直接读当前repo并核SHA。archive成员即使原test-runs存在也只从zip读，不依赖旧工作区。

完整证据路径/SHA、逐算法调用、精确 JSONPointer、条件结论见 [E16_E19_ACCEPTANCE.json](E16_E19_ACCEPTANCE.json)。
