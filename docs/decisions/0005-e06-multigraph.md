# ADR-0005：环、自环、平行边与阶段协议

状态：source-reviewed，revision1，scope id `E06-ADR0005-revision1`。27组件已逐项独立审查并批准，公开准入切换到本范围；运行验收单独见E06最终记录。
run=`test-runs/20261103-E06-01`；1055文件起点已备份，498项基线已通过。实际源固定elkjs0.12.1 commit `624ae90aa37110033a8af59c5ccbb292708b4317`、生成worker SHA `275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`。

## 输入与规模

限定单层、单弱连通、0–8原始节点、最多28原始边的有向多重图，允许环、自环和相同端点的独立平行边。RIGHT/缺省、ORTHOGONAL、给定尺寸/有效spacing/padding各在0–1000000、非零signed32 seed；省略seed仍沿固定default1政策，非法值/歧义不回退。
原E05全部输入仍在范围内；原25master、E04/E05各suite与原始oracle保留。公开ports/labels/层级/初始几何/高级选项等旧边界不自动放开，显式padding仍需参考importer接受的字符串。
NS在原始节点上工作；规范化层数不超过8须由新来源审查证明。非self边跨度不超过7，单边dummy不超过6，因此粗界为176内部节点、196段边、392端口。selfloop预处理不新建节点/端口；恢复的原loop端口计入总端口界。每个阶段须验证自己的实际前提，不能复用E05 simple-DAG的64界。
实际压力输入已观测到134内部节点，作为正式候选用例；有限观测只印证，不替代理论边界审查。parallel默认每原edge独立两个端口，原始MERGE/HYPERNODE/collector默认false链另封source证明，不添加不存在的专用运行算法。

## 原始身份、反向与长边

A提供`cycles.reverse_edge(edge, *, adapt_ports: bool)->None`。保留`LEdge.origin`，先detach原两端，再old target挂source、old source挂target；不改变port side/position/anchor。`REVERSED`逐次toggle，恢复后保留显式False属性；bend链反序并逐Vec2深拷贝。JUNCTION_POINTS链不因reverse额外倒序。
adapt_ports只涉及源collector支路；本轮显式排除collector，不能偷换成一般端口重建。restore逐layer/node/port遍历outgoing快照，允许恢复后在后续port再次遇到同edge，以False避免再次反转。GREEDY候选唯一仍须`next_int(1)`消耗真实31bits。
NS/split使用反向后的当前邻接；REVERSED是私有元数据，不能污染公开原始sources/targets。长边拆分/ORIGIN/indexed join与Junction getter继续按源身份/顺序恢复，同原edge对应多个段必须在trace中区分。

## 自环与调用次序

无selfloop仍为19实际调用；默认有selfloop时，在正确源配置位置插入PreProcessor、PortRestorer、Router、PostProcessor，共23。pipeline配置按真实graph flags一次决定，不依据case ID或观察结果分派。
SelfLoopPreProcessor保存真实holder/loop/wrapper，detach原loop edge两端与loop-only端口。两次LayerSweep期间这些对象隐藏；PortRestorer在其后恢复原NORTH端口，edge仍detach。NodeSize分布NORTH端口，margin处理后SelfLoopRouter计算真实slot/bends及margin，BK和普通ORTHO只读当前可见flow邻接；Post最后恢复原edge并加node位置偏移。不能提前连回loop参与交叉计数或路由。
默认loop使用NORTH/STACKED、无labels。其他side/自定义选项/collector不因该实现而支持。缓存portSideIndices可能仍是恢复前状态；不添加源码未读取的缓存一致性前提。
B独占`SelfLoopHolder`、`SelfLoopPort`、`SelfLoopEdge`、`SelfHyperLoop`身份类及真实算法；原对象身份不重建成公共ID表。B同时提供纯观察`snapshot_holder(holder, value)->dict`，包含有序hidden refs、geometry/owner/adjacency；root将其接到独立trace，不写算法属性或消耗RNG。

## 来源、所有权和验收

固定来源分母27：A8（reverse/GREEDY/NS/split/join/restorer/import/export）、B4 selfloop阶段、root15（pipeline配置、四个排序/放置/普通路由phase、其余10intermediate）。indexed setter与其他未改helper以E05固定artifact/seal继承；默认unmerged guard另封不可变证明，不虚增运行算法数。
每组件批准须绑定canonical component、source context、实际helper/guard、typed proof依赖、版本化独立review和原license；部分组件获批即可实现，整gate等全部支持域闭合。source提案里的旧scope/guard明确标为不继承，不能用DAG no-op结论泛化有环行为。
root独占scope/pipeline/phases/processors/crossing/placement/routing和全局检查/状态；A独占graph/cycles/layering/long_edges/import_export；B独占loops及E06 source observer；V独立suite/来源审计/真实conformance。后续文件转交须先登记，旧“尚不支持”测试只由root明确迁移。
几何默认保留原独立orthogonal检查。零尺寸cycle同坐标不证明同层；如采用不同rank源lemma，须显式policy并核原拓扑/默认策略前提，不能按case ID或整个SCC豁免。几何容差不变；section ID、业务值、端点和数组顺序严格。
本轮实际采用`rankSeparation=default-greedy-simple-ring-v1`。仅原输入2–8节点、恰好n条边、每点各一入一出、单一有向简单环、默认策略满足来源前提时，由GREEDY与unit-minimum NETWORK_SIMPLEX证明原节点rank互异。无marker沿用旧校验；多环、附加边、自环、平行边或高级策略均不得引用该lemma。重叠、边框、端点、路由及模型顺序检查继续执行。
E04/E05原包和声明只做历史归档审计，不能认证E06当前源码；新wheel使用同一正式suite两端各至少3次、候选-I/空PATH，旧两个suite回归，并经Windows/WSL/Git过滤副本同源码验证。
完整算法通过数仍0，12/243/8与25master分母不缩。精确外部Java build和项目发行许可仍待后续门禁；本轮不发布或执行py-mermaid集成。
