# E19：四个打包与拓扑保持算法的原生迁移准备

## 当前增量交付（HOST-10）

HOST-11 收口补记：四个 E19 私有 provider 真 body 均已实现。RectPacking 的完整三阶段、真实 Compactor clone 迭代、顺序处理、可选 whitespace、tryBox 真分支、前后真 Micro 和取消早退已按分块来源批准接齐。两份新增完整原版请求与 Python 首次执行均通过，几何误差为零、有限几何成立；default 覆盖二次 Compactor 与 min/padding/alignment，SIMPLE 覆盖 8 节点、重复 desiredPosition、size order、interactive、TO_ASPECT_RATIO 与小数间距。默认和 SIMPLE 分别保留 6、9 处生成 `$H` 严格差异及原 `terminate` TypeError，不宣称公共生命周期或安装包通过。

两份完整执行固定在源码 `5782e4d7…`。最终复核发现新 F14 对齐 helper 使用 caller fallback 会漏掉已修改但无 presence 的 Core EnumSet 默认值；只将这一 getter 改为 `get_native_property`，当前源码 `3384b8fe…`。负例与旧源全文保留，AST 证明其余整个模块不变，只新增一个 shared-default/no-has 控制验证修正。旧两份完整请求没有重采、重跑或改绑新 SHA。最终独审为 `HOST-11/V/rectpacking-provider-code-review-01.json`，当前全部 source/代码/实际证据身份见来源清单的 `latestPrivateDelivery`。

这些是私有源码与定向见证的交付，不是 E19 机器计划完成声明。完整 public registry、递归 coordinator、diagnostics 异常分支和同包验收由后续阶段完成；不能把少量成功请求宣称为所有选项组合已穷尽验证。以下 HOST-10 与准备阶段记录作为历史分块保留。

私有 DisCo 已接通真实分量导入、轮廓、栅格、Polyomino 打包、裁剪与几何回写。首个新增官方请求包含一个连通二节点分量与一个孤立节点，原版与 Python 的 mandatory 差异为零、几何有限；4 处生成 `$H` 的严格差异保留。独立代码审查为 `HOST-10/V/disco-provider-code-review-01.json`，只认证这次实际默认路径，没有认证所有选项组合。可选 underlying 仍走同 Session 真 provider，不克隆掉内部副作用。

共同 Polyomino 的栅格、叠加、四种 successor、quadrant 缓存、fill、9 种遍历选择、稳定排序和无额外 cap 的 first-fit 均已按来源实现。新增遍历对象已独立比较通过，Corner comparator 复用 7 个原版观察后首次原生比较通过。原 Collector 实际以常量 1 计数，不会把 Direction 强制转为 Long；初步疑问与更正后的第 03 份来源包均保留。独立完整 packer 对象执行仍单列 pending，不把源码审查或 Corner 的执行升级为全部策略实测。

RectPacking 已有真实最小尺寸、DrawingData、宽度近似、行与 Block/Stack 运算。RP16–20 余下 search/place/remove/expand 获得独立来源批准后才实现，四个新增原版对象与 Python 首次比较 strict 差异为零，代码审查也已接受；simulation 无写、真实换行与列表身份、按对象身份移除、空集合 IEEE NaN/Infinity、stack 绝对 Y 加尾部间距均保留。随后 RP22 的三种行调整、RP23/26/27 初始放置与 SIMPLE/NONE 阶段、RP28 whitespace 均已获独立来源批准并实现，各有一个新增局部控制。它们的新原版对照与代码审查另行记录，不能借先前 Block 的通过冒称已验收新增代码。RP21/24/25 compaction 与 RP29–31 完整调度仍待实现，不能提供替代布局或宣称完整 provider。

来源清单新增的每个 span 均逐字节核固定 worker、LF 编码及 SHA。`references/e19-packing-sources.json` 的 `latestPrivateDelivery` 记录当前私有文件身份和各次独立审查；旧执行报告继续绑定当时源码，不改绑为新 SHA。新 holder 的结构化默认值在自己的属性表 clone/cache，Spore 的 padding 8、RP 的首次 padding 15 按真实 caller 物化；不从 origin 偷读缺省，也不把 scalar 默认读取变成 presence。

以下分块说明保留准备阶段的历史语境；当前完成边界以上述交付及机器计划为准。开发仍只做变更相关校验，不运行旧组或全量。

最新增量：DisCo 的真实数据/缓存与严格多边形判定已分别通过独立来源和代码审查。两份数据对象、四份多边形对象使用原版 Node 先采集、Python 后对照，均无 typed 差异。判定保留 `1e-5` 开区间：完全包住 cell 的大 polygon 和边界完全重合的 polygon 都可能不相交；不能改为通用包围盒或闭线段判定。四个原结果复用，没有重采旧样例。

下一来源包分别是 `polyomino-grid-source-proposal-01.json`（TwoBitGrid/PlanarGrid/Polyomino 与 DCPolyomino 栅格化）、`rectpacking-drawing-source-proposal-01.json` 和 `rectpacking-width-source-proposal-01.json`。尚未获批准的部分不先写数学。Root 已授权 B 单写 `algorithms/polyomino.py`，只作为真实共享栅格/遍历/打包实现，不能当作后端。栅格化、完整 DisCo importer/packer 和 RectPacking packing/whitespace 仍待实现，不能把对象级对照升级为完整 provider 通过。

其中 PG01/PG04/PG05 栅格基础现已接受并实现，两个新增原版对象对照通过：真实 64 位 word 中每 32 个 cell、31/32 边界、值 3 与强/弱状态区分、逻辑宽度之外但 word 内的读取、center/弱区/重新初始化均保留。原 JS 内部 TypeError 文本与 Python 原生文本仍有严格差异，原始结果及 strict diff 全保留，不能称 raw parity 或公开错误消息协议相等。RP04–06 DrawingData 和已批准的 BlockRow/RectRow 子集已实现，独立对象验收另记；其余尚未批准的调用路径没有假实现。

PG02/PG03/D09 的真实叠加、扩展射线与 DisCo 栅格化也已接受：两个新增原版对象与 Python 首次比较 typed strict 差异为零，旧组没有重跑。逐格扫描仍可能留下完全处于大 polygon 内部的空 cell，填充是另外明确受选项控制的四 profile 阶段。PG06–12/14 的四种确定性 successor、quadrant 身份缓存、fill 和容器已按批准源码实现，但本次栅格对照没有认证它们，独立代码/对象核验另记。`JITTER` 名称在此指整数遍历顺序，不调用随机熵。

当前交付补记：SP01–SP21 与 TD01–TD06 的实际来源闭包已经分块接受。私有 `spore.py` 实现两个真实 provider，`triangulation.py` 实现 Bowyer–Watson、NaiveMinST 和真实值 hash/bucket 适配；Source 默认、同中心扰动、节点 margin-only、可变对象身份与 underlying provider 均使用共同持久 Session。当前两核已可运行，独立完整 provider 比对另行记录，不能凭来源批准宣称公开算法已验收。

`rectpacking.py` 目前只有真实 RP03 最小尺寸前/后处理：先 effective minimum，仅实际 parent 存在时调用真实 `process(False,True)`，只写内部尺寸；第二 flag 是 ignoreInsidePortLabels。它尚未提供 packing 结果。DisCo/Polyomino、RectPacking 其余数学、完整元数据/公有注册/同包验收仍为目标。

Root 已提供 `calculate_node_margins`、`random_unit`、`identifier_text`、`invoke_layout` 和 `label_node_minimum`。其中原生熵与布局 seed 独立、不宣称 V8 随机轨迹；内部 identifier 文本不改原 typed ID；invoke 只在成功解析后创建一次子任务并调用同 Session 真 body，已知未接分支明确报未实现。详见 ADR0012/0013 与本轮 immutable source proposals，旧执行 SHA 不重绑。

机器计划保持 planned，只做本次变更相关校验。B 单写本文件、`references/e19-packing-sources.json`，拟在独立迁移树实现 `algorithms/disco.py`、`spore.py`、`rectpacking.py`；公共 Polyomino/Delaunay helper 的具体文件归属另行冻结。E11 主源码与已接受 Force/Stress 不变，不运行旧矩阵或全量。

四个 provider 不能合并成一个简化打包器：DisCo 默认保留分量内部布局，真实变换为 Polyomino 再压紧；`sporeOverlap` 使用 Delaunay、最小生成树和 GrowTree，并显式覆盖树/根/代价策略；`sporeCompaction` 使用所选结构、树、代价与 DepthFirstCompaction；rectpacking 有真实三阶段与若干中间处理器，只在原 tryBox 判定分支调用已实现 Box，不能整体替换成 Box 或 Frame。

## 接口与分块

各入口复用单作业持久 `JsonLayoutSession` 和 `_layout(state,node,monitor=None)`，保留真实输入节点、端口、标签与 computed options 身份。Spore 两入口共享实际 Graph/Node/import/transfer；DisCo 与 rectpacking 使用各自源专用模型。显式 underlying/component 算法选项应调用未来中央真实 provider factory，不执行 JS/JVM/其他后端，不用假布局应付分支。

第一块是 SPOrE Node 的可变中心/rectangle、translate、underlap、rectangle overlap factor 与共享 Graph 数据。它只解锁这些真实几何原语，不认证 Delaunay 或 provider。第二块封 NodeMargin 导入、真实几何距离与 transfer；第三块分开封 Delaunay 结构、树与代价、scanline、GrowTree/DepthFirstCompaction。另并行推进 DisCo connected components/Polyomino 与 rectpacking width approximation、packing、whitespace、order/minimum/row/stack 小闭包。每个闭包独审接受后立即实现，再取独立官方定向请求，不等整个 E19 源包。

唯一行为基线为 elkjs0.12.1 固定 worker，SHA `275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`。原 span 的 LF bytes/base64/SHA 与依赖已封；固定 Java HEAD 的五份完整源码仅为可读许可旁证，不宣称 exact external build。新增 helper 必须逐依赖核许可，不能把 GWT/Guava 等支持代码泛标 ELK dual。

## 必须保留的宿主义务

Spore importer 的同中心检测原调用 `Math.random`，不受 `randomSeed` 选项控制。原 while guard、每轮两次取样和幅度需封入后续源块；原生熵策略由 root 明确 ADR，不能跳过重心碰撞、固定黄金 seed 或宣称跨 V8/CPython 随机轨迹相同。当前基础几何闭包不涉及该随机分支。

DisCo/Spore 的 underlying provider 是真实可见选项，中央 registry 未接完时明确 pending。Spore 导入使用真实 NodeMarginCalculator 与 margins/spacing，不能替换为仅 width/height 的假 margin。Rectpacking 前后两次 NodeMicro、最小尺寸与顺序副作用也须按源保留。源失败、非有限数值、原始 strict `$H` 差异、退化结构与所有策略分支分别记录；不加任意图数量上限，不以新迭代 cap 替换源终止。
