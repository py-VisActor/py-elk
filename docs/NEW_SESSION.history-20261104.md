# 新会话入口

完成审计补充（2026-11-04）：37 步／917 测试是冻结开发检查通过，不能代替所有 E11–E21 退出条件。当前补当前 0.1 包逐算法性能/峰值内存、243 选项效果/状态账本、独立高级几何与干净 Git checkout 验证；PyPI 配置和上传下载仍待完成。算法实现不重做，已过数学组不重跑。详见 `docs/implementation-backlog.json`。

当前发行状态（2026-11-04）：完整迁移及冻结全量校验已通过（37 步／917 测试），正式源码为 `0.1.0` 候选。仅版本字面值的运行差异已核，新 wheel/sdist 双安装已验。详见 [0.1.0 发行收口](releases/0.1.0.md)；剩余为 PyPI 配置、上传及下载复验，尚未发布。下方执行中与旧切片说明按其历史日期理解，不要重复实现已完成的功能。

当前状态（2026-11-04）：[完整实现已合入正式 src，进入统一校验与集中修复](FULL_NATIVE_IMPLEMENTATION.md)。196 个 Python 模块语法/导入通过；12/243/8 完整接线尚未代表正确性通过。`.local/migration-next` 已冻结；本阶段修复直接改 `src/pyelk`。下方旧私有批次与切片状态仅按其日期作历史记录。

**最新策略已切换为[先完成全部功能，再统一校验与修复](IMPLEMENTATION_FIRST.md)。** 用户要求加快进度，覆盖下方历史的逐模块源审/代码门禁/原版采集安排。A 实现全部 Layered 中间处理器与工厂，B 全 P1/P2，V 全 P3/P4，Root 公共 API/registry/其它算法整合；只做语法/导入/接线检查，所有新增实现未验证。完整分母不减，py-mermaid/绘图仍后置；18 批归档保持原事实。

最新 [18 批](changes/20261104-next-native-18.json)：191 文件 `fede8e4c4cad221df3800d36396f685280c8d7f89f96a7c7c269c41356e580c0`，1760 份新增材料、16 份限定代码审查。Polyline、两种 LongestPath、DepthFirst、Simple、端点标签和中心标签共 7 个新增完整 caller 通过，保留各自原始形状哈希差异；标签 prepared 与全调用的证据分开。纯绑定检查 0.262681 秒、0 产品执行。按 [19 brief](iterations/NEXT_NATIVE_19.md)推进 Coffman–Graham、comments、其它 P1 及默认值桥；使用方法见[18 校验入口](iterations/LABELS_PHASE_STRATEGIES_VALIDATION.md)、[复盘](retrospectives/NEXT_NATIVE_18.md)。完整算法仍 0、正式 src 仍 E11，未全量/未发布；本阶段不新增绘图校验。下方 17 及更早为历史。

最新 [17 批](changes/20261104-next-native-17.json)：183 文件 `7325ae72993e9f7822473c2596108b92553b60588a4fd75b8ba5739e5c2188ee`，1333 份新增材料、10 份限定代码审查。真实完整 compound（300×82）、DOWN、组件压缩和关闭日志的最小 SPLINES 已接实际注册/池/阶段；原始形状哈希差异分别保留，Spline logging=true 原版日志收集 NPE 仍待，旧 external 顺序 23 项未关闭。P5/Final 已代码审；Polyline 和 center-label 在本快照仍为未验草稿。先读[校验入口](iterations/NATIVE_COMPOUND_COMPACTION_SPLINE_VALIDATION.md)、[复盘](retrospectives/NEXT_NATIVE_17.md)，按 [18 brief](iterations/NEXT_NATIVE_18.md)继续。完整算法仍 0、正式 src 仍 E11，未全量/未发布。下方 16 及更早为历史。

最新 [16 批](changes/20261104-next-native-16.json)：171 文件 `b7b30ba0f73a81141ee44942f2d9e49e5c56082556a90800c3defb3772007c51`、928 份新增材料、9 份限定代码审查。层级导入、compound pre/post、层级尺寸、Spline foundation/ranking、矩形凸包与正交南北轴已按范围验收；Spline 主流程含未执行草稿，首次 gap 的 10 项配置差异保留。完整 compound、Spline Final、connected compactor 继续实施。先读[校验手册](iterations/HIERARCHY_SPLINE_COMPACTION_VALIDATION.md)和[复盘](retrospectives/NEXT_NATIVE_16.md)，按 [17 brief](iterations/NEXT_NATIVE_17.md)继续。独立重写文件采用 MIT，仍按实际来源逐文件分类；完整算法仍 0、未全量/未发布。下方 15 及更早为历史。

最新 [15 批](changes/20261104-next-native-15.json)：162 文件 `8ef85d93156d168fc065414e7cbebc0070609bc76b5deb9671f5325cf8f92aa6`、799 份新增材料、13 份限定代码审查。真实默认 19 阶段、自环 23 阶段已走私有注册表/RGE/池，几何、日志、业务严格一致，原始四项生成 `$H` 差异按既有 ADR 单列。CGraph、基础间距、NubSpline 已限定验收。见[校验手册](iterations/LAYERED_FULL_VALIDATION.md)、[复盘](retrospectives/NEXT_NATIVE_15.md)，按 [16 brief](iterations/NEXT_NATIVE_16.md)继续 hierarchy/compound、general Spline 和 connected compactor。完整算法仍 0、未全量/未发布；下方 14 及更早为历史。

最新 [14 批](changes/20261104-next-native-14.json)：154 文件 `3d6e0431fd40b03ba52b5dc28e420f222d6df9f47dc7fb122df16e6cfa8cf4ef`、366 份新增材料、10 份限定代码审查。通用 adapter 数值修复、enum/map、外部三 placer、自环 foundation/pre/post/side assignment 已按范围独审；外部普通首例 23 项顺序差异仍保留，未宣称整体通过。见[使用方法](iterations/EXTERNAL_COMPONENTS_VALIDATION.md)、[复盘](retrospectives/NEXT_NATIVE_14.md)，按 [15 brief](iterations/NEXT_NATIVE_15.md)继续真实完整默认调用与自环 router。完整算法仍 0；下方 13 及更早为历史。

2026-11-04 用户已明确选择项目原创代码 **MIT**，根 LICENSE、机器决定与 pyproject 已落实；第三方移植许可、版权与通知保留。见[许可决定](E11_LICENSE_PROPOSAL.md)和[定向校验](iterations/LICENSE_VALIDATION.md)。下方“等待许可选择”均为旧状态，不再向用户重复确认。稳定版本、剩余迁移及实际发行验收继续推进。

最新固定 [13 批](changes/20261104-next-native-13.json)：146 文件 `1c086f0651c288c3086144c24cca544adebbb35aa82cd707ba36bdc676b1c4d7`、259 份新增材料、8 份限定代码审查。全局 optsToCfg 与新 Box 消费者、通用组件 split/SimpleRow、cleanup/resize 已按范围验收；使用方法见[全局配置](iterations/GLOBAL_OPTIONS_VALIDATION.md)、[组件与尺寸](iterations/COMPONENT_RESIZE_VALIDATION.md)。两处观察器修正保原失败，只复核保存数据；超长键/大整数修复另有单例执行。按 [14 brief](iterations/NEXT_NATIVE_14.md)继续真实完整默认调用、完整导入和高级组件分支。完整算法验收仍 0，下方 12 及更早内容为历史；开发仅变更校验。

当前最新 [12 批](changes/20261104-next-native-12.json)固定 138 文件 `9428b606012a93a163977ee57c23f8072d5860aa3a87dcf9be79976246e99c0f`，新增 356 份材料、7 份限定代码审查。选定注册集/legacy 元数据、两份 Box 集成及通用 NS/BK/Orthogonal 指定工作图已验。BK 原进程失败与观察器修正分别保留，未重跑整组。按 [13 brief](iterations/NEXT_NATIVE_13.md)继续 Full Layered、原生 adapter 和全局 optsToCfg；使用方法见[元数据手册](iterations/METADATA_REGISTRATION_VALIDATION.md)。完整算法验收仍为 0，开发只做变更校验；下方 11 及更早内容为历史。

最新 [11 批记录](changes/20261104-next-native-11.json) 固定 126 文件 `e482a49e1453cc9c866947053c1ee539769df160badef1e280f6be6d388afd9a`。真实普通递归两例、Topdown、DisCo→Fixed 共享池均严格对照通过；14 个 local import DTO 与实际属性 presence 已独审。Topdown 首次失败已修，原失败仍保留。按 [12 批 brief](iterations/NEXT_NATIVE_12.md) 继续：A 接 Layered 动态流水线，B 接通用 Network Simplex，Root 继续 registry/属性与入口，V 独审。下方 122/105 等段落为历史状态，不能用其失败或 pending 描述覆盖本段，也不能把旧执行重绑新源码。

11 批递归协调器最新执行状态见[协调器变更校验](iterations/RECURSIVE_COORDINATOR_VALIDATION.md)：7 个 helper、12 项 feature 与 provider pool/deprecated 已代码独审；普通递归和 Topdown 实现正在接真实原版轨迹。122 文件 `d6c65fc1…` 首候选实际在本地 padding 解析阶段失败，原始失败已保存；不能据此声称协调器通过。B 正在闭合 inside-loop 并修本地导入边界，A 推进完整 Layered，V 独审。下方较早的 105 文件段落是历史进度，不代表当前工作区，也不能重绑旧执行。

11当前先行固定105文件`baa16153805f8f16f7386ff6101e2cd10945df5c4f693942c188ff09be0707a7`：Root实际Basic monitor恒false取消接口、RectPacking完整私有body/同会话路由均已独审；RP两份新原/候选请求通过，后验共享EnumSet getter单叶另有独立控制，不回绑5782执行。A的b1df完整plain Bary阶段已独审，后续真实ModelOrder成本首原对照通过但统一代码审仍在推进。B已转写独占`execution/recursive_helpers.py`、`metadata/_feature_data.py`与resolver仅features部分，feature/count/继承和scale/childArea新owner控制通过，完整小原控/Root代码独审待收；这些后续文件尚未固定进105。Root负责闭合完整visitor/pool/loops/topdown/递归并审B的helper，V已批7helper/12声明不代表全coordinator已批准或实现。最新完整归档仍是下方10，工作区更晚数学各保自己的源码收据。

最新完整[10归档](changes/20261104-next-native-10.json)：固定104文件`e41ac8821aca65ce50215904ffc0a08a228916df8632f99123ca313a1e9e1bc5`、170份原始证据、8份范围限定代码复审；[变更校验](changes/20261104-next-native-10-change-validation.json)通过。真实MODEL_ORDER producer、232条显式owner声明/scalar读取、per-node算法resolver和DisCo同会话入口已独审；仍非完整导入/递归/公开包。现在按[11 brief](iterations/NEXT_NATIVE_11.md)继续。A后续b1df完整plain Bary工作图阶段已新原控/代码独审，B的后续whitespace/Compactor正在推进，均保各自source/execution而非回绑104。下文10先行段和09及更早段落为历史。

10先行：MODEL_ORDER真实producer已实现，16个needs分支和实际flat-import节点/端口/边guard顺序、MAX及非空CB分组计数均已新原控/首候选严格0差异。固定100文件`38a8700b46dfa191e82acd9c08741ef8c4250ca197dbc584e382c7a9afebddc7`，源审接受、代码独审中；新原收据`test-runs/20261104-HOST-10`。这里只接真实producer与native属性/token，transform callbacks的完整geometry/endpoint实现仍待，不能称完整import或布局。独立owner默认表提取由A先核源，dev生成器必须有accepted行范围与hash gate后才可输出，未应用为runtime默认。完整固定归档仍是下方09。

最新[09批](changes/20261104-next-native-09.json)已归档：固定99文件`05a3920472313b4e00e82256d81c803f5d82213f3bfa00d8fcc80f5d1b0dd73a`、203份原始证据、11份范围限定的代码独审。junction/default/Integer宿主桥已通过新增定向对照；[归档绑定校验](changes/20261104-next-native-09-change-validation.json)仅核字节与声明范围，不执行产品。按[10 brief](iterations/NEXT_NATIVE_10.md)继续真实producer、sweep/递归及完整packing，10进展见顶部。下文09先行段与08及更早记录均为历史，实际工作区可领先固定快照。

09共享增量先行：junction typed/Fixed/Box/export桥六个新场景与真实Fixed请求已对照通过；Snapshot/Session默认入口已独审接受。Box/Fixed实际caller已物化padding15，Spore物化8，后续owner共享已存值。Integer解析/显式赋值token桥新增真实原版对象矩阵与首个候选严格0差异，并已源/代码独审；后验类型guard另有五负一正控制。当前固定99文件`05a3920472313b4e00e82256d81c803f5d82213f3bfa00d8fcc80f5d1b0dd73a`可恢复；完整批次归档仍为08，09原收据在`test-runs/20261104-HOST-09`，不要重绑旧快照。继续按[09 brief](iterations/NEXT_NATIVE_09.md)：接MODEL_ORDER真实producer、sweep/递归。A/B后续Source/Code交付各有独立收据，不能据文件数视为整个算法验收。

最新[08批](changes/20261104-next-native-08.json)固定96文件与212份原始证据：私有Session已接243项类型登记，235项可从raw值构造，另8项保留原版无构造器诊断并允许内部typed值。实际Core标量默认68项、浅属性快照、position/向量链已独审；基础/NS/Hyper计数、DisCo判定、grid/raster及Drawing/Row的所声明小块已分别验收。完整owner默认/Integer盒provenance、真实sweep/递归/公开包仍未完成，公开仍9选项、完整算法验收0。09已开始，工作区可能领先固定快照；按[09 brief](iterations/NEXT_NATIVE_09.md)继续，不重绑08执行。下方07及更早段落均是历史状态。

最新[07批](changes/20261104-next-native-07.json)固定90文件检查点`ab674459c82b0acbb082b4d1536afac46adecb62c6a7c5448a20bb724748fd15`及82份原始证据，SweepCopy、Core默认隔离、225项静态声明与独立显式解析器已源/代码独审。10个新原解析小样例严格对照通过。解析器尚未接Session/公开入口，不能据此修改63/9的运行声明。接手见[通用属性手册](iterations/GENERIC_PROPERTIES.md)，下一批按[08 brief](iterations/NEXT_NATIVE_08.md)并行；下方06及更早内容是固定历史，不重绑旧执行。

用户最新规则：持续goal完成剩余E09–E21迁移；[变更校验政策](VALIDATION_POLICY.md) 优先。开发只运行变更相关校验，全部功能完成后再统一全量；下文旧逐轮full要求不再作为当前收口前置。

E09已完成变更验收：111项针对性测试通过，本轮未执行全量或三平台full；最终全量留全部迁移功能完成之后。当前状态以 [机器计划](iteration-plan.json)、[状态页](RELEASE_STATUS.md) 和 [E09记录](changes/20261103-E09.json) 为准。正式0.1.0发布仍未执行，py-mermaid集成是独立后置步骤。

本机实际项目为 `C:/code/py-visactor/py-elk`，环境可能仍显示旧py-mermaid目录；命令先设正确workdir。保留既有未提交变更。完整算法通过数0，参考分母12算法/243选项/8类别、25master全部保留。

最新[06批记录](changes/20261104-next-native-06.json)固定87文件检查点及389份原始证据。共享层新增margin-only、最小尺寸查询、同会话provider调用、标识符文本和DOUBLE存储；EnumSet默认/全局共享及resize后的可变属性身份已按真实源修正。Spore overlap/compaction两个新增完整私有请求通过有限几何和业务对照；A的barycenter/Forster/model-order/port-rank/distribution内核已独审，完整crossing仍待闭合。操作见[共享运行层手册](iterations/HOST_DELTA_VALIDATION.md)。私有schema63项，公开仍9；243项原元数据采集不是完整运行支持。05及下文04批均为历史固定快照，不重绑其执行SHA。

2026-11-04同步推进E13/E16/E17与E18，代码与恢复方法见[migration/next-native](../migration/next-native/README.md)，当前保存71文件检查点。最近[本批记录](changes/20261104-next-native-04.json)固定源码、原始对照与独审。先前MrTree4例及Radial2个有限几何/1个上游非有限wire例保持原证据，不重绑新SHA。本批新增NS helper三例严格一致、属性helper两个分支一致、Box全局选项一例一致及binary64几何两例一致；这些都不是完整算法验收。正式src仍为E11基础候选；E13/E16/E17/E18机器状态仍planned，完整算法验收数0。项目许可选择未收到前继续技术迁移，不能把预选推荐当答复。

私有schema现为63，正式仍9。Core portAlignment=DISTRIBUTED而真实Layered覆写JUSTIFIED；IndividualSpacings分隔为精确`;,;`。Session的has/set/remove与generic reader共用存在性；False/0、targets、删除遮蔽及clear后新赋值均有针对性证据。Vec/Insets默认按元素物化，EnumSet默认则共享且读取不产生presence；显式global EnumSet也共享，不能套用统一深复制规则。randomSeed Core默认None与Force1分开。几何及已声明DOUBLE在输入finite校验后采用binary64，整数ID和业务原值保留。完整属性注册、Integer盒身份及递归仍待继续。最终wire映射生成的非有限值，见[微布局手册](iterations/NODE_MICRO_VALIDATION.md)、[identity决定](decisions/0010-native-object-identity.md)、[wire决定](decisions/0011-source-json-wire.md)。

下一步root补完整属性注册、Integer盒身份、递归/注册/高级诊断；A接SweepCopy、真实counter/sweep与routing调度，不能仅删guard；B接DisCo polygon/raster/Polyomino及完整RectPacking。Force/Stress的05批小样本已接受，不重复执行。V按新source块、代码和新原控独审；root归档与各owner实现并行，采样用独立恢复副本。Stress显式desiredEdgeLength使用`Session.has_option`区分，不读references当runtime数据。

当前原生包提供0–8原始节点/最多28边的平面layered、四方向、多组件、环/自环/平行/长边及9选项；尺寸、padding和间距≤1e6，非零signed32seed默认1。高级ports/labels/compound、预存几何、其它routing/算法明确拒绝。具体见 [首版范围](FIRST_RELEASE_SCOPE.md)、[机器profile](release-profiles.json) 和 [E09手册](E09_BRANCH_COVERAGE.md)。

E09实际新增monitor树、BK实时日志和计时四组合；根logging保留，嵌套业务字段不删。计时沿用固定生成源的整数wall-ms差×1000×1e-9，不能按普通秒/CPU解释。旧profile和容差未变；G01专用v3只修官方1e-7邻接rank误判，旧v2仍保留。

先读 [实现策略](IMPLEMENTATION_PLAN.md)、[迭代计划](ITERATION_PLAN.md)、[校验手册](LAYOUT_VALIDATION.md) 和 [并行规范](PARALLEL_EXECUTION.md)。从机器计划读取active/next；E01–E12先交独立基础正式包，E13–E21扩展全量，I0–I3单列。每轮root+A/B/V单文件owner、首个真实小交付、独审、变更校验和复盘；所有功能完成后再全量。

E10已完成：八格wheel、两个sdist代表、18公共性能和三个独立插桩样本通过，14项针对性测试及六份独审接受。E11已开始修正许可，旧E09/E10候选已冻结为历史材料；需要重核旧候选时用 `python scripts/iteration/e11_history.py --out test-runs/e09-e10-history-new.json`，该入口不执行旧包、不认证当前产品；不要用旧当前审计要求新源码退回旧SHA。当前进入 [E11候选](iterations/E11.md)，先读已完成的 [许可盘点](iterations/E11-license-inventory.json) 与 [许可拟案](E11_LICENSE_PROPOSAL.md)。Apache正文/归属与对应package-data已补，项目自身许可选择仍待落实；正式版本/包尚未发布。

开发期只执行本批manifest选中的命令；不要将以下完整审计配方作为每次进入会话的启动步骤。最终全量入口（全部迁移功能完成后使用）是：

```shell
python scripts/check.py --out test-runs/session-full-01
```

本轮Windows实际解释器为 `C:/code/ppt-compare/.local/tools/python-3.13.15/python.exe`；Linux为WSL Ubuntu CPython3.14.4。复制环境时按实际解释器重测，不把两个版本当完整3.11–3.14矩阵。输出路径每次换新。

当前证据在 references/e09-runtime-audit.json、e09-installed-check.json、e09-coverage-installed.json。geometry/API/newcoverage必须完全同wheel/METADATA/解释器；219是有限行为见证，不是全路径或全部图的证明。静态表不代表执行，纯校验不声称重跑或认证历史。采集命令见手册，不能只更新hash或用旧wheel认证新源码。

E04–E08使用相应validate_e0N_runtime.py --historical；不导入执行旧包。新代码、采集器、输入、包/README/METADATA变更需相应重采。验收脚本全源context较粗，E09已保留三版真实运行及所有失败；E10再验证拆分capture/pure-checker方案，不能倒改旧执行源SHA。

E10安装/平台矩阵已完成，不作为新会话启动步骤。正式发行/许可/账号/上传仍按E11/E12，集成后置；后续工作顺序以顶部当前批记录和机器计划为准。
