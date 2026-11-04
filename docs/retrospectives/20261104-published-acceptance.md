# 已发布实现的增量验收复盘

## 交付与验收

`py-visactor-elk 0.1.0` 已实际发布。当前工作保持产品源码和发布 tag 不变：E16–E19 有逐条件清单及便携原始证据；Radial 私有目标数组的 11 个严格尾差单独保留。发布版 MrTree 只追加 8／32／96 节点性能测量，15 个正式样本及 3 个预热全部通过，不重跑其他 36 个性能配置。

[高级几何](../ADVANCED_GEOMETRY.md)新增独立约束及负控制。实际增量是 24 个公共结果、4 个已执行的 LabelCell 状态及 154 项新或新具检错能力的检查；14 个公共结果仍 PARTIAL。旧 142 个观察及 Source 执行身份保持不变，不将几何成立当作无限组合或坐标全通过。

本批分支矩阵的 90 个核心 factory 已分类；补充的 121 个枚举值分别保留 68 个 helper／body／effect 限定见证、1 个 TOP_LEFT consumer 状态、1 个 NONE scheduler 排除见证，以及 51 个尚无 variant 见证。NodePromotion 新 9 个实际 body 都有正常状态结果；其 NONE 仅证明不调度，未调用 body 冒充空操作。内部 IMPROVED 后备路径及 NODECOUNT 末端 cap 没有由这些观察升级为通过。

## 并行执行

| 角色 | 独占交付 | 协作接口 |
| --- | --- | --- |
| A | 高级几何脚本／测试／真实 fixture；随后接手有限分支矩阵与 branches 归档 | 先冻结几何，再顺序集成 B／V 的原始状态指针，避免两个任务同时修改同一文件。 |
| B | 最小缺失 owner DTO 和 NodePromotion 家族实际调用，先写 ignored 交接材料 | 按 consumer 家族合批；保留首败和类型修复；NONE 使用真实 scheduler 决策，不能伪造 body no-op。 |
| V | 独立读取现有证据、逐条件清单及对应便携归档 | 将 helper、prepared phase、公共调用分开；缺失值不由输入字符串或汇总 PASS 补齐。 |
| Root | 机器状态、增量性能工具、文档、变更检查规则和最终 Git 集成 | 检查文件 owner／归档闭包后集成；不编辑仍由 agent 持有的文件，不重建未变发行包。 |

## 问题与改进

变更检查原来将整个 `references/full-native-closure/**` 交给选项归档消费者，导致新增 branches／algorithms 也选择无关的选项恢复与校验。现改成显式归档路径；新增 geometry-contracts 也只选择高级几何检查。四个纯 CI 测试通过，包括分别验证三个归档的消费者和未知路径停机。此处证明检查选择范围缩小，不宣称未经测量的整体提速比例。

对 Git clean filter 另做了 450 个直接依赖的字节检查，未发现会在提交时改变的原材料。给 SHA 绑定的 ITERATION_PLAN 和 M7 JSON 保留原字节，避免工作区通过而新 checkout 失败。旧证据不能改 SHA 来适配当前脚本。

独立几何复用保存结果，新增 Source 调用只用于确实不存在的公共样本或分支状态。数学矩阵、跨平台和安装证据按各自执行版本保留；变更检查工具及文档不触发全量布局。

## 下一轮

按原退出条件完成 E13／E14 清单，将剩余 Layered 枚举按消费函数合批收口；E15／E20／E21 继续进行。所有缺项、Source 边界、严格差异和未评估项保留终态，不能由首包发布或核心 factory 全分类推导全部验收完成。py-mermaid 集成继续单独后置。
