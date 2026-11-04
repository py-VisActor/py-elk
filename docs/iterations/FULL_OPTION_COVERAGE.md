# 243 项选项的证据账本

本账本逐项区分元数据、解析、公共输入、实际分支、状态变化和布局效果。入口是 [option-coverage.json](../option-coverage.json)，不修改旧 compatibility 账本，也不把某个完整输出相等推定为其中每项选项已产生效果。

现有基线包含 243 项官方元数据、306 个解析输入、151 个算法请求及 72 个复杂 Layered 请求。235 项原版可构造属性的有效解析值一致；另 8 项原版自身没有 raw factory，错误结果及消息一致，JS/Python 异常类名差异继续保留。88 个 ID 在两组公共输入中显式出现，这只是输入出现数：其余属性可能通过默认 getter 被使用，不能据此断言未执行。

首版离线映射保留冻结全量执行中的 7 项 E07 空间约束断言，只标记适用范围内的 `scoped_verified`。其余效果、以及这 7 项的其他值和高级组合，均不自动提升。解析默认值、读取成功、配置复制、选中某个类，也不能替代数值或顺序效果；`runtime_state` 与 `layout_geometry` 分开记。

既有 typed 集成材料中的真实 targets/覆盖、Integer 身份、MapHolder 浅复制、链对象别名、默认值物化与 presence 另映射到 15 项 `runtime_state`。这些记录绑定实际原版和候选状态比较，不能当作 15 项布局效果或全部选项取值已验证。

首批新增效果材料来自 33 个真实 `0.1.0` 公共调用，增加 20 个 ID 的具体变化证据，空间效果合计为 27 项 scoped 状态。账本另核 baseline 与 variant 的请求只改变所声明的选项，并从原始 Source/native 指针重新读取变化前后值；两边都必须真正变化且值一致。普通端口的 treatAsGroup 无变化场景仍保留为失败尝试，只有实际 external port 场景提升该限定效果。nodeLabels.padding 的两种已测上下文都无变化，保持未验证，不计入效果通过。

后续 45 个新调用增加 19 个 ID 的效果证据，7 份冻结报告合计 78 个公共调用、39 个新增 ID；加既有 7 项后是 **46 项限定几何效果、15 项限定状态效果**。P4 参数、模型顺序、路由、压缩、wrapping 和 high-degree 的提升均由原始 paired 指针重核。没有可见变化的 NodeInfluence、压缩约束策略及 treeHeight 场景保留 false，不推断选项未使用，也不计入效果通过。

非 Layered 新批另有 52 个正常 whole 观察、32 个严格效果断言，涉及 29 个 ID，其中 27 个是账本新增的几何范围。因此当前为 **73 项限定几何效果、15 项限定状态效果**，不是 243 项全部语义通过。两个 whole 数值微差只按既有坐标容差重核，rawStrict/projectedStrict 原差保留；更严格的 Force repulsion 指针仍不相等、8 个 Source 无效果的场景仍不提升。MrTree BFS 的原始 RangeError 与候选 timeout 单独保存，未计入这 52 个正常结果，也未计入效果通过；后续 active-path 终止修复由独立发行差分证据验证。

```text
python scripts/iteration/option_coverage.py --build --out NEW_BUILD_REPORT.json
python scripts/iteration/option_coverage.py --check --out NEW_CHECK_REPORT.json
python scripts/iteration/option_coverage.py --check-structure --out NEW_CI_STRUCTURE_REPORT.json
```

工具只读取已有材料和声明表，不导入产品、不运行布局、不调用参考引擎。所有证据文件绑定实际 SHA；版本执行仍记 `0.0.1a0`，通过已记录的 version-only delta 关联 `0.1.0`，没有重新标注旧执行。

`--check` 严格重算完整账本，缺少档案时直接失败。随仓库保存的 [options.zip](../../references/full-native-closure/options.zip) 和 [manifest](../../references/full-native-closure/options.manifest.json) 收录账本实际引用的 JSON，逐文件保存原字节与 SHA；所需的 9 个仓库代码文件仅在 manifest 中绑定，不复制源码快照。fresh clone 可以恢复后做完整检查：

```text
python scripts/iteration/option_evidence.py --restore
python scripts/iteration/option_coverage.py --check --evidence-manifest references/full-native-closure/options.manifest.json --root-map "C:\code\py-visactor\py-elk=<CURRENT_ABSOLUTE_ROOT>"
```

把 `<CURRENT_ABSOLUTE_ROOT>` 替换为当前 checkout 的绝对路径。原报告内的旧绝对路径保持原字节；映射只用于解析实际输入路径。没有映射不会搜索旧工作区。恢复前先核全部 archive 成员、SHA、代码依赖和现有文件；路径逃逸、缺失或冲突直接失败，不覆盖不同内容。

`option_evidence.py --inventory` 可先查看清单与大小；账本纳入新报告后用 `--build --replace` 一次增量重建。若在其他 checkout 重建，显式传 `--original-root` 指明报告原执行 root。`--check-structure` 仍保留为较弱的轻量检查：列出缺失 ignored 档案，不重新认证效果。它不能替代恢复后的严格重算。

优先补证家族如下；先找已有真实断言，再对缺口增加最小新输入，不重跑 151/72/306/8+2 整组，也不要求 243 项无穷组合。

| 优先级 | 家族 | 要求的效果 |
| --- | --- | --- |
| 0 | 端口约束、side/index/anchor、边框及标签 | 合法 nested 场景下实际边界、比例、顺序、锚点或间距；不能只检查属性存在 |
| 0 | node/edge label、nodeSize | 给定标签尺寸下的实际容纳、侧别、inline margin、minimum 与约束效果 |
| 1 | considerModelOrder、P3 权重及分组 | 可观察的节点/端口顺序、交叉代价或有明确来源的真实状态；使用有区分度的非零配置 |
| 1 | P4 flexibility/interactive/linear/NS | 实际节点/端口位移、对齐和直线化结果 |
| 1 | Spline/路由选项 | 实际控制点、bend、sloppy factor 等；保留上游日志异常与非有限结果分类 |
| 2 | 层级扫描、wrapping、compaction | 实际尺寸、空白、组件顺序和压缩约束；上游失败不计正常效果通过 |

新增 `pyelk-option-effect-results/v1` 报告可通过重复的 `--effect-report PATH` 合并。每个 `rows` 项包含 `id`、规范 `optionIds`、有 `path/sha256` 的 `request/reference/native`、`comparison.passed`，以及 `assertions`。断言含规范 `option`、`kind`（`layout_geometry`、`runtime_state` 或 `source_selection`）、`description`、原始 `expected/actual`、`sourceDerived` 与 `passed`。还须提供 `referencePointers/nativePointers` JSON Pointer 列表：单指针取该值，多指针取有序值列表；paired 观察可以将真实 Source/native 派生 observables 保存在各自原始记录中再指向该字段。工具核对文件 SHA、独立重算完整输出比较、验证期望和值确实来自对应原始观察，并严格重算 expected/actual 及 baseline 的实际变化后才登记对应层级；不读取布尔 PASS 或 `sourceDerived:true` 来替代数值来源校验。全局报告因个别未证明效果而为 false 时，不丢弃其中真正独立成功的断言。失败或不适用项保持未验证，原始差异不能删除。

已存非 Layered `effectTest.pointers` 协议明确返回有序数组，即便仅一个指针也保持 `[value]`；账本另记 `pointerProjection`，不拆包或修改原报告。旧单 `pointer` 协议继续取标量。新增一个原本缺失的 `layoutOptions/properties` 字典时，字典内全部键必须是该 paired 记录声明的 option ID；其他输入变化仍拒绝。当前 whole 比较工具版本及纯保存 wrapper 修复审计均另绑定 SHA，旧运行没有重绑为新工具执行。

这是覆盖状态与下一步输入选择工具，不是完整正确性证明。完成条件是每个 ID 都有准确的范围与状态；提升某个范围的效果状态必须附真实断言和执行材料。旧原始错误、生成哈希差异、未测分支及 PyPI 发布状态继续分别保留。
