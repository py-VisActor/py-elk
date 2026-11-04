# ADR-0003：E04生成源切片与阶段接口

状态：接口与支持域frozen-design，revision 4；逐组件来源已完成独立复核，见[审批记录](../../references/e04-component-approvals.json)。run：`test-runs/20261103-E04-01`。revision2补源内LayerSweep实际写入的Layer.id；历次修订原件保留于run。
原始373文件已备份，276项基线通过。本ADR定义设计边界；实际执行结论由独立源码审查和安装验证记录提供。

## 来源与许可

实际移植输入为固定elkjs0.12.1、commit624ae90aa37110033a8af59c5ccbb292708b4317的生成worker，SHA275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86，与锁定npm逐字节一致。准确外部Java build仍unresolved，不使用候选标签冒充。
源入口、活跃helper、读取/写入、数值/collection host映射、guarded-out分支和局部等价推导必须逐组件记录；运行trace只提供观察，不能替代所有值/循环的源码论证。
明确前提下可提取生成源码的退化分支，但必须执行真实写操作和随机消耗，不用通用no-op或oracle坐标代替。
来源按组件审批：有独立source review、固定document/review/许可SHA及明确前置guard的组件可先机械移植，未核实组件继续等待。全局algorithm-source只有实际slice所有组件闭合后才verified，不以部分phase审批冒充完整slice。纯Python数据表达/双向邻接可作为host实现独立推进，不提前写布局计算。
机械移植文件保留`EPL-2.0 OR GPL-3.0-or-later` SPDX与生成源身份；原LICENSE字节和NOTICE已在`src/pyelk/_licenses/`，wheel带上。项目自身发行许可独立未定，不表示已可正式发布。

## 本轮支持域

`scope.validate_slice(context)`是独立host admission，不产生rank/坐标。flat单向连通无环路径，0–4个child、非空字符串身份、给定有限非负尺寸；input node/edge数组可任意顺序，不把数组顺序当path。
RIGHT或UNDEFINED按真实路径解析；非零signed32 seed、separateConnectedComponents=true、ORTHOGONAL；node尺寸/三间距/四边padding均<=1e6。
限制源于本轮审查范围及源内n>=40/浮点epsilon分支，不代表整个layered算法支持。超域明确失败，不按case ID白名单，也不回退其他布局。
ports/labels/compound、fork/join/cycle/self/parallel/disconnected、非空child/edge局部配置、legacy properties容器、已有root几何/node位置/edge sections和container、logging/timing真值及未知执行参数均域外。空模型容器和不影响ELK语义的业务字段保留。
只注册本轮layered切片，constructor算法筛选仅缺省或['layered']；worker参数出现即拒绝。原25master分母保留，5个原字节请求与16新增变体分别登记，未入选不计通过。

## 共享LGraph协议

A独占`graph.py/import_export.py/processors.py`与`tests/layered/test_processors.py`，B独占`phases.py`与`test_phases.py`；root独占scope/pipeline/最小API和全局审计，V独占suite/conformance。
mutable dataclass均eq=False，算法对象使用身份比较；顺序由list维护，不用set/hash顺序决定布局。
Vec2(x,y)、Insets(top,right,bottom,left)为mutable数值；LGraph(origin:Graph,options:ResolvedOptions,random,layerless_nodes,layers,size,offset,padding,properties)。
LNode(graph,origin,id,type,pos,size,margin,padding,ports,layer,properties,port_sides_cached,port_side_indices)；LPort(owner,origin,id,side,pos,size,anchor,incoming_edges,outgoing_edges,properties)；LEdge(origin,id,source,target,bend_points,properties)；Layer(graph,nodes,size,id=0)，Layer.id由真实LayerSweep写layer index，不能省略为动态外部字段。
set_source/set_target/set_port_owner/set_layer(node,layer,index=None)维护双向有序邻接，不只改指针。origin保存E03身份，内部整数id不回写用户ID。
`import_graph(context,random)->LGraph`真实导入隐式port；`export_layout(graph)->dict`从原JSON独立副本回填，保留业务字段/顺序，生成sections不绕过E03索引写入限制。

## 阶段与随机接口

B提供`greedy_cycle_breaker(graph)`、`network_simplex_layerer(graph)`、`layer_sweep(graph,*,strategy)`、`bk_node_placer(graph)`、`orthogonal_edge_router(graph)`。
JavaRandom(seed)提供next(bits)/next_int(bound)/next_long/next_float/next_double/set_seed；图每call一实例，LayerSweep局部流按真实source初始化。生成GWT数值/整数行为与标准Java不同之处明确保留，不泛称全部Java兼容。
A提供13个具名intermediate函数(graph)，root按E01默认19调用顺序dispatch，两个LayerSweep策略分别为BARYCENTER/TWO_SIDED_GREEDY_SWITCH。空图按来源递归早退，不伪造19调用；单点仍按实际19调用和各stage早退。
trace只为研发另存，记录真实执行的阶段与工作图/RNG，不混入ELK JSON、不参与生成坐标。

## 最小公开连接与验收

root在算法真正完成后才导出`ELK(options=None)`、`async layout(graph,args=None)`，调用真实pipeline。输入精确保留，失败明确，不读reference/golden、不启动Node/JVM。terminateWorker只做本地关闭，完整生命周期/调度/取消验收仍归E08。
当前async连接不承诺CPU并行或事件循环隔离；只宣布实际测过的实验性slice，不提升完整12算法/243布局选项的通过状态。
同suite官方/真实已安装wheel候选比较：原strict差异保留，native profile、独立geometry、重复确定性共同验收；既定坐标1e-6/1e-9不变。
V发现零尺寸+零间距使不同DAG层同x的合法oracle：geometry仅以原输入DAG可达性排除“同坐标即同层”的误判；不放松非可达siblings、循环输入、重叠/方向/边距等检查，独立负例验证。

revision3补充host入口边界：已有root logging、root/child直接`$H`会触发额外cache/清理支路，暂不属于本slice。嵌套业务`$H`和`error.stack`仍按E02合同保留，未修改21个原请求字节。

revision4要求有效显式padding为源JSON importer接受的字符串；E03 Mapping解析只是宿主便利能力。检查最终选中raw值：被call空配置或local字符串覆盖的Mapping不影响实际布局，不应误拒。已有edge几何按字段存在拒绝，包括空sections/junctionPoints/bendPoints及sourcePoint/targetPoint。

省略seed的重复校验使用独立、显式的`elkjs-0.12.1-default-seed-v1`来源policy，固定默认值1；原`explicit-nonzero-seed`规则不变。显式0/非法值/多别名歧义不回退，完整合同重复仍exact比较，不修改请求或坐标容差。
