# ADR-0004：E05 DAG与长边协议

状态：source-reviewed，revision1（`E05-ADR0004-revision1`）。行为基线仍为固定elkjs0.12.1；22个实际组件已独立来源审阅。运行验收另由E05当前包证据决定，不表示任意DAG已支持。
run：`test-runs/20261103-E05-01`；636文件已备份、400项基线通过。来源范围已冻结：0–8原始节点的单连通简单DAG，RIGHT/缺省，ORTHOGONAL；13个intermediate、6次主phase调用、导入/导出及indexed-target共22组件，固定分母由来源审计脚本独立枚举。

## 共同前提

单层、单连通、extended single-source/target edges的无环图，RIGHT/缺省、ORTHOGONAL、给定有限非负尺寸、非零signed32 seed；原E04能力必须回归。空图/单节点保留真实源支路。
节点数上限8；尺寸、有效spacing/padding各在0–1000000。NS在split前处理原始节点；归一化层数不超过8，长边dummy总数不超过C(8,3)=56，故内部节点不超过64、段边不超过84、端口不超过168。后续phase按这些实际内部上限审查，不能借原节点数绕开大图分支。
有效padding仍为源importer接受的字符串；logging/timing和未审的已有几何/标签/端口/层级等前提不随拓扑扩展自动改变。自环、平行边、环、多连通分量、其他方向仍不准入；Kahn检查只作DAG admission，不提供布局层次或坐标。
固定生成worker为实际来源，原许可与NOTICE保留；精确外部Java build仍unresolved。每项新增component/helper/输入域需独立source review和root逐组件审批，只有全部实际slice闭合才提升全局来源gate。
部分审批使用UTF-8规范component JSON SHA：`json.dumps(component, sort_keys=True, ensure_ascii=True, separators=(",", ":"))`，不加尾换行。其引用的source身份、可变proof/guard依赖闭包同时绑定；原E04不可变映射用版本化文件SHA引用。审批记录当时document SHA，最后完整slice另封final document SHA，不因其他open组件追加而静默改变已审内容。

## 图与身份协议

沿用E04 eq=False的LGraph/LNode/LPort/LEdge/Layer和有序身份邻接，不重定义公共图层。A唯一写graph/import/export/processors；B唯一写phases和新crossing/placement/routing；root写scope/pipeline/API和全局验证。
原始NORMAL节点的`node.origin`仍为E03 Node，dummy的`node.origin=None`，真实来源ORIGIN放在properties里（可能为LEdge），不能把所有无origin对象直接过滤丢弃。
虚拟节点type使用源`LONG_EDGE`；源内`LONG_EDGE_SOURCE/TARGET`、端口约束、thickness、ORIGIN等实际属性保留原角色，不先发明独立链算法或持久registry替代源内links。
使用已有mutable位置/尺寸/margin/padding、端口incoming/outgoing及层列表；新增字段/属性必须先登记来源读写，再由root冻结。内部整数ID与虚拟身份不回写用户节点/边ID。
set_source/set_target/set_port_owner/set_layer保留源move-to-tail语义；LongEdgeJoiner需要按原target索引重连时，A提出具名indexed setter并绑定实际源语义，经独立小范围复核后加入，不修改已有setter含义。
A在`long_edges.py`唯一提供`get_junction_points(edge)->list[Vec2]`：缺失时每edge创建并store新的mutable空链，返回存储对象；已有空链按presence取同一对象，不能用Python truthiness代替JS对象存在。B routing需要此行为时调用同一实现。厚度属性统一名由A依实际源记录并同步，默认thickness=1时dummy尺寸(0,1)、port.y=floor(1/2)=0，不能泛化为零高或居中0.5。

## 阶段接口与调用顺序

A提供`layering.network_simplex_layerer(graph)->None`；B维护原`phases.network_simplex_layerer`入口为兼容包装，在A接口稳定后委派，E04公共导入不破坏。
B保持greedy_cycle_breaker/layer_sweep(graph, strategy=...)/bk_node_placer/orthogonal_edge_router签名。A按真实processor配置提供split/join/port-side/sort/node-size/margin等，不沿用“多端口都居中”的路径推导。
root以真正DAG trace和源配置核实际processor序列，允许必要新增processor；不能先假定固定19调用，也不能用通用no-op填表。空图源leaf支路不强行执行非空pipeline。
真实图每call一条源random流；局部LayerSweep流的初始化、消耗和整数host语义需逐阶段对应，不因拓扑变多换Python random。
原节点数和内部节点数分阶段区分：NS发生在split之前；多长边会放大内部图，8原节点的complete DAG可到64内部节点。该规模及每阶段相关条件需独立源证明，不能由“原节点<=8”推出后续处理器所有分支仍在E04路径内。

## 恢复、导出与trace

split后所有实际长边段连接相邻层，保持原始边链和有序端口邻接；source证明允许的特殊支路另行声明。
join按源内端口索引/弯折点次序恢复；最终原始节点/边分母、ID、数组顺序、端点和业务值精确保留，内部dummy、临时ID和stage属性不能泄漏为公开JSON字段。
root trace必须区分同一original edge派生的多个内部段及dummy，不依赖用户ID唯一标识每个临时对象；快照只观察，不参与选择布局。JSON结果之外单独保存真实阶段/RNG状态。
导出combine/offset/resize只由A export执行一次，root pipeline不重复处理。

## 审计与验证迁移

E04原始source/安装/数值收据是历史事实，不回写成E05通过。当前E05支持域与新wheel必须有自己的运行证据。
E04历史审计应保持完整来源/默认值/ID/输入/采集命令/原失败语义守卫；明确的historical-only模式不拿旧wheel package SHA认证新src。默认current模式不因迁移而失去当前源码字节校验。
历史模式使用`references/history/E04`保存的真实原wheel（48KB）和原声明字节，禁止作为运行时fallback导入/执行。旧审计负例的独立fixture从该真实archive恢复E04原包/声明，再验证当前模式，避免新runtime变化使所有负例提前无关失败。历史模式明确`currentPackageBytesValidated=false`，新的当前能力必须由E05新wheel验收。
原E04负例若因真实新增能力成为正例，须由root明确迁移相应“尚未支持”断言并保留历史suite admission，不删除结构/非法输入/几何不变量；其他lane不能顺手改旧测试。
同suite真实JS/已安装Python候选至少各3次，显式native profile/default-seed policy、完整原strict差异、独立几何及exact重复共同验收。abs1e-6/rel1e-9不变；完整12/243/8和25master分母保留。
