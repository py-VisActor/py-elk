# E13 显式端口迁移准备

状态：E13 仍为 planned。本文件和来源材料是下一阶段准备，不表示当前发行包已支持显式端口。当前产品 `src/pyelk`、README、pyproject 和版本仍由 root 管理；实现先写入 `.local/migration-next` 独立副本。项目自身许可证选择仍 pending，不以准备工作代替该决定。

固定行为源为 elkjs 0.12.1、commit `624ae90aa37110033a8af59c5ccbb292708b4317`，worker SHA256 `275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`。复用既有 33 组件的真实图模型、属性容器、RNG 和数值顺序证明；需要新增支路时补精确来源，不重新审计未改变的全部 helper。精确外部 Java 构建身份仍 unresolved。

## 首个来源闭包

`references/e13-ports-sources.json` 的 `E13-P01-PORT-INITIALIZATION` 包含 `initializePort`、`calcPortSide`、`calcPortOffset`、`LPort.setSide/setNode`、约束/方向枚举和显式 anchor 默认值的固定原字节、行段和 SHA。`transformNode/transformPort` 只作为真实 caller 上下文；其内部 hierarchy、labels 和 inside-connections 分支不因此获批。

移植必须保留这些分支：

- 六种 portConstraints 与五种 side 的真实语义，不能将未实现值静默映射成 FREE。
- 仅当 side 为 UNDEFINED 且约束并非 FREE/UNDEFINED 时从位置推断 side。两个节点维度都非正时保留 UNDEFINED；只有一个维度为零时，保留 JS 的 Infinity/NaN 比较行为，不新增“节点维度必须大于零”限制。
- 显式 borderOffset 为 0 与缺省不同。仅源条件满足且该属性缺失时才推导 offset。
- FIXED_RATIO 保存端口左上角在对应节点轴长上的比例；节点轴长不大于零时比例为 0。
- 显式 anchor 复制后设置 supplied 标志；后续 setSide 不得覆盖它。FREE/UNDEFINED 默认使用中心 anchor，其余已确定 side 使用边界 anchor。
- owner 重新赋值继续遵守 remove-then-append，不能为稳定结果另按公共 ID 排序。

P01、P02、P02S、P03、P04A 和 P04B 已获 V 独审并按 root 有限批准或委托封存，原 proposal 与 review 字节保存在来源记录中。private `ports.py` 已实际移植初始化、side/offset/anchor、side/order 与真实 comparator sort 过程，`graph.py` 新增 supplied-anchor 字段。P01 的 A 十项局部检查和 V 十二项原 Node helper oracle 比较通过；P02/P02S 的 V 八组原 Node helper 比较通过。P03 独立导入/导出已接中央五项 typed options，经两项原 worker 导入比较及实现独审；新入口不调用布局。P04A 的 `node_size.py` 已实现四边端口 placement，九项原 helper 比较通过。P04B 已实现实际 NodeContext/PortContext 数据、真实 Cell/LabelCell 创建、属性继承和 side/volatile-id 排序，完成实现独审及实际 NS adapter 单项反例复核。完整 minimum-size/label 链与真实 pipeline 还未接通。只证明对应 private primitives，不表示端到端或 installed 包支持。每块的来源批准、实现复审、真实运行结论分别记录。

## 后续真实调用链

完整目标是 ports 能力，而不是另造“8 节点/4 端口”等上限来避开分支。已有发行域保持原状，下一副本的缺口必须显式列出，不能将准备中的成功小例子描述成完整支持。

| 阶段 | 固定源入口 | 必须处理的行为 |
| --- | --- | --- |
| 导入 | transformNode → transformPort → initializePort | 原端口顺序、属性/几何/身份、endpoint 连接、node 约束、side/ratio/anchor |
| 准备与方向 | GraphConfigurator、GraphTransformer | 原约束保存、显式 index 的反向变化、position/size/anchor 的镜像/转置、四方向 |
| side/order | PortSideProcessor、PortListSorter | FREE 与固定 side 分支、N/E/S/W 分组、index/position 比较、fixed ratio/position 的顺序、degree 策略及缓存 |
| 节点尺寸和端口位置 | LabelAndNodeSizeProcessor → NodeContext/PortContext → calculators | fixed position/ratio/free、node-size constraints、port-size/margin/alignment/border offsets；labels 与后续 labels lane 协作 |
| 交叉/放置/路由 | 实际 LayerSweep/BK/orthogonal pipeline | NORTH_SOUTH_PORTS 调度、虚拟端口节点、同层边/长边/反向边、自环与显式端口的交互，不能屏蔽 graph flags 绕过 |
| 导出 | applyLayout → applyNodeLayout/applyEdgeLayout → JSON transfer | 原 port local x/y、最终 side、条件性 node final size、edge absolute anchor 和公共输入属性保留 |

PortListSorter 内部还有独立 source comparator，而不是只复用 node-size adapter 的 comparator。必须分别核真实调用、index 缺省行为、相等比较和稳定顺序；已发现源里的 range/reverse 边界不能按通常算法直觉修正。

实际复盘发现：FIXED_ORDER 在两端 index 都存在时比较 index，缺任一 index 时比较 position，因此可以构成非传递比较环。初稿 Python Timsort 在三个混合 index 端口及十端口 REVERSED-degree 两个真实原 Node 案例中不等；旧稿及原结果均保留。最终 P02S 按固定 GWT insertion/merge 的阈值 7、交替缓冲、shortcut 和 equal-left 顺序精确移植，附 Google 2008/Apache-2.0 归属，不以“稳定排序”一般性质替代真实来源。这次修正没有增加“所有 index 必须齐全”或端口数量限制。

P03 的第二个真实复盘是 root 坐标：新 standalone 入口已经接受 root x/y，而旧 bounded export 无条件写 0。原 Node 的 17/29 正本暴露了这个差异；现仅 `original_ports` 模式保留原 root x/y、缺省为 0，空图和非空图一致，旧 bounded 路径不变。未通过禁止 root 坐标来隐藏差异，也未将手动设置的工作图位置冒称真实布局输出。

P04A 初稿把缺省 portAlignment 写成 JUSTIFIED，原 CoreOptions 的真实缺省为 DISTRIBUTED。最初八个显式 alignment 案例没有覆盖缺省，后来通过缺省三端口原 Node 正本定位并纠正；旧稿和失败差异保留，修后为 22/48/74。后续默认值从固定 property 声明和实际 metadata targets/type 逐项提取，不能凭惯例填写。P04B 同时明确 individual-map → graph → default 的继承顺序，不能额外插入直接 node spacing 作为未经源证明的优先级。

P04B 的适配器复盘进一步要求实际 caller 的语义：compound 只由 COMPOUND_NODE 或 inside-loop 激活决定，不额外按 nested_graph 推断。透明标志为真且端口 owner 为 NORTH_SOUTH_PORT 时，原适配器最先返回真实 empty view；该源叶已精确移植，标志为假时不走此分支。其他 PORT_DUMMY 和 SELF_LOOP_HOLDER 隐藏边仍需调用方提供真实视图，未完成时明确 pending，不以原 adjacency 假装完整适配器。

## 在新副本复验

root 将实验源码的基线和增量保存在 `migration/next-native`，通过已有脚本恢复；指定一个尚不存在的新目录，不覆盖当前其他 owner 的工作副本：

```shell
python scripts/iteration/next_workspace.py restore --destination .local/migration-e13-review-01
```

对应已保存的原 worker primitive 输入与观察位于 `tests/fixtures/suites/next-native`。可在恢复出的源码上纯比较已批准的 placement/cell primitives，不重新执行 Node，也不运行完整布局：

```shell
python tools/reference/compare_next_ports.py --source .local/migration-e13-review-01/src --out .local/migration-e13-review-01/ports-review.json
python tests/fixtures/suites/next-native/compare_placement.py .local/migration-e13-review-01/src tests/fixtures/suites/next-native/ports-placement-request.json tests/fixtures/suites/next-native/ports-placement-oracle.json .local/migration-e13-review-01/placement-review.json
```

`compare_next_ports.py` 的默认角色包括初始化 12 项、side/order 8 项、真实 importer 2 项、NS adapter 原叶 1 项，共 23 项；可用 `--role init|order|import|adapter` 只复核受变更影响的部分。脚本重算 private helper/importer 的值，核对已保存原 request/observation/log/probe/worker/source-role 关系和本次源码前后 SHA，不启动原 Node 或完整布局；输出路径须为新文件。该新 runner 的首次 23 项实际 CLI 校验于本批通过，原观察未重采。

复验报告绑定本次读取的源码与原观察；不能把旧 PASS 的源码 SHA 改成当前文件 SHA。实验源码恢复只表示字节身份可重建，不代表端到端、安装包或正式发布已经通过。下列早期 primitive 记录继续保留；后续完整尺寸 process 和原生流水线进展见本页的当前装配说明。

## 新增尺寸计算块的当前范围

P04C 已按独立接受的固定来源实现到 private `node_size_math.py`：真实 fixed-position/fixed-ratio/free 端口最小尺寸、实际 label margin、cell 尺寸贡献、最小节点尺寸、width/height 两阶段。固定比例比较来自 Guava DoubleMath 内联分支，容差为 `0.01`，并保留其独立 Apache-2.0/Guava Authors 归属；不是几何比较器的容差。水平比例路径逐端口重算 margin、垂直路径只在循环前重算，空端口组保留已有内容最小值，固定图大小仍允许内部 cell 矩形与最终节点大小不同，这些源细节均保留。

P04D 已按独立接受的固定来源实现到 private `node_size_cells.py`：真实 21 个 node-label location 及 UNDEFINED、显式空 placement 覆盖、真实 Grid/Strip/LabelCell 与端口区域创建、border-offset/fixed-label 内侧 padding、computed padding 和外侧 label container 定位。它只消费给定 label 的位置及尺寸，不测量文本；写回 padding 保留原对象身份。

这两块分别通过 14 项和 5 项新增定向实现检查。P04C 另外完成了 6 个新独立原 worker 数学 DTO 的严格类型与数值精确对照，覆盖 ratio 邻近阈值、label margin、空组最小值和固定图尺寸等；它们使用真实前置 cells，不等于完整 cell creator 或完整 process 验收。P04C 首轮定向测试曾把两个 outside 端口统一 spacing 前已清除的 margin 误期望为 31；真实为 0，修正了测试预期，首失败保留，生产实现未因此修改。

P04C 的新原始 request/probe/oracle/command 与纯比较脚本保存在同一 fixtures 目录。恢复包含该组件的 snapshot 后，可按变更需要执行纯比较，不重新采 Node：

```shell
python tests/fixtures/suites/next-native/compare_size_math.py .local/migration-e13-review-01/src tests/fixtures/suites/next-native/size-math-request.json tests/fixtures/suites/next-native/size-math-oracle.json .local/migration-e13-review-01/size-math-review.json
```

P04E/F 已按独立接受的来源实现到 private `port_label_placement.py` 和 `node_size_process.py`。前者执行真实 simple/constrained label placement 和 rectangle-strip overlap removal，保留 equal-right-border 集合行为、真实排序及 maxd 的 NaN 规则；后者按真实源顺序编排尺寸、端口、label、padding，并保留 `apply_stuff=False` 早返回。两者新增 5 项和 3 项定向检查通过，随后三个新增原版对象的 standalone process 严格类型与数值对照通过；对应 `node-size-process-*` 原材料及 `compare_node_size_process.py` 可按变更需要复用。它们不代表整套 Layered 或已发布 ports 能力。

Core 的 DISTRIBUTED 缺省与 Layered 的算法级 JUSTIFIED 覆盖必须区分。后续 importer/caller 接中央 typed options 时显式选择 `algorithm='layered'`；单独 Core primitive 的默认正本不能代表 Layered 调用已解析算法覆盖。

中央 20 项 typed options 的 native importer 桥接现已实现：保留 default/algorithm-default/global/local/individualSpacings 来源，individual holder 的 key 保持 canonical ID，Vector2/Padding 复制为独立 Vec2/Insets。新增 6 项桥接检查通过。首检查曾误把 root-local minimum 当作 child 的 global minimum，已改测试为真实 constructor defaultLayoutOptions，原失败保留；没有改变来源继承规则来迎合测试。

## 单写接口

root 已分配 A 独占 private copy 下的 `graph.py`、`import_export.py`、`scope.py`、`ports.py`、`node_size.py` 及新尺寸 helper；后续端口真实接入涉及的 `processors.py`、`directions.py`、`pipeline.py`、`crossing.py`、`phases.py` 也由 A 单写。B 独占 cells 与其他 provider 模块。中央 options/model/context 与通用 JSON host transfer 仍由 root 单写，接口变化先协调。

现有 LPort 已包含 origin、pos、size、anchor 和顺序 adjacency；只需补真实的 `explicitly_supplied_port_anchor=False` 字段，保留旧结构。现有 model 的 `Edge.source_endpoints/target_endpoints` 已提供实际 Node 或 Port 对象，`Port.owner` 已存在，因此不用新增或假定存在 `Graph.connectable` API。

需要 root 冻结的中央 options 接口：按 element/path 取得已选择并规范化的 node-local/port-local typed mapping，保留属性缺省与显式 0/false 的区别。涉及 node `portConstraints`，port `side/index/anchor/borderOffset`，后续 node-size/port-alignment/spacing 等继续按真实 source 支路增加。当前 root-only 九选项 resolver 不能拿来声称这些局部属性已解析，也不能将全局映射随意覆盖每个端口。

import/export 接口由 A 在 private copy 调整：先按源顺序创建全部显式端口、建立 typed origin 映射，再连接边；Node endpoint 仍走真实 implicit-port 创建路径。导出从 origin.path 写回原 JSON，保留业务字段，不用工作图顺序重排输入端口数组。

## 当前原生流水线装配

截至 2026-11-04 的后续增量以 `JsonLayoutSession` 实际 working holder 为入口，新增 `native_import.py`，与早期独立 model 的 `import_export.py` 区分。原始 Node/Port/Label/Edge 通过实际对象身份连接，属性仅复制 present 值及同一 Integer token；canonical 属性 ID 只存一份。原始端口、边数组和最终 JSON 输出仍交由已有 Session transfer 保存。`ORIGIN` 是实际 working 对象，边的当前 container 与初始 JSON parent 也分别保留。

已实现真正的动态配置与装配器、源模型排序、Barycenter/Median/Greedy sweep 及其真实计数器和 ModelOrder 成本消费者。默认主阶段连接新的一般版 Network Simplex、Brandes–Koepf 和正交路由，分别位于 `network_simplex_general.py`、`brandes_koepf_general.py`、`orthogonal_general.py`。这些 body 的独立原版对象对照及代码审核已完成；完整默认入口的整调用仍需另行核实，不用已有五个局部阶段的成功代替。

真实 general layer constraint、尺寸/边距适配器等已按各自独审范围接入 factory。一般版长边 split/join 和非空末端 label cell 分组排序已通过新增独立原版对象与代码验收，并接入真实 handler；原 `long_edges.py` 等受限代码保持原证据。SelfLoop 新 holder 的 pre、port restorer、router、post 四阶段均已按各自来源及新增原对象完成独审；router 在 factory 中绑定一个实例的 `process`，其 director 和 slot assigner 随装配器缓存保留，不在每次调用重建。旧 holder 不参与该新流水线。

`provider.LayeredProvider` 保留有状态 Configurator/Assembler 和 ComponentsProcessor，`do_layout` 按真实源顺序 prepare、split、逐组件执行、清理层、combine、resize；保留取消路径和原 null-monitor 行为。当前 `__call__` 已连接真正的 `FullElkGraphImporter`、动态流水线和 `ElkGraphLayoutTransferrer`，再交已有 Session exporter 输出。outer/external/minimum 具体算法也已按来源实现，但普通与外部分支的实际对照范围分别记录。base spacing 已实现并通过三个新增原对象精确对照，保留显式值不覆盖、默认及 fuzzy 分支和过滤器累积行为。层次导入的三函数来源已独审封存；具体实现和 compound 调度继续分别推进，缺失 body 明确 pending，不采用空回调或旧 bounded admission 来绕过。私有 registry 已接有状态 provider，并由真实 RecursiveLayoutEngine 调用；正式包的公开入口仍未替换。

首个完整私有调用使用一个新的 RIGHT 图：3 个节点、3 条边，其中一条跨层长边，包含给定尺寸并居中的非空节点标签。原版完整 API 仅采集一次；首次 native 整调用揭示 NS 默认 Property 符号错误，同类静态检查又定位到 NS/BK 共 7 个错误 owner 符号，均仅纠正真实 `_0` 名字，数学未改。首败和完整不可变源码副本保留，没有重跑旧阶段矩阵。

修正后的完整调用与已保存原版结果比较：全部几何、标签、折点和完整 19 槽及 BK 日志精确相等。raw strict 仍为 false，保留原版新增的四个形状 `$H` 缺字段差异；仅依据 ADR-0001 的既有规则，对原输入没有 `$H` 且 ID/数组位置匹配的 root/child 做明确四条投影后，整个结果精确差异为零。没有忽略业务同名字段、放宽容差或伪造 GWT 编号。native 输入拥有规则与原版原地回填分别报告；该新场景证明默认整调用接线，不代表全部算法、选项、生命周期或正式包通过。

随后新增一个独立完整自环场景：3 个节点、两条常规边、两个没有标签的自环，seed 37，logging 开启且 timing 关闭。仅采集一次 stock elkjs 公开调用，再执行一次私有 RecursiveLayoutEngine → registry/pool → Layered provider 的首个 native 调用；完整 23 槽日志、节点与两条自环几何、业务字段精确相等。原始四处新增形状 `$H` 差异继续保留，既有投影后差异为零；业务对象中的 `$H: false`、`$H: 0` 仍严格保留。native 完整 input before/after、constructor 和参数保留，缓存检查没有增加布局调用。原版的原地输入回填及 terminate TypeError 分开保存，不冒称两者相同。这次新场景与 factory 增量的 V 独审结果另见本批交付，不重采之前的默认图或重跑旧阶段组。

层次导入已实现为独立 `HierarchicalElkGraphImporter`，并通过一个新的原版 import-only 对象与代码独审：两次 BFS、隐藏节点先记录 model order、跨层坐标来源及实际父子图引用均精确一致。新的 `hierarchical_driver.py` 按源顺序准备各图并消费具体 LayerSweep 屏障；当前已完成源码和代码审核，匹配策略的完整 compound 调度尚待整调用验证。策略冲突错误使用真实 Session 上下文渲染 LGraph，保留初稿缺上下文导致 TypeError 的记录。

`compound_pre.py`、`compound_post.py`、`compound_model.py` 和通用 native `external_port_dummy.py` 已通过两个新的原版阶段对象及代码独审：真实共享端口合并、双向跨层边、三类标签迁移、旧链引用及 junction 空链分支精确一致。对照中的内部位置和折点是明确给定的测试输入，不代表路由或完整布局。新的 hierarchy node resizer 也已通过四个独立原版对象，保留层列表身份、零旧尺寸 IEEE 除法、真实 native LPort origin 和层次 resize 不检查 fixedGraphSize 的源差异；其 factory 仅新增真实 body 绑定，不重复执行这些阶段。

其余四个 hierarchy port handler 已按独审小块落实，独立原对象与代码验收继续推进。一般版方向 wrapper 另在新模块接真实 typed chain、默认克隆和 Integer token 写回，旧 `directions.py` 的范围与历史证据保持原样。compound provider 尚未接通前继续明确 pending；不能用已存在的 scheduler、给定阶段几何或一个默认图将层次、方向和高级标签能力一并标为完成。

后续单写范围：A 负责原生 Layered 配置、import/transfer、其余 layered kernels；B 负责新 `native_adapters.py`、一般版 Network Simplex/BK 和 `self_loops_general.py`；root 负责 Session/中央选项、`components_general.py`、`resize_general.py` 和一般版正交路由。源码恢复和最新进展仍以 root 保存的 checkpoint 与机器记录为准，不能假定正在工作的 `.local` 目录已进入某个历史快照。

## 变更校验与交付

遵守当前变更校验政策，不运行全量或旧三平台大屏障。每个来源块先离线核 source SHA/原字节并独审，再以实际局部输入校验移植行为；小 oracle 由 V 独立采集。针对性检查应覆盖约束、四方向、零维度、未连接/多边共用端口、混合 Node/Port endpoint、显式 anchor、相同/缺失 index 和公共输入保留。

每次交付列明：已批准来源范围、private 实现文件 SHA、真实测试命令和原观察、未实现的调用链分支。最终把新实现接回正式产品前，另由 root 冻结接口、移除不再适用的旧 guard、更新能力声明并执行变更相关校验；全部迁移功能完成后才运行最终全量。


## Batch 17: actual compound caller accepted

The new stock request with two nested sibling graphs and bidirectional cross-hierarchy edges ran once through the private RecursiveLayoutEngine, registry, persistent Layered provider, real compound preprocessor, hierarchical schedule, four hierarchical port processors, postprocessor, transfer and Session export. Original and native root dimensions are 300 x 82; all nested geometry, bends and complete logging agree. The actual source and first native snapshots remain bound in `kernel-handoff-18.json`; independent code and saved-data review is `HOST-17/V/compound-caller-code-review-01.json` (SHA `1a2a2dcb762d64fc56f70e8d919f569deb6b5833d9ef2c45a134d46ac0c604c0`).

Raw strict comparison remains false for seven generated `$H` shape fields. The older shallow projection still reports four nested fields; neither historical result was rewritten. ADR-0011 adds an explicit hierarchy-only saved comparison that validates each subgraph context before projecting source-generated shape hashes. The new saved comparison passes with seven documented adaptations and zero geometry/logging differences. Business `$H` values remain strict. This checks saved bytes and does not rerun Source or native layout.

For a newly saved request/result, use the explicit hierarchy flag only when the request actually contains nested graphs. Keep the raw report beside the projected result:

```shell
python scripts/iteration/check_layered_saved.py --request REQUEST.json --original ORIGINAL.json --candidate CANDIDATE.json --out REPORT.json --project-reference-hierarchy-shape-hashes
```

This new witness completes one real compound consumer path, including its required processors. It does not certify every hierarchy strategy, option, label placement or routing mode, and does not replace the published package. General direction conversion is undergoing a separate new typed-object check; its remaining getter fix and PRE/POST factory wiring have their own evidence. Center-label insertion/removal, switching and side selection remain distinct implementation blocks, with no empty fallback standing in for missing processors.


## Batches 17-18: directions, SPLINES and POLYLINE consumers

The new DOWN whole call, including a long edge and a sized node label, passes complete saved JSON and logging comparison at 74 x 144; `kernel-handoff-19.json` and its separate acceptance supplement bind the actual Source/native snapshots. General GraphTransformer getter tests separately preserve the initial physical-null index failure and the corrected default handling. PRE and POST use the original Source modes, including their counterintuitive names.

The first distinct SPLINES stock request with logging enabled throws an upstream `TypeError: java.lang.NullPointerException` during `collectLogs` conversion of a null task name. That raw observation remains a failure. The initial native runner rejected the throwing reference before calling the layout engine; its `attempt-scope.json` records zero actual engine calls. A separate minimal two-node single-edge request with logging and timing explicitly disabled returns, and its first actual native RGE call agrees at 118 x 50. `kernel-handoff-20.json` binds this limited positive witness, the retained upstream failure, and the persistent SplineEdgeRouter/Final instances. Final retains the Source behavior of not touching its monitor. No logging-enabled full SPLINES success is claimed.

A new POLYLINE three-node/three-edge long-edge request with logging enabled also passes its first Source/native comparison at 198.26666666666665 x 64; `kernel-handoff-21.json` and its independent acceptance supplement bind all inputs, snapshots and logs. Source-generated shape hash fields remain visible in each raw false comparison before the existing explicit projection. No earlier whole-call or prepared-object success was replayed for these factory changes.

Center-label work is split into actual insertion/removal, the six-strategy stateful switcher and the six-mode side selector. Insertion/removal has independent new RIGHT/UP object evidence and code acceptance. Switcher and selector source closures are approved, and their new implementations await their own independent object/code checks; they are not registered as completed pipeline processors. The physically null strategy correction preserves the first HAS holder while GET reads its own declared MEDIAN_LAYER default, rather than the graph-selected alternate default. Both original and correcting source reviews remain available.

The fixed compiled label-manager callback and endpoint-label postprocessor have separately approved source scopes. Their new implementations are still separate from factory registration and whole-label conformance. Manager targeted controls check absent/null success and rejection of false, zero, empty string and empty list, preserving begin-before-failure without done. The first harness construction failure is retained. End-label preprocessing source covers real cells, four sides, overlap removal and margin updates; implementation waits for independent approval. No empty callback or bounding-box approximation substitutes for these steps.


## Batch 18: selected strategies and nonempty labels accepted

The new LONGEST_PATH and LONGEST_PATH_SOURCE strategy-selected whole requests agree with their first stock observations, producing 238 x 102 and 242 x 100 respectively on an unequal-depth DAG. A new DEPTH_FIRST cycle-and-tail whole request agrees at 246 x 59, including the Source-general reversed-edge restorer; its legacy finite-vector helper remains unchanged in the old module. A new SIMPLE placement whole request agrees at 134 x 104. The distinct calls, raw generated-hash differences and independent caller acceptances are recorded by `kernel-handoff-22` through `kernel-handoff-24`, each with a separate `-review.json` supplement. No prepared or earlier whole-layout success was rerun.

The complete end-label and center-label chains now also have actual new whole-call witnesses. A fork with four nonempty HEAD/TAIL labels agrees at 180 x 98; a four-node backbone and long edge with two nonempty CENTER labels agrees at 250 x 93. Comparison includes all label geometry, routing, complete logs and input/business data. The original raw false comparisons retain four and five generated shape hash fields respectively. `kernel-handoff-25.json` binds the exact shared immutable 191-file source snapshot and separately reviewed processor bodies; its acceptance supplement binds V's saved-data/caller review. Actual manager selection was false in both configurations; registering its true callback does not claim that it executed.

The six-strategy switcher and six-mode selector have their own independent new object evidence. The selector's original negative-small-value ceil produced positive zero; the source-correct helper now preserves negative zero, with the original implementation, targeted counterexample and all earlier successful captures retained separately. End-label pre/post also passed two independent prepared directions using actual cell producers, rectangle overlap removal and in-place margin updates. These processor results and the two whole calls are separate evidence scopes.

Current factory wiring enables only the individually ported bodies. Other Layered phase variants and advanced combinations remain explicit pending entries; the selected whole calls do not certify every option, routing/strategy combination or the public Python package. Comment processor source preparation is the next isolated block and has no implementation or runtime acceptance yet.
