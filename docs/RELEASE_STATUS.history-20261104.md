# 当前状态

完成审计补充（2026-11-04）：37 步／917 测试是冻结开发检查通过，不能代替所有 E11–E21 退出条件。当前补当前 0.1 包逐算法性能/峰值内存、243 选项效果/状态账本、独立高级几何与干净 Git checkout 验证；PyPI 配置和上传下载仍待完成。算法实现不重做，已过数学组不重跑。详见 `docs/implementation-backlog.json`。

当前发行状态（2026-11-04）：完整迁移及冻结全量校验已通过（37 步／917 测试），正式源码为 `0.1.0` 候选。仅版本字面值的运行差异已核，新 wheel/sdist 双安装已验。详见 [0.1.0 发行收口](releases/0.1.0.md)；剩余为 PyPI 配置、上传及下载复验，尚未发布。下方执行中与旧切片说明按其历史日期理解，不要重复实现已完成的功能。

当前状态（2026-11-04）：[完整实现已合入正式 src，进入统一校验与集中修复](FULL_NATIVE_IMPLEMENTATION.md)。196 个 Python 模块语法/导入通过；12/243/8 完整接线尚未代表正确性通过。`.local/migration-next` 已冻结；本阶段修复直接改 `src/pyelk`。下方旧私有批次与切片状态仅按其日期作历史记录。

用户最新决定：切换为[先实现全部功能，再统一校验修复](IMPLEMENTATION_FIRST.md)。第 19 批起四路实现并行，暂停逐模块原版/差分与审查等待，仅最低语法/导入/接线检查；新代码状态为未验证，旧 18 批的验收事实不改。发布和完整算法通过数在统一验证前不提升。

最新 [18 批](changes/20261104-next-native-18.json)：191 文件、1760 份新增材料、16 份限定代码审查。实际新增 7 个完整 caller：Polyline、LongestPath 两种、DepthFirst、Simple、非空端点标签、非空中心标签，完整几何/日志/输入按范围通过，原始 `$H` 差异保留。标签管理回调已审但未在两个完整标签调用中实际选中。纯绑定 0.262681 秒、0 产品；完整算法仍 0、正式 src 仍 E11，未全量/未发布。按 [19 brief](iterations/NEXT_NATIVE_19.md)继续，见[校验入口](iterations/LABELS_PHASE_STRATEGIES_VALIDATION.md)。下方 17 及更早为历史。

最新 [17 批](changes/20261104-next-native-17.json)固定 183 文件，新增 1333 份材料、10 份限定代码审查。完整 compound、DOWN、组件压缩与 logging=false 最小 SPLINES 新调用按限定范围通过，原始 `$H` 差异及 logging=true 原版 NPE 保留；旧 external 23 项顺序差异仍开放。Spline P5/Final 已审，Polyline/center-label 草稿未在此快照验收。见[校验入口](iterations/NATIVE_COMPOUND_COMPACTION_SPLINE_VALIDATION.md)，按 [18 brief](iterations/NEXT_NATIVE_18.md)继续。正式 src 仍 E11，完整算法仍 0；未全量、未发布。下方 16 及更早为历史。

最新 [16 批](changes/20261104-next-native-16.json)固定 171 文件，新增 928 份材料、9 份限定代码审查。层级导入、compound 前后处理、层级尺寸、Spline 数据/排序、矩形凸包与南北正交策略已分别验收；完整 compound consumer、Spline 主流程/Final 和 connected compactor 尚待。首次 Spline gap 原始配置差异 10 项保留，不冒称整个 Spline 通过。纯绑定检查 0.169610 秒、0 产品执行；完整算法仍 0，正式 src 仍 E11，未全量/未发布。按 [17 brief](iterations/NEXT_NATIVE_17.md)继续，下方 15 及更早为历史。

最新 [15 批](changes/20261104-next-native-15.json)固定 162 文件：默认 19 阶段及自环 23 阶段真实整调用已独审，私有注册/RGE/池与持久缓存已验；原始四个 Source 生成 `$H` 差异保留，受限 ADR 投影后完整结果严格零差。799 份新增材料、13 份限定代码审查保留首败及实际 SHA。CGraph、基础间距和 NubSpline 已验，hierarchy 草稿/compound/general Spline/connected compactor 继续实施。正式 src 仍 E11，完整算法仍 0；未全量/未发布，继续 [16 brief](iterations/NEXT_NATIVE_16.md)。

最新 [14 批](changes/20261104-next-native-14.json)固定 154 文件，新增 366 份材料、10 份限定代码审查。Adapter/共享 enum/三种 component placer/自环基础与 pre/post/side assignment 按范围完成；外部首例原始 23 项顺序差异保留，其余四例严格通过。Long/End/constraints 已代码独审，真实默认完整入口正在接线；whole algorithm 仍 0，未全量、未发布。继续 [15 brief](iterations/NEXT_NATIVE_15.md)。

2026-11-04 项目原创代码许可已由用户明确选择 **MIT**，发行包按混合来源表达式声明并保留上游通知，见[决定](E11_LICENSE_PROPOSAL.md)。许可选择不再待定；尚未正式发布，功能迁移与技术验收继续。下方旧批次中的待定描述仅作历史。

最新 [13 批](changes/20261104-next-native-13.json)固定 146 文件。新增全局配置、通用组件 split/SimpleRow、cleanup/resize 已完成限定来源/代码/实际对象校验；外部 component placer、Compactor、完整 Layered 导入与主流程、公开包仍待完成。259 份新增材料保留原失败与实际执行 SHA。完整算法验收仍为 0，未全量、未发布；继续 [14 brief](iterations/NEXT_NATIVE_14.md)。下方 12 及更早状态属于历史。

最新私有迁移见 [12 批](changes/20261104-next-native-12.json)：138 文件固定检查点、356 份新增材料。元数据与通用 NS/BK/Orthogonal 指定范围已独审；完整 Layered 导入/组件/尺寸/主流程、全局配置及公开入口仍待接通。正式包未发布，完整算法验收仍为 0。按 [13 brief](iterations/NEXT_NATIVE_13.md)继续，全部功能完成后再全量。以下旧切片验收不能代替完整迁移验收。

最新 [11 批](changes/20261104-next-native-11.json) 固定 126 文件及 1218 份归档材料，15 份代码复审保留各自范围。普通递归两例、Topdown、DisCo→Fixed 共享池四个新增完整调用场景严格对照通过，14 个 local import DTO 已独审。来源/证据完整性校验约 0.19 秒，未执行产品或全量。完整 Layered、公开 API、正式包仍在推进，完整算法验收保持 0；继续 [12 批 brief](iterations/NEXT_NATIVE_12.md)。下方 10 批及更早内容为历史状态。

最新[10批](changes/20261104-next-native-10.json)固定104文件与170份证据，8份代码独审各保子范围：真实MODEL_ORDER producer、实际Layered默认声明/scalar入口、per-node resolver及DisCo真实同会话调用已落。新增原控按场景对照，未重旧组或全量；完整算法验收仍0，公开仍9选项、正式包未发布。按[11 brief](iterations/NEXT_NATIVE_11.md)继续真实递归/完整导入/其余Layered策略与RectPacking。下文09及更早是历史。

最新[09批](changes/20261104-next-native-09.json)固定99文件与203份原始证据。typed junction生成/平移/条件导出、Snapshot/Session当前holder默认、Box/Fixed/Spore实际padding首读及Integer解析/显式token赋值桥已按声明范围独审。新增原对象对照与目标负控制通过，旧成功组未重跑；归档核验仅执行字节绑定检查。完整算法验收0，公开仍9选项，尚未全量、发布或集成py-mermaid。按[10 brief](iterations/NEXT_NATIVE_10.md)继续MODEL_ORDER真实producer、完整sweep/递归与DisCo/RectPacking。下方08及更早是历史。

最新[08批](changes/20261104-next-native-08.json)已保存96文件、212份新增原始证据。Session类型登记243、raw可构造235，8个原版无构造器分支明确诊断；Core实际标量默认68、向量链浅clone与属性快照已独审。新增真实Box请求、属性配置/对象/快照及各计数、packing内核小对象对照通过；grid原始错误文本差异保留。完整owner默认、盒身份、sweep/递归/完整packing及公开包继续，完整算法验收仍0。未全量或发布；[09 brief](iterations/NEXT_NATIVE_09.md)已列下批分工。下方07及更早内容为固定历史。

最新[07批](changes/20261104-next-native-07.json)固定90文件及82份新增原始证据。225项静态声明/独立显式解析器、Core默认隔离与SweepCopy已源/代码独审；10个新原解析控制与3个新对象控制通过，未重跑旧布局组。解析器尚未接入Session/公开API，Session仍63项、公开仍9项，完整算法验收仍0。后续见[08 brief](iterations/NEXT_NATIVE_08.md)；下方06及更早批次是固定历史。未执行全量或发布。

用户最新规则：持续goal完成剩余E09–E21迁移；[变更校验政策](VALIDATION_POLICY.md) 优先。开发只运行变更相关校验，全部功能完成后再统一全量；下文旧逐轮full要求不再作为当前收口前置。

最新[06批](changes/20261104-next-native-06.json)固定87文件及389份原始证据：共享运行层、Spore两个真实私有provider请求和barycenter/Forster/model-order/port-rank/distribution内核已按变更独审。私有schema63项，公开仍9；全部243项元数据仅完成原始采集。DisCo目前为数据/cache/公式，RectPacking目前为minimum预后处理，完整实现继续。独审发现并修复DOUBLE默认覆盖及EnumSet复制/变更丢失问题，只复验受影响分支。正式src/发行仍未切换，完整算法验收数仍0；本批未全量。操作见[共享运行层手册](iterations/HOST_DELTA_VALIDATION.md)。下文04及更早批次是历史状态。

2026-11-04并行先行实现继续推进：已保存71文件[源码检查点](../migration/next-native/README.md)及[最新记录](changes/20261104-next-native-04.json)。私有schema53项，Session共用存在性/显式global/删除与generic声明；NS helper/两字段bridge独审及三个原版local样例通过。新增属性helper两个分支、Box全局请求一个、binary64语义几何两个对照一致。旧MrTree/Radial成功组未重跑，原证据及上游非有限结果分类保留。force foundation已开始，import/components源已分块接受；完整力模型、NS crossing/routing、全部typed/递归和公开注册仍在实施。完整算法验收数0；正式src仍为E11基础候选，许可选择与正式发行尚待落实。未执行全量。

E10已完成变更验收：Windows/Linux × CPython3.11–3.14八格wheel、Windows3.13与Linux3.14两份sdist代表安装、真实运行取消/恢复通过。三档各1预热+5正式公共性能样本，以及三份独立插桩通过；14项针对性测试、六份独审接受，未执行全量或旧矩阵重采。操作与限制见 [E10手册](E10_PLATFORM_VALIDATION.md)、[实际审计](../references/e10-runtime-audit.json) 和 [复盘](retrospectives/E10.md)。下一步 [E11正式候选](iterations/E11.md)，当前0.0.1a0未发布。

E09已完成变更验收：111项针对性测试通过，本轮未执行全量或三平台full；最终全量留全部迁移功能完成之后。当前43文件候选包含35个Python模块、7份许可通知与py.typed，真实日志/计时、181例旧布局回归、144例新矩阵和219项有限行为见证通过。完整算法及正式发布仍后置。见 [E09记录](changes/20261103-E09.json) 和 [手册](E09_BRANCH_COVERAGE.md)。

## E08及更早历史记录

E08已完成：受限公开API、1/9/1实例元数据及真实spawn异步/取消/关闭/恢复通过同一新wheel验收；Windows、Linux与Git过滤副本各844项完整检查通过。Windows/Fresh各1项symlink权限跳过，Linux0跳过且真实覆盖。见[E08记录](changes/20261103-E08.json)、[手册](E08_API_LIFECYCLE.md)与[复盘](retrospectives/E08.md)。下一轮按[E09 brief](iterations/E09.md)收口首版声明，尚未正式发布。

E08-00六项验收/协作改进已完成，完整检查 337.83 → 132.75 秒，减少 60.7%（2.54 倍）；审计 279.45 → 81.61 秒，减少 70.8%；请求对照 108.57 → 87.93 秒，减少 19.0%。 原688项全部保留，最终758项；下一步仍为E08公共API/生命周期。操作见[验收提速规范](EFFICIENCY_WORKFLOW.md)，结果见[批次记录](changes/20261103-E08-00.json)与[复盘](retrospectives/E08-00.md)。未修改生产包，尚未正式发布。

2026-11-03：**E07已完成：四方向、多连通分量和九项基础选项通过真实新wheel的72例同suite校验及旧52/36/21例回归，每端各3次；Windows、WSL Linux和Git过滤无缓存副本各688项测试通过，源码与测试指纹一致。尚未正式发布。** 实际命令、SHA、首败与复验见[最终记录](changes/20261103-E07.json)。

当前支持共0–8原始节点、最多28原始边、四方向/UNDEFINED及ORTHOGONAL，可选真实component拆分/打包或false不拆分。33组件独立来源续审已闭合；每分量19/21/23/25真实调用，单一共享RNG、原方向隐式端口、真实NS私有分量驱动与previous filling均有阶段证据。复跑见[E07手册](E07_DIRECTIONS_COMPONENTS.md)。

原图限定的DAG/严格简单环rank规则和独立component frame仅消除同层猜测误报，其他几何与原端点继续否决。当前新wheel完整Python/五许可/METADATA与README/pyproject绑定；E04/E05/E06旧包只作历史归档审计、不执行或回退。完整算法仍0，12/243/8/25分母不变；下一轮按[E08 brief](iterations/E08.md)处理API/元数据/错误与生命周期。

## E06 历史实验能力

2026-11-03：**E06已完成：真实Python `ELK` 环、自环、独立平行边及长边切片通过52例同包对照，Windows/WSL/Git过滤副本各597项测试通过；没有正式发布Python包。** 完整验收结果见[最终记录](changes/20261103-E06.json)。
本地`0.0.1a0`公开`ELK`与版本；支持0–8原始节点、最多28原始边、RIGHT/缺省、ORTHOGONAL的flat单弱连通图，完整边界与52输入复跑见[E06手册](E06_NATIVE_MULTIGRAPH.md)。输入/调用参数保留，每次独立工作图和RNG；async仍在调用线程计算，完整API/生命周期另行验收。

E06采用27组件逐项来源批准；普通图19调用，含自环23调用。实际破环/NS/拆并长边与四个loop阶段保留原边、端口、section及顺序，默认平行边不合并。134内部节点压力覆盖旧64界外分支；来源粗界176节点/196段/392端口，路由临时segment另计。新增显式简单环rank几何lemma和tiny NORTH逐次浮点负零测试。
E04/E05真实旧包与声明仅作historical审计，当前E06包须由自己新建的wheel、完整模块/全部许可和METADATA证明；不导入历史wheel作为fallback。实际Windows/WSL/Git过滤副本检查、同52输入至少3次双端比较及旧36/21例回归的命令与SHA保存到最终记录。完整算法数仍0，默认12/243/8及25master分母保留；远端CI未执行，未提交/推送或发布本轮变更。
下一轮按[E07 brief](iterations/E07.md)处理方向、组件及九项选项生效；[E06复盘](retrospectives/E06.md)的具体改进已纳入准备/所有权/反审规范。

源码仓库已核实为 [py-VisActor/py-elk](https://github.com/py-VisActor/py-elk)，默认分支main。
2026-11-03本地Git初始化并连接origin，以远端初始README提交`8288240963843e7295a55550c12eea30f3f72b67`为基础同步现有结构、工具和规划，保留历史。
源码提交不表示Python包已发布；实际推送与CI结果以GitHub对应提交/Actions为准。

2026-11-03新增实现策略与具体迭代规划：[实现策略](IMPLEMENTATION_PLAN.md#2a-python实现策略)、[21轮执行计划](ITERATION_PLAN.md)、[机器索引](iteration-plan.json)。
E01–E12交付基础正式包，E13–E21扩展全量能力，I0–I3仍为独立集成；E05实现DAG/长边，下一轮E06处理环/自环/平行边。最终完成状态、平台计数与命令以机器索引及本轮记录为准。
此前规划记录见 [20261103-implementation-strategy.json](changes/20261103-implementation-strategy.json)。

## E05 当前实验能力

新增一般DAG NETWORK_SIMPLEX、真实长边dummy与indexed恢复、两次LayerSweep、完整BK/ORTHO及端口/尺寸/margin/导出；22个固定生成worker组件逐项独立来源审查，所有proof依赖及修订完整基审均版本化绑定。
独立36输入=12个master原字节+24项目变体；原25分母/13排除理由及E04的21输入与原始收据保留。新wheel候选-I/空PATH、同36输入每端各3次通过公开合同exact、独立geometry与exact重复；同新wheel另通过原E04的21×3回归。
[当前安装收据](../references/e05-installed-check.json)、[运行审计](../references/e05-runtime-audit.json)、[复盘](retrospectives/E05.md)和[迭代记录](changes/20261103-E05.json)给出实际包SHA、源指纹、平台与限制。E04原包/声明归档审计明确不证明当前源码。
最终Windows CPython3.13.15、WSL Linux CPython3.14.4、Git过滤后的无.git/.local新副本各498项回归通过，代码指纹一致。官方25例重采/回放、合同探针、canonical来源和RNG采集独立步骤通过；首轮完整检查的旧fixture/文档链接失败均保留。E05已完成，nextIteration=E06。
完整算法通过数仍0；12算法/243选项/8类别分母不缩。环/自环/平行边、其他方向、多组件、公开ports/labels、compound、完整API/生命周期及正式发布门禁仍待后续轮次。本轮没有提交/推送或运行远端CI。

## E04 历史实验能力

从固定生成worker逐组件审查并移植真实默认链：空图leaf支路、非空19调用、13中间处理器、六次phase调用及生成RNG。来源gate只对[ADR0003](decisions/0003-e04-generated-source-slice.md)支持域verified，新增拓扑/策略/helper必须续审；精确外部Java build仍unresolved。
suite包含5个master原字节及16项目变体，原25分母与20排除理由保留；另12数值正例及1个有效Mapping padding负例。真实build03 wheel/sdist构建并安装，候选-I/空PATH执行；21例每端各3次通过公开合同exact、geometry和exact重复确定性，原strict差异保留。
实际wheel SHA为`7ebf9e042028bb4fdc3e73270066d398c285a1af2c5b2cb3cc7a39c5e30d95f7`；METADATA/模块路径、wheel/已安装包/当前src及许可字节已核一致。[安装历史收据](../references/e04-installed-check.json)、[runtime审计](../references/e04-runtime-audit.json)、[复盘](retrospectives/E04.md)与[完整本轮记录](changes/20261103-E04.json)提供可追溯证据。最终跨平台结果以本轮记录的实际命令与指纹为准。
最终Windows CPython3.13.15、WSL Linux CPython3.14.4、无.git/.local的Git过滤后新目录各400项回归通过，代码指纹相同；Windows另通过25例官方重采/回放、56探针、108个RNG方法向量采集和canonical源码复核。225份绑定文件Git过滤后字节一致；旧25请求/案例表及247份历史收据不变。V对新审计24项独立控制通过，历史wheel缺失时的离线不可独立认证限制明确保留。
兼容账本新增experimental，layered及最小constructor/layout/terminateWorker仅提升为受限实验能力；完整12算法/243选项/8类别不缩，完整算法验收数仍0，元数据查询未实现。项目发行许可、基础全域/API/生命周期/平台性能/正式候选与上传下载验收仍待完成。
未正式发布，未在本轮提交/推送或运行远端CI；CI配置不当作实际运行结果。

## E01–E03 历史记录

以下“未实现/未核实”保留为各轮结束时的事实；当前E05能力以本页上方和独立收据为准，不回写旧审计。

E03已实现Graph/Node/Port/Edge、typed ID/有序索引、深克隆/端点/尺寸/容器验证、九项解析schema和每调用工作图/state/快照；[来源与审计](../references/e03-audit.json)和[ADR0002](decisions/0002-model-options-context.md)区分固定源与宿主设计。
Windows完整集成276项回归、2项Node超时控制、25案例/56探针回放及canonical来源校验通过；真实数据基础对25份请求做输入分类，没有运行布局。最终状态/平台/新目录和SHA见 [E03记录](changes/20261103-E03.json)。
完成状态更新后，Windows CPython3.13.15、WSL CPython3.14.4及无.git/.local的新目录各276项离线再验通过，最终代码SHA一致。
[E03复盘](retrospectives/E03.md)的6项改进已用于[E04分工](iterations/E04.md)；反审修复了模型option容器遗漏、错误归属、CRLF/canonical路径及完整事实/schema/seal守卫问题。
`ordered-model-options`只核实宿主基础，`algorithm-source`仍unverified；随机流、公开API、布局、生命周期、并发/取消仍未验收，未推送/发布或运行远端CI。

E02已交付 [原生合同ADR](decisions/0001-native-contract.md)、[机器规则](../references/native-contract.json)、[56组官方探针](../references/e02-contract-probes.json) 与 [审计索引](../references/e02-audit.json)。
显式`native-basic-layered-v1`可执行，默认strict及原始差异保留；输入精确保留、有限形状`$H`投影之外的业务字段/section ID/顺序/坐标继续比较，几何与确定性单独否决。
root+A/B/V并行推进并互审；返回范围、采集清理超时、深层伪声明和证据/汇总守卫缺口已修复复验。[E02复盘](retrospectives/E02.md) 的7项改进已进入 [E03 brief](iterations/E03.md)。
Windows171项离线回归、2项Node超时控制、25例官方布局回放和56组合同探针回放已通过；完成状态更新后，Windows/WSL/无.git和.local的新目录各171项再验通过。实际SHA见 [20261103-E02.json](changes/20261103-E02.json)。CI配置已接入，未在远端运行。
`native-contract`仅为设计/工具gate verified；算法来源gate仍unverified，Python算法/API/生命周期尚未实现，没有正式包发布。

E01实际并行交付：root+A来源/B路径/V断言索引，包含 [来源链](../references/e01-source-lineage.md)、[默认路径](../references/e01-layered-path-notes.md)、[40项映射](../references/port-map.json)、[审计汇总](../references/e01-audit.json)。
固定Git/npm的12文件逐字节一致；Java候选已锁定，精确构建对应与逐组件来源/许可gate仍unverified。默认单边实测19调用，23请求/69个不同引擎进程/451对调用的完整结果相等。
Windows3.13.15、WSL3.14.4及无.local的新目录，各95项工具测试与来源/索引离线检查通过；Windows官方原参数重采回放和只读路径探针通过。新CI配置已接入，未把本轮写成远端CI执行成功。
并行规则已落地 [PARALLEL_EXECUTION](PARALLEL_EXECUTION.md)，反审发现的伪能力元数据、进度/evidence/span守卫缺口已修复并复核；[E01复盘](retrospectives/E01.md) 记录6项改进，已用于E02执行。
本轮没有Python算法/API实现、正式发行或算法兼容提升，记录见 [20261103-E01.json](changes/20261103-E01.json)。

本次新增真实官方布局验证工具：一键检查、独立进程JS/Python适配器、完整JSON差分、既定几何数值容差、平面正交几何、确定性、负控制和来源指纹校验。
25个自行编写案例的官方快照已保存，每例2次独立Node进程；新重采默认3次。
操作入口为 [NEW_SESSION](NEW_SESSION.md) 与 [LAYOUT_VALIDATION](LAYOUT_VALIDATION.md)。

2026-11-03实际验证：

- Windows / CPython 3.13.15：14项bootstrap、42项校验回归、25例官方快照与20项控制通过；Node 24.19.0真实重采/回放通过。
- WSL Ubuntu / CPython 3.14.4：离线一键检查已通过；具体最终命令、退出码与范围见本次变更记录。
- 安装的旧版本骨架缺少ELK时，真实candidate运行失败，原始ImportError/退出码留存，未生成成功布局观察。
- 所有Python算法/API/坐标兼容状态仍未实现；该早期记录的副作用适配问题现已在E02冻结为显式工具profile，运行时尚待实现。

证据和文件指纹见 [20261103-layout-validation.json](changes/20261103-layout-validation.json)。
CI增加工具自测/官方重采回放配置，未宣称远端CI执行成功。Python3.11/3.12和Windows3.14本轮未执行。

以下为2026-11-02项目骨架与来源验证记录，保留原有范围：

已建立：src 包元信息/类型标记和职责目录、pyproject/开发依赖、双语入口、M0–M8 及独立 I0–I3、
首版0.1.0范围/机器profile、兼容账本、来源工具、bootstrap/负控制、CI配置、范围查看例子。
当前 CI 是配置，未把它写成远端执行成功。

已真实核实的来源与范围：

- elkjs 0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`；npm gitHead一致，tarball integrity/SHA及12个发行文件固定。
- 64个elkjs Git文件含14个Mocha文件，11个关键canonical blob SHA固定；不是断言通过数。
- 官方bundled默认注册元数据为12算法、243选项、8类别；Python实现全部planned。
- bundled/FakeWorker调用terminateWorker实测TypeError，初次采集失败已保留；修订采集器明确记录throws，不称生命周期通过。

Java算法源码与生成worker的精确对应仍unresolved；自有发行许可待确定。
起点目录没有.git；预期组织仓库访问未核实，未宣称创建/发布/推送成功。

本轮验证记录见 [20261102-project-structure.json](changes/20261102-project-structure.json)。
来源检查、结构/负控制、元数据重采与本地骨架打包的实际命令、退出码和SHA各自记录；
它们不能提升任何算法为已实现，也不满足正式包的真实布局门禁。

本轮实际限定验证（Windows / CPython 3.13.15 / Node 24.19.0）：

| 检查 | 实际结果与范围 |
| --- | --- |
| bootstrap 与负控制 | 14项测试通过，包括分母删除、伪验证、缺证据、元数据/来源漂移、archive越界及首版集成依赖错误 |
| 上游来源 | 固定Git提交/关键blob、64文件索引和npm发行文件核验通过 |
| 官方元数据重采 | 默认12/243/8原始目录与保存快照一致，terminate异常独立记录 |
| 本地骨架构建 | wheel/sdist构建通过，未上传 |
| 隔离安装/导入 | 新环境、仓库外-I、移除PATH/PYTHONPATH/PYTHONHOME；包从site-packages导入，只公开版本信息 |

Linux及Python3.11/3.12/3.14本轮未执行；CI矩阵不替代实际结果。没有任何Python算法/API/坐标通过数或正式发布结论。

当前优先顺序是M1–M4独立基础功能/候选验收 → M5正式Python包0.1.0发布 → 后续M6–M8扩展。
py-mermaid集成单独后置I0–I3，不作为基础包发布前提，也不维护旧ELK兼容分支。
