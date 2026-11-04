# E09 首版分支声明与验证

本页记录 E09 实现的基础包有限声明和验证流程。最终完成状态及平台屏障以 [机器计划](iteration-plan.json) 和 [状态页](RELEASE_STATUS.md) 为准，不代表完整 ELK Layered、正式发布或 py-mermaid 集成已经完成。完整参考目录保留 **12 算法 / 243 选项 / 8 类别**，项目自编的 **25 个 master 请求**全部保留；这些请求不是上游完整测试集。

## 三种证据分别回答什么

1. [固定来源](../references/e09-diagnostics-sources.json)保存 elkjs 0.12.1 固定 commit、文件 SHA、40 个精确行段及其原始字节。独立来源复审的原 JSON 和审阅材料字节保存在[来源批准](../references/e09-source-approvals.json)及其引用的版本化文件中。离线门不需要 `.git`、`.local`、Node 或历史 `test-runs`。
2. [机器分支清单](../references/e09-branch-matrix.json)固定 **38 项声明 / 219 个枚举分支 / 25 个 master 分类**，对应真实实现符号、含断言的测试方法、来源组件和未来同包证据位置。这里的“分支”是有限产品行为的枚举项，不是 Python 字节码覆盖率。存在一个测试引用不等于该分支已经在候选 wheel 上执行。
3. 当前 wheel 的几何、API/生命周期和新增诊断/生成请求证明，必须由运行审计独立重算。结果及实际 receipt SHA 写入独立运行审计，不能回写来源事实或本清单来制造完成状态。

`sourceApproved: true`只表示有限来源子集已有原始独立复审和 ADR0008 授权。脚本还逐项核验 40 个不可自重绑的来源 seal、独审范围、原材料、许可及完整批准分母；不能单凭该布尔值宣布运行通过。Number 字符串适配器属于原创宿主代码，需要独立固定 Node 边界与 round-trip 对照；不存在可冒称已经机械移植的 elkjs 专用 Number formatter 源码。

## 声明边界

首版只注册原生 `org.eclipse.elk.layered`，默认查询为 **1 算法 / 9 选项 / 1 类别**，注册与返回值在实例间隔离。`algorithms=[]`仅提供元数据查询：算法、类别为空，九项解析选项仍可查询，布局明确拒绝。未知算法与已知但未实现算法分别报错，实际 resolver 会解析的全局与局部 selector 均分类。

布局域由 [release-profiles](release-profiles.json)、[FIRST_RELEASE_SCOPE](FIRST_RELEASE_SCOPE.md) 和真实 admission 共同限制：0–8 个原始 child、0–28 条原始边、平面有向多重图、非空字符串 ID、给定且有限非负的节点尺寸、尺寸/spacing/padding 不超过 1,000,000、非零 signed32 seed（省略为 1）。支持四方向、默认 UNDEFINED、分离或合并弱连通分量、环、自环、平行边，以及已审核的叶节点四边 padding。端口、标签布局、嵌套图、超边、未实现选项/算法、既存几何与其它未审输入明确拒绝。

九项选项各声明默认、完整 ID、`elk.*` 别名、有效值与无效值分支。constructor 默认与 call 的替换关系、显式空 call、root-local 优先级、同 scope 别名冲突单列。25 个 master 请求在采集前固定为 22 个支持请求和 3 个预期错误请求，分类不由候选结果反推；原请求 SHA 逐项锁定。

## 日志和时间的精确含义

`logging` / `measureExecutionTime`允许省略或 bool，四种交叉组合均须真实执行；其它类型拒绝。**仅返回根的 `/logging` 为保留字段**：成功布局在副本上删除原值，任一 flag 为真时重新生成树。节点/边/嵌套业务字段的同名 `logging` 以及根业务 `executionTime` 均保持原值。失败路径不伪造成功监视树；输入、constructor、arguments 均保留。

树来自真实 `begin/sub_task/done`，不能从阶段 trace 拼装。空图只有 `Recursive Graph Layout`；单分量直接进入 `Layered layout`，多分离分量增加实际 `Component Layout`；合并分量不增加该 wrapper，但可有多个 Network simplex 子监视器。阶段顺序、重复 crossing 阶段、自环额外阶段、方向变换的固定字面名称、BK 动态日志与 marked-edge 首次成功 add 顺序都必须保留。

固定生成代码读整数 wall 毫秒 tick，做 long 整数差乘 1000，再按源乘法顺序乘 `1e-9`。Python 等价实现是 `float((end_ms - start_ms) * 1000) * 1e-9`，tick 用 `time.time_ns() // 1_000_000`。**这不是 CPU 时间，也不是通常以秒表示的 wall 耗时**。零值与时钟回拨产生的负值不钳制；禁用计时时不读 clock。实际测量值不作跨进程、跨语言数值相等断言。

非空图的 Recursive 监视区间包含 provider 的实际 import 和 LGraph 布局回写，Layered 区间包含组件布局/组合/resize，但不包含 provider import/回写。Python 的模型/JSON 转换部分融合，按真实 native 操作边界设置监视器，不声称转换成本或计时数值与 JavaScript 相同。D40 保存此调用链的额外来源；空图不进入 provider。

## 当前包验收位置

新增矩阵为144个请求：25原master及其三组诊断开关派生共100例、24个固定seed生成图、8个业务字段隔离例、12个既有压力图诊断例。其中132个返回、12个预期错误；3个原错误仍完整保留，不混入成功布局数。每引擎各三次真实采集，另外三个 installed host probe 验52个公开边界请求/298个数字字符串及可控原语，三个 lifecycle probe 验真实运行超时/恢复和明确标注的私有故障注入。合成clock及kernel instrumentation只证明相应内部合同，不能替代实际布局壁钟或公共生命周期。

静态表共38项声明、219个有限行为枚举；[映射清单](../references/e09-branch-evidence-map.json) 将每项接到原始实际观察、case/probe、字段及断言。纯校验逐项重算，缺项保持pending；219并非字节码路径覆盖率，也不是所有图/浮点值的数学证明。

| 角色 | 固定 portable 位置 | 纯校验入口 |
| --- | --- | --- |
| geometry | `references/e09-installed-check.json` | `validate_e08_runtime.validate_layout_receipt` |
| api | 上述 JSON 的 `/apiRuntime` | `validate_e08_api.validate_candidate_receipt` |
| newcoverage | `references/e09-coverage-installed.json` | `validate_e09_coverage.validate_candidate_receipt` |

三角色必须有完全相同的 installed wheel 文件清单、METADATA 和解释器身份。实际包含35个Python模块、7份许可/通知和py.typed；仓库内另外6份README不属于wheel文件分母。捕获前及最终复验均先检查真实安装身份、完整文件及非源码路径。Windows venv可能有中间启动器，合法直接子进程和shim关系分别核验，不能用Popen.pid与engine.pid恒等假设，也不能把仍活的launcher自身当成新子进程。

## 离线重核与真实新执行

仓库根目录，CPython 3.11+，以下离线命令不依赖Node或.local缓存；每次使用新输出路径：

```shell
python scripts/validate_e09_sources.py
python scripts/validate_e09_coverage.py
python scripts/validate_e09_branch_evidence.py --out test-runs/session-e09-branches-01.json
python scripts/validate_e09_runtime.py --out test-runs/session-e09-runtime-01.json
python scripts/check.py --out test-runs/session-e09-full-01
```

branch CLI先全验实际收据，再逐219项判断；runtime入口另核审批、当前包、源码继承、声明与全部强连接。它们重算原始字节的一致性，不声称重新执行或认证历史。新的同wheel布局/API/诊断采集与portable导出步骤见 [LAYOUT_VALIDATION](LAYOUT_VALIDATION.md)，完整入口为35步，含官方重采为54步。

## 独立几何规则与保留失败

官方 generated-10 的边n6→n0两端不同NS rank，但轴坐标相差1e-7，旧v2同层推断会误报。原始Node请求、观察、命令和日志封存在 [regression材料](../references/e09-geometry-regression.json)。经独立固定源码及实际callee复审的 [G01证明](../references/e09-geometry-premise.json) 只对原非self邻接端点追加不同rank事实；E09专用v3不改变旧v2、原请求、1e-6/1e-9容差、真正同层间距、重叠、端点或其他几何否决。候选自行新增的边不能提供原图前提。

本轮前两批完整采集及其来源快照均保留：第一批新coverage因错误计入6份未打包README而失败；第二批正本虽通过，独立重绑反例仍发现PID关系过宽，因此未作最终门禁。最终03在修正后的冻结源上重新实际采集，旧sourceSHA与原始字节从未重绑。单纯验证器变更也触发重采的成本单列复盘，采集与纯验证源码拆分作为E10待验证方案，不计作已经实现的提速。

运行审计连通三个角色的完整 `installed` 收据与实际 candidate 解释器，逐原请求重算。E09 复用 E08 的共享执行协议并实际重采当前包；旧 wheel 只认证历史。实际命令、原始观察和独立复验分别保留，本页静态表本身不证明执行。

## 新会话命令

从项目根目录使用 Python 3.11+，输出路径每次换新：

```shell
python scripts/validate_e09_sources.py --out test-runs/session-e09-source-01.json
python scripts/validate_e09_sources.py --branch-matrix --out test-runs/session-e09-declarations-01.json
python -m unittest discover -s tests/audit -p test_e09_sources.py -v
```

第二条还检查固定声明 ID/分母、全部真实 Python 符号与测试断言、当前 profile 与 metadata、三类证据位置及纯验证函数、25 个未改请求；静态声明门不读取实际候选收据。实现/验证函数缺失时明确失败，不跳过。

已具备固定上游缓存时可额外核真实原文件和 Git blob：

```shell
python scripts/validate_e09_sources.py --with-upstream --branch-matrix --out test-runs/session-e09-upstream-01.json
```

全项目与安装包/跨平台屏障由 root 在源码、工具、清单及独审冻结后执行。`python scripts/check.py --out test-runs/session-e09-full-01`是项目既有全检入口；首版完成还要求同包运行审计、必要平台结果、声明对齐和复盘，不能以本页的静态门替代。
