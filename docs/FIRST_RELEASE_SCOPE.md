# 首个正式 Python 包：基础版范围与门禁

当前[完整实现已整合并进入统一校验](FULL_NATIVE_IMPLEMENTATION.md)。本页保留基础版发行门禁；旧“仅受限切片”的状态按其历史日期理解。正式发布及下载复验仍待执行，不能用实现接线或本地包替代。

按当前需求，先交付可独立使用的基础 py-elk 并发布正式 Python 包；py-mermaid 集成是之后的独立步骤，不能阻塞首版发布。
计划首个公开版本为 **0.1.0**（无 alpha/rc 后缀）；当前本地 `0.0.1a0` 已有受限真实ELK实验切片，尚未满足正式发布范围。
PyPI 发行名为 `py-visactor-elk`，导入名仍为 `pyelk`，GitHub 仓库仍为 `py-elk`。旧发行名因 PyPI 相似名称限制被拒；用户已配置新名称的 Trusted Publisher。真实发布和下载状态见 [发行记录](releases/0.1.0.md)。
具体执行为 [ITERATION_PLAN](ITERATION_PLAN.md) 的E01–E12，方法见 [Python实现策略](IMPLEMENTATION_PLAN.md#2a-python实现策略)。实现轮次完成仍须满足本页门禁，不能用规划或实验性切片替代正式验收。

## 首版最低可用范围

| 维度 | 首版目标 |
| --- | --- |
| 入口 | 可独立 `from pyelk import ELK`，真实 `await elk.layout(graph, args)`；元数据查询只返回已实现范围 |
| 算法 | 真正原生 Python layered，默认值/策略按 elkjs 0.12.1 的已冻结首版路径 |
| 图模型 | 单层 root/children、字符串 ID、调用方给定有限非负节点尺寸、单源单目标 extended edges，保留业务字段 |
| 基础拓扑 | 空图、单点、链、分叉/汇合、菱形、长边 DAG、环、自环、多边、非连通及不等尺寸节点 |
| 几何 | 四方向、padding、同层/层间/分量间距、component 处理、正交 routing/sections、根尺寸与正确坐标回填 |
| 配置 | 标准完整 ID 和 `elk.*` 别名、构造默认与调用级替换、元素覆盖；9 项核心选项见机器清单 |
| 行为 | 输入不被意外污染、错误类别/字段路径明确、seed/顺序稳定；公开的 async/关闭/并发限制有实测契约 |
| 平台 | CPython 3.11–3.14，Windows/Linux 的真实 wheel/sdist 安装与布局；以实际通过矩阵声明支持 |
| 运行依赖 | 不调用 Node/JVM/浏览器/JS 解释器、参考源码或其他布局后端；不依赖 py-mermaid/Canvas |

首版 9 项选项：algorithm、direction、padding、spacing.nodeNode、
layered.spacing.nodeNodeBetweenLayers、separateConnectedComponents、spacing.componentComponent、edgeRouting、randomSeed。
edgeRouting 首版只声明已验证的 ORTHOGONAL；其他路由模式不能静默替换为它。
精确 ID/枚举/默认值/适用输入和可调用子集在 M1/M3 冻结；没有证据的分支不得纳入首版支持。

E09 按 [ADR0008](decisions/0008-e09-diagnostics-coverage.md) 明确首版受限输入域：0–8 个原始子节点、0–28 条原始边；给定尺寸、间距和 padding 不超过 1e6；seed 为非零 signed32，省略默认1。上述全部基本拓扑均保留；预先存在的根/节点坐标、边 sections 等几何字段仍显式拒绝。更大图和新数值支路须续核来源后另行扩展，不将当前有限验证声明成无界兼容。机器边界见 [release-profiles.json](release-profiles.json)。

日志/计时的 true 和 false 四组合属于本轮必需分支。日志必须来自真实执行 monitor；根 logging 是保留字段，在返回副本清理或重建，嵌套业务同名字段保留。固定 elkjs 的 executionTime 使用整数 wall 毫秒差乘1000再乘1e-9，不能按普通秒或CPU时间解释。几何比较仍使用原容差，诊断树只对源码生成的计时叶采用单独的时钟规则；原始 strict 差异保留。

## 独立后续范围

端口及端口标签、独立节点/边标签布局、compound/跨层级边、primitive edges/hyperedges、
更多 layered 策略/选项/路由和其他 11 个算法放到 M6/M7。
首版遇到会改变布局却未支持的这些能力应明确失败，不能忽略字段、换算法或返回原坐标冒充成功。
已知业务元数据的无损保留与 ELK 语义字段的支持检查分开处理。

全量目标仍保留 12 算法/243 选项/8 类别及完整 API/跨领域分母；基础版发布不等于全部 ELK 兼容。
py-mermaid 的适配、上层案例与 Canvas 输出只在[独立集成步骤](MERMAID_INTEGRATION.md)验收，不进入首版发布门禁。

## 正式发布门禁

1. M1–M3 的首版输入/策略/选项/错误断言全部通过；原始官方输出和 Python 差分保留。
   声明坐标兼容的分支满足既定 `abs_tol=1e-6` / `rel_tol=1e-9`；semantic-only 原型不算正式兼容验收。
2. 真实可运行例子、公共类型/API、支持矩阵、限制、资源上限和基本性能结果完整。
   不靠样例数、方法存在或空图返回证明能力；加入故意破坏几何/默认值/错误的负控制。
3. 新构建的同一候选 wheel/sdist 在干净环境、仓库外 `python -I`、无 Node/JVM/浏览器 PATH 下执行真实布局；
   骨架 import 只证明打包，不满足此门禁。
4. 项目发行许可、移植源码/版权与第三方通知闭环；名称/账号发布权限、版本和最终包内容已核对。
5. M5 上传真实 0.1.0 候选、核查 PyPI 页面/metadata，重新下载核 SHA 并再次安装/布局；记录发布 URL 和结果。

用户已明确正式包发布目标；到执行阶段应先准备可审阅的真实候选与上述证据，再处理必要的名称、许可、账号或凭据输入。
当前已有E03宿主基础及E04–E07受限真实四方向/多组件/多重图布局与安装对照，完整基础功能/API/生命周期/许可/发行门禁仍未完成；不能把实验切片上传当作正式0.1.0交付。
