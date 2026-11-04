# E17：mrtree 与 radial 私有原生迁移

机器计划仍为 planned。本批是固定 worker 来源核验与隔离副本的实际实现，不代表 E17 或完整算法门禁完成。E11 主源码、README、版本及候选包不变；不启动全量，不重跑 E16 的既有 17 项。

B 独占 `references/e17-tree-sources.json`、本文件以及 `.local/migration-next/src/pyelk/algorithms/mrtree.py`、`radial.py`。root 管理中央 State/递归/import/export 与私有代码镜像；A 管理共享 NodeContext/NodeMicroLayout；V 独立审来源、定义并采集官方原请求和结果。获审的小闭包立即移植，不等整个算法的大审计。

## 真实路径与分块

mrtree 的真实 provider 先执行 NodeMicroLayout，再构建 ordered TGraph，分 connected components，执行 treeification、node ordering、node placement、edge routing 及按配置插入的 intermediate processors，最后 pack、normalize 与 transfer。首块先实现真实 TGraph、DFS/BFS treeification、root/forest 和 eliminated edges 恢复；这些阶段不产生冒充完整布局的坐标。

随后逐块移植所有 weighting/constraint、方向、compaction/levels、routing modes/gaps 及组件排序/packing。目标包括非树输入和适用的完整选项，不以仅简单树、仅默认配置或任意节点上限代替完整目标。未闭合的阶段明确 pending。

radial 逐块核 provider/root/radius、Eades node-size/leaves wedge、sorters/optimization、compaction、rotation/topdown/angle 与最终坐标。真实 `findRoot` 只取第一个无 incoming 的子节点，不能凭算法名称新增“所有非树一律拒绝”的预校验；无 root 的原错误及其它拓扑结果由独立官方观察决定。

## 共享模型与宿主边界

保持 E16 的每作业单一持久 `_State`，原 node/port 身份、内部清除的 constraints 与推导 side 跨 provider 保留。目标入口仍为 `_layout(state, node, monitor=None)`，克隆 convenience wrapper 与公开注册由中央宿主分开处理。

两个算法默认调用真实 NodeMicroLayout。需要 root/A 的 generic raw-node adapter/hook 连接已审的 common cell/NodeContext/placement，不能默默跳过标签或端口，也不能按文本长度猜尺寸。这个共享依赖没有完成前，不用 `omitNodeMicroLayout=true` 的小例冒充默认完整能力。

TGraph 专用节点/边保存真实有序 adjacency、临时 properties 和 origin 引用；不污染调用者 `layoutOptions`。源中的 IDs 是当前算法图内部顺序，不是按公共请求 id 分派布局。没有 JS/JVM 或其它布局后端参与候选计算。

## 首块需要保留的细节

- 图导入先用原尺寸一半计算初始中心，再将算法尺寸取至少 1。
- DFS/BFS 严格按源的 visited=0/1/2 转移，不换成教科书版本；BFS 的标记时机在 dequeue。
- eliminated edges 只从节点 adjacency 删除，仍在图 edges 和 REMOVABLE_EDGES，恢复时按原记录顺序 append。
- root 数 0/1/多分别按源建立 DUMMY_ROOT、不改、或 SUPER_ROOT 与 dummy edges；不按直觉另选根。
- 默认 mrtree padding=20、spacing=20/3、MODEL_ORDER、DFS、AVOID_OVERLAP；完整有效属性和实际依赖仍逐源核。

基线、原 span bytes/SHA、依赖和各块 pending 范围在来源 JSON；来源接受与实现/测试结论分别保存。运行证据在 `test-runs/20261104-E17-01`，V 的首批官方全图原样例另保留于 next-native 原观察目录。阶段对象级比较与完整 provider 几何比较分开，原 strict 差异与首败不覆盖。

## 当前交付与真实边界

MrTree 已实现真实模型、树化/根/恢复、四种排序、Walker、方向/坐标、完整压缩、组件和三种路由，按固定 15 阶段运行。V 的 routing-code-review-02 接受数学闭包；9 个阶段对象、12 个舍入值、新增 3 个路由/压缩对象及装箱/补偿 mean 的实际对照分别保留。pack 仅承诺真实入口与已审阶段的可达属性，不宣称任意手工 IProperty 引擎等价。

Radial 已实现 R01–16 数学、所有 sorter/优化目标/compactor、旋转、图尺寸、路由及角度。POSITION 是一次解码的 mutable Vec2，fuzzy 排序复用真实 source sort；原怪异算术、acos NaN 和副作用不修正。HashSet 使用共同 signed32 identity allocator，保留桶首序和桶内 identity；不读输入 `$H`，不冒称复制所有 GWT 分配点，不加图数量上限。BigLong 仅观察语义，数值转换为原创宿主适配。

两 wrapper 仅接统一 JsonLayoutSession/export，数学 AST 不变。root 默认微布局四原图已实际通过，B 只新增首树 wrapper 默认路径一次，真实微布局调用、caller 保留、非 `$H` 差异零，原 strict 差异完整保存。旧四图没有整批重跑。

Radial 第三新官方例本身返回 nonfinite 的 JSON null；内核保 NaN/Infinity，仅最终共同 wire 映射 null。source wire parity 与 valid finite geometry 分开报告，不能 clamp 或把 null 算有效几何。

高级诊断仍单列：Radial logging=true 缺真实 logGraph snapshot 时明确 pending；false 原调用为 noop。MrTree 新增一份 timing 原请求实际 TypeError/java.lang.NullPointerException，来自未 begin 子 monitor；只认证该组合，不制造成功树。

完整 243 parser、递归/坐标模式、公有注册、安装包与整轮门槛仍由后续宿主处理。主 src/README/pyproject 未由 B 修改，未跑 full。先前 PowerShell 编码造成的问号追加段已修复，原件保留 B encoding-fix 前快照；旧 handoff/执行 SHA 不重绑。
