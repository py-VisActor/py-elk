# E16：fixed、box、random 原生迁移准备

本批在 `.local/migration-next/src/pyelk` 的隔离副本推进真实 Python 实现。E11 主 `src`、版本、README 和发布候选保持由 root 管理。只运行本次变更的来源与定向比较；没有全量或旧矩阵重采。

## 实施顺序与归属

B 独占本文件、`references/e16-basic-sources.json` 与隔离副本 `algorithms/fixed.py`、`box.py`、`random.py`。root 管理共享模型、选项/注册、递归引擎及最终集成；V 独立审来源，并用固定官方 worker 构造与采集原请求和输出。每个闭包独审后立即实现，不等整个 E16 审计结束。

1. fixed：先核 provider、resize、port/label、edge section/bend、junction 的真实闭包，随后移植并比较。
2. box：核四种 packingMode、priority/interactive 顺序、expandNodes、contentAlignment、minimum-size 与边界；逐模式移植，不把 SIMPLE 当全部算法。
3. random：核显式 seed 和 seed=0 入口、真实随机流消耗、参数数值语义、节点/边路由及端口分支；复用已审 PRNG，并保留固定版本可观察到的行为。生成源 `$floatValue` 是 identity，不擅自将用户值降为 float32；仅原默认常量保留其真实十进制值。

目标包括各算法适用的完整选项和输入能力。共享模型尚缺的能力明确交接，未实现或未对照的分支标 pending；不新增任意 8 节点限制，不用更小支持域冒充完整迁移。

## 宿主与 provider 接口

`layout_fixed(graph, options=None, *, monitor=None) -> new_graph`，另外两个 provider 使用同形接口。provider 执行已审来源的数学与有序处理；不运行 JavaScript/JVM 或调用其它布局后端。传入 JSON 图保持不变，返回独立图。

中央宿主负责原图克隆、导入默认值、布局属性解析及生效规则、层次/递归调度、错误与生命周期、导出身份与业务字段保持。provider 只负责一次父节点布局调用，不能自行重复递归，也不能把原始 `layoutOptions` 改写成内部默认/临时属性。初期独立 raw-JSON 适配仅用于核实真实数学，不代表中央 import/export、所有选项语法和公共 API 已集成。

fixed 的 `resizeNode_1` 会移动端口和标签，并清空内部 size constraints；这个内部副作用应与调用者原始选项分离。IEEE754 除零、NaN 比较等应按固定源真实分支处理，不能加无来源的钳制或“修正”。

递归集成必须跨 provider 保留内部 property 状态：子图 fixed resize 清除的 constraints、推导出的 `port.side` 不能在父图 box 调用时因重新从原 JSON 建状态而丢失。隔离 `_State` 已分别保存 `cleared_constraints` 与 `computed_options`，root 已冻结每作业一个持久 State。三个模块均提供 `_layout(state, node, monitor=None)`，中央递归直接调用该入口；`layout_*(graph, options, monitor=...)` 继续保留独立克隆 wrapper。不能把原始 `layoutOptions` 当成当前内部属性。

此抽取保留 box/random 数学主体的归一 AST 相等；只重核三核原始代表，未重跑已有 17 项。另以独立官方 child-fixed→parent-box 原请求实际验证同 node/port 对象、约束 clear 与推导 side 跨调用保留：c=190×80、port=(190,5)、父图245×110。原选项与调用者输入未变，完整 strict 导出差异仍留存，见 `B/state-interface-smoke-01`、`B/persistent-state-01` 及各命令日志。

## 首批来源事实

固定基线为 elkjs 0.12.1，`lib/elk-worker.js` SHA256 `275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`。逐组件行号、LF span SHA、原内容与依赖见来源 JSON 的 F01–F14。固定 npm 声明及 Java v0.12.1 可读文件分别保存许可证据；可读 Java 仅作交叉理解，不冒称已解决生成 worker 的外部构建身份。

fixed 并非 no-op：position 会改节点/标签/端口位置；子节点 minimum resize 仅在有 position 时走；边 bend-chain 可生成 section；ORTHOGONAL 真实计算共享端口 junction；父尺寸含 padding，但不无条件平移所有子节点。源中多 section 的错误分支按官方实际观察保留，不凭直觉修补。

## 验证与交接

V 的官方原始请求/输出定义 expected。首先对 positioned fixed 的最小真实路径比较，然后扩展每个实际 guard 与 helper 分支、层级/端口/标签/sections，保留首败和完整差异。基础数学、原数据保持、错误行为、几何及宿主生命周期分别记录，单个样例通过不代表全部算法/选项等价。

本批运行目录为 `test-runs/20261104-E16-01`，B 输出在其 `B` 子目录。fixed 首来源提案 `B/fixed-first-proposal.json` 保留原字节；来源接受、实现状态及后验测试放各自收据，不把测试 PASS 反写成源码事实。

## 已进入隔离副本的实际代码

来源 JSON 的 `implementationState` 保留最初提案时的快照，不是当前完成声明；当前隔离实现进度看本节及原始运行收据，最终能力状态仍由 root 的机器计划决定。

fixed 的一次 provider 调用已实现节点/端口/标签位置、minimum resize、section/bend 与真实 junction 处理。V 的 6 个分支原用例已逐一对照：返回图的几何及业务字段吻合，缺 section 的官方错误亦实际触发。完整 strict 差异仍保留 `$H`、container、section id 和 shape 引用等待中央导出；公共错误分类也待宿主映射，不能写成公共 API 已等价。见 `B/fixed-branches-03/report.json` 与原命令日志。

box 的四种 mode 均已真实实现，包括 source priority/interactive/面积稳定排序、真实 sample 方差、micro-resize、expand、内容平移与 GWT PQ 相等面积 tie 顺序。SIMPLE 首例见 `B/box-simple-smoke-01/report.json`，随后三 GROUP、priority/interactive、两种 expand/minimum 及非整数参数的独立官方请求见 `B/box-random-branches-01/report.json`，数值相等而中央导出差异仍完整保留；没有用 SIMPLE 回退其它模式。

random 的一次 provider 调用已移植节点和边随机流、hierarchical 判断及实际 seed-zero wall-clock 入口。显式 seed=7 首例见 `B/random-smoke-01/report.json`；随后 edge/asymmetric padding、port source、负 seed 官方样本见 `B/box-random-branches-01/report.json`。未改变共享 `phases.JavaRandom`；显式 seed 的可比几何与 seed=0 的实际不确定结果必须分开验收。该进展不代表所有语法、所有分支、递归或公共注册已完成。

seed=0 的实际采样见 `B/random-unseeded-01/report.json`：只旁路观察真实无参 constructor，原时钟未覆盖，原 constructor 原样委托；所用 seed 在实际 OS wall-ms 窗口内，process counter 真实递增。对官方独立 seed-zero 原观察只核确定尺寸、有限采样范围及输入保持，随机坐标的 strict 差异完整保留，不声明黄金坐标相等。

PQ 新适配保留 Google 2008/Apache-2.0 归属；无参 Random 也扩展了原 notice 所述 seeded-only 范围。这些变化在隔离模块中保留明确 SPDX 与说明；正式并包前由 root 补齐 NOTICE，不修改已冻结 E11 候选。
