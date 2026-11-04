# ADR0008：真实执行诊断与首版分支覆盖

状态：接口冻结，来源批准后实施；E09-01，2026-11-03。执行目录为 `test-runs/20261103-E09-01`。本决策不构成运行通过、正式发布或完整算法认证。

首个来源子集批准：root 已核 D01–D12 的原始片段、实际调用和独立 V 复审（review-source-monitor-01.json，SHA256 d5e991c612b58649b8c8cc3c0437bc439520f91a173ccc57903c37b5633aa1d5）。这12项仅批准根清理、BasicProgressMonitor/collect、Recursive/Layered/Component 真实调用边界与 Network simplex 子任务的机械移植。BK 日志/数值格式/集合顺序的完整依赖另审；不得把本子集批准扩展到未审 helper。最终可离线来源材料与批准由版本化 source 文档保存。

第二来源子集批准：D13–D39 的 BK 动态日志及 designation/集合字符串依赖已经 V 独立核实，review-source-bk-01.json SHA256 8ba708f980ffefe2fb5ed58cc6623fd3d583420890ff6465991ca1c194da2b66。root 限定批准实际首次成功 add 时旁路保留 fresh 私有 LEdge 的观察顺序，生命周期仅 add 至最终 clear；算法原 set 的 membership 和选择不变，不推论所有 HashSet 都有插入顺序。JS 数字字符串由宿主 intrinsic 生成，elkjs 没有可移植的 formatter 算法；Python formatter 是明确的原创新宿主适配，须独立固定 Node 边界及 roundtrip oracle 验证，不能冒称机械移植或以 candidate 生成 expected。来源批准仍不构成运行通过。

D40 续核真实 LayeredLayoutProvider 的 flat 分支，V 独审 review-source-provider-01.json SHA256 cfbc479c19c3975816a1cbcfc442185d2eccecd5633e3928c4ffba3d4508fd39；root 批准此最小来源补充。非空 Recursive monitor 包含 LGraph import 和 layout transfer，Layered monitor 在 import 后开始、resize 后结束；empty 不进入 provider。Python 融合 JSON/模型传输的宿主边界须明示，外层采集 wall interval 只约束各自真实测量，不声明双方执行成本或计时相等。INCLUDE_CHILDREN 不在批准范围。

几何检查另续核 G01：真实官方 generated-10 的非自环边 n6→n0 两端处于不同 Network simplex rank，坐标轴相距1e-7，旧同层推断因此误报。A 的11固定源片段及 E05–E07 继承经 V 独审接受（review-source-geometry-01.json SHA256 06ff744141375098f39f3d433109c2182957589733bd932c924c84ac6c1b4bd3），root 限定批准独立 v3 premise。GREEDY 可改变朝向、不会合并原非self端点；默认 NS 的单位最小层长使该邻接对 rank 不同，后续默认处理器不合并该对。不推论任意 SCC 内所有节点对不同层，不用候选坐标推导原图前提。仅 E09 新 rankSeparation 采用该引理，旧v2/profile、原请求及容差保持不变，所有其它几何否决仍执行。原始误报和真实 Node 字节封存于 references/e09-geometry-regression.json；第一版未含 EXTERNAL_PORT 实际谓词 callee 的不足已补全后才获批。

## 范围与来源

沿用 ADR0006 的 0–8 个原始子节点、0–28 条原始边、有限非负且不超过 1e6 的给定尺寸及间距、非零 signed32 seed、四方向、平面 directed multigraph 和九项选项。不会因覆盖表新增而放宽算法输入域；端口、独立标签、层级及其他算法仍显式拒绝。首版发布 profile 必须明确这些边界，保留全部基本拓扑；25 个 master 输入逐项登记成功、预期错误或范围外，不能把分母改为成功数。

新增来源限固定 elkjs 0.12.1 的 BasicProgressMonitor、RecursiveGraphLayoutEngine/LayeredLayoutProvider/ElkLayered monitor callers、collectLogs、Network simplex 子 monitor 与 BK 在选择现场输出的日志。A 先交实际 caller/guard/片段及许可证，root 和独立 V 审查后才允许机械移植。E07 的33组件批准保持原状，精确外部 Java 构建仍 unresolved；来源批准不等于算法运行验收。

## 诊断合同

`logging`、`measureExecutionTime` 仅接受 Python bool，省略视为 false。四组合分别为无新树、树及日志、树及计时、树及两者。返回树由真实 begin/subTask/done 调用产生，保持源码名称、顺序和条件；空图、单组件直接复用 Layered monitor、多组件 Component Layout、Network simplex 嵌套以及 BK 动态日志分别实测。不得从 trace 事后拼接树或编造阶段时长。

源码首先清理 root.logging，然后按开关决定是否写入新树。该根字段属于保留诊断字段；嵌套业务字段、root.executionTime、业务对象中的 logging/executionTime 保留并精确比较。只清理返回工作副本，调用方输入仍保持不变；无开关时也执行已核实的根日志清理。

固定生成源使用整数毫秒 `Date.now()`，经过 long 的乘 1000 和差值后再乘 `1e-9`。因此其数值不是通常意义的秒；必须保留发行物的真实换算顺序 `float((end_ms-start_ms)*1000)*1e-9`，不能照 Java 注释猜测单位。Python 默认以 `time.time_ns() // 1_000_000` 取得整数 wall tick，支持测试注入 clock。不要用 process_time CPU 秒、perf_counter 秒、固定0或任意比例替代。源码 wall clock 可能回拨，不无证据钳制为0；比较器应验证结构、数值、真实采集身份和规则，正常实测另核非负与可观察的 wall interval。

旧 native-basic-layered-v1 和原始 strict 比较不变。新增诊断比较策略只允许处理在源码生成树中、由双方实际树结构确定的 executionTime 叶；名称/日志/子树/非计时值仍逐项精确校验，所有业务同名字段必须 exact。原始 strict 差异和两个引擎的原始时长始终保留。计时跨引擎不声明相等，也不伪装成坐标容差。新增策略和 mutation controls 必须独立审查。

## 实现接口及单写归属

显式传递 monitor，不使用进程全局、threadlocal 或 trace 反推。`BasicProgressMonitor(logging=False, measure_execution_time=False, clock_ms=None)` 提供 begin/is_running/sub_task/log/done/collect。`layout_context(..., monitor=None)` 和 network_simplex_layerer/bk_node_placer 的可选 monitor 保留已有调用兼容。处理器的真实调用边界采集诊断，算法选择、数学计算、随机流和坐标逻辑不改。

| owner | 独占文件及职责 |
| --- | --- |
| A | references/e09-diagnostics-sources.json、references/e09-branch-matrix.json、docs/E09_BRANCH_COVERAGE.md、tests/audit/test_e09_sources.py；来源与首版分支，独审 B 实现 |
| B | src/pyelk/execution/diagnostics.py、worker.py；algorithms/layered 下 pipeline.py、phases.py、layering.py、placement.py；tests/execution/test_e09_diagnostics.py；真实 hooks 及单元验证 |
| V | tools/reference/capture_e09_layout.cjs（仅必要时）、scripts/build_e09_suite.py、scripts/validate_e09_coverage.py、tests/fixtures/suites/E09/**、tests/contract/test_e09_logging_contract.py、tests/conformance/test_e09_coverage.py、tests/audit/test_e09_coverage_validation.py、references/e09-coverage-validation.json；官方采集及独立反例 |
| root | scope.py、import_export.py 的 current admission 转发、metadata、公共入口必要集成、E08 历史审计迁移、新同包证据/审计、全局 check、当前声明/许可/文档、计划及最终记录 |

V 另获准仅清理 test_e04_cases.py 的 kernel-only 虚 termination；原算法断言、普通公开 API 的真实 termination 不改。跨 owner 修改先显式转交。所有 agent 不提交/推送，不修改旧原始请求、oracle、容差和旧 profile；复审统一 accepted/blockers/filesSha256。

## 验收顺序

起点完整输入与 immutable baseline-source 已保存；完整基线在该副本运行，使准备及实现可并行。开发按 owner 检查，再进行跨进程和异 root 小正本；同一新 wheel 在仓库外 -I/空 PATH 完成旧181案例回归、新生成/诊断覆盖、真实 API/生命周期。旧 E08 证据仅历史审计，不能认证新 worker。README/METADATA、生产与采集器冻结后才进行大采集，实际执行记录和后验结论另存，避免循环改源码 SHA。

首版 branch→实现符号→固定来源→断言→同一安装包证据完全对应后，才能核验 first-release-coverage；仍缺必需分支时保持 pending。其后最终三平台 full 验证代码/测试及门禁输入，完成记录只走受限元数据收尾。E10 平台/打包、E11/E12 正式发布和独立 py-mermaid 集成不提前声明完成。

本轮复盘分别报告真实新增执行成本、首次失败到修复与集成等待；没有相同分母、顺序实测的对照，不宣称整体加速比例。
