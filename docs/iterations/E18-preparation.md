# E18：force / stress 原生迁移准备

当前交付补记：F01–13/S01–08 及向量支持闭包已分块独审接受，F04 由 root 独立审核，其余由 V 审核。原始提案、每块审核及最初失败分别保留，不把新 canonical SHA 绑回旧执行。

私有 `force.py` 已实现真实图导入、组件、Eades、Fruchterman–Reingold、共享 RNG 和回传；`stress.py` 已实现真实 Force 初值、Dijkstra、可变比较器优先队列和顺序 majorization。两者使用同一个持久 Session，默认路径调用真实 NodeMicro。源码 SHA 分别为 `ac02bbf04bae1d62e8db492091da63b9fa0ac59c703d2d2a566ff310605e9f30`、`e214e3c0bdd08cb772e2037b4d0d7e4fdc05b3a2e8efc421af53163d566bcb33`，当前冻结。

V 独立先采原 Node 四例，再对两核各比较两例：Eades 加权、端口、标签和 repulsive bends；FR 三组件共享 RNG；Stress interactive X、fixed 与 edge 长度；非 interactive Force 初值后 Y。数值与业务字段全部 exact，原始 strict 仅生成 `$H` 差异保留。`V/force-stress-code-review-01.json` 已接受此具体实现闭包，不认证全部公开选项、递归调度或安装包。原 Node terminate 的 TypeError 保留，不称生命周期通过。

同一新增 Stress 非交互原例的 cycle 标签未显式设 inline，实际为 midpoint+(5,-5-labelHeight)，证明该次运行使用共享 FLabel false；不把 metadata true 当作运行属性，也不冒称另跑了 interactive-label 分支。B 的小检查另覆盖同位 bend 两次只移动 first、显式 desiredLength=0 的 presence、post-increment 边界、fixed 与可变向量身份、相等堆顺序。原命令见本轮 `B/{foundation,import-components,models}-owner-01/command.json`，这些 owner 检查不能代替独立 Node oracle。

完整选项、诊断、未见证分支、源失败/非有限值仍为目标；不加任意图数量上限，不用新循环 cap 替换源终止。完整 parser、公有注册、发布及全部功能后的最终验收另有门槛，机器 E18 仍为 planned。下面保留本批职责与来源设计。

机器计划仍为 planned。本批只跑变更相关校验，不运行 full、旧 E17/E16 图批或旧矩阵。B 单写来源 JSON、本文件和私有 algorithms/force.py、stress.py；root 管理共同宿主与镜像，V 独立审源和定义原 Node 请求。主 src、E11 包、README、pyproject 和已冻结 E17 两核不变。

## 单写接口与分块

force.py 持有源专用 FParticle/FNode/FEdge/FBendpoint/FLabel/FGraph、导入/回传/组件及两种 force model。stress.py 复用该真实模型，实现 Dijkstra/APSP/weights 和 StressMajorization；不能换用 MrTree/layered 模型或 JS/JVM/其他后端。

统一 `_layout(state,node,monitor=None)` 复用持久 JsonLayoutSession，wrapper 用共同 factory/export。真实微布局、identity/bucket、wire 和 presence 由宿主提供，不建第二 parser，不逐层 clone 丢失节点/端口身份与内部副作用。

第一块 FGraph/label/import/transfer/components/default/seed 独审后立即实现；第二块 Force 初始化、逐对 displacement、累加、模型/温度/终止/同位置处理；第三块 Stress 优先队列/remove、顺序 majorization、fixed/维度/收敛。来源、原观察、实现、校验和声明分别保存，数据类不算完整算法。

## 已封来源

唯一行为基线是 elkjs0.12.1 固定 worker，SHA `275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`。canonical `references/e18-force-stress-sources.json` 与 `test-runs/20261104-E18-01/B/first-source-proposal-02.json` 同 bytes，封 F01–09/S01–03 原 span/base64/SHA、依赖、默认和 targets；新 JSON 写 LF。

Java HEAD3aa3b9fb98d8f9a41285b3061cff5efe79ed2ba4 三份完整源码只作可读许可旁证，不替代 worker，不宣称 exact external build。算法保 ELK dual license。JavaRandom、真实 wall-ms/共享 seedcounter、clip、source sort、resize 只复用明确获审闭包；新 helper 逐依赖审，不用 Python random 或独立 seedcounter。

Stress noninteractive 真实调用 Force 获得初值再 reimport；interactive 才仅微布局。Force RANDOM 在 split 前创建，浅复制后跨组件共用连续 draw。FGraph node 使用中心坐标，原尺寸先算中心再 clamp>=1；FLabel refresh 是真实 top-left。Force component DFS 的 last-node 跳边与 MrTree 不同。

## Presence 与 pending

Stress 原 28031 以 hasProperty 区分 edge desiredEdgeLength 显式覆盖与 parent fallback。实际 27867 为 PARENTS+EDGES、default100；`state.has_option` 按 computed/cached mutable、removed/local/适用 global 判断，primitive 默认不能因读取获得 presence。

来源 JSON 的 targetDeclarations 已封 13 项声明：Force 参数与 Stress dimension/epsilon/iterationLimit 为 PARENTS，repulsivePower 为 EDGES，stress.fixed 为 NODES，desiredEdgeLength 为 PARENTS+EDGES；Core priority 为 NODES+EDGES、seed 为 PARENTS、edgeLabels.inline 为 LABELS。Stress inline metadata true 与 Force Property false 并存，需原 caller/default resolution 证明，不能仅凭 descriptor 推运行值。
