# 布局比对与校验操作手册

本页描述已经存在的脚本。当前没有 Python `ELK`/布局实现，工具自测或官方重采通过不表示 Python 布局通过。
唯一行为基线为 `UPSTREAM.json` 固定的 elkjs 0.12.1，Node 只用于研发采集。

## 新会话先运行

仓库根目录，CPython 3.11+，无需安装依赖、Node 或网络：

```shell
python scripts/check.py --out test-runs/start-01
```

执行结构/来源快照检查、bootstrap、比较器回归、官方正例和破坏负控制。
`DEVELOPMENT_CHECKS_PASS` 表示研发工具通过，`pythonAlgorithmsVerified` 仍为 0。
每次换新输出目录，既有目录/文件不覆盖。汇总为 `test-runs/start-01/report.json`，原始日志在各 `*-command` 目录。
Windows、Linux 均从仓库根目录使用相同 Python 命令。

有 Node/Git 时，一次完成官方重采与回放：

```shell
python scripts/upstream.py fetch
python scripts/check.py --with-reference --out test-runs/start-oracle-01
```

首次 fetch 使用网络并核验固定 Git/npm SHA，后续复用 `.local`。
`--with-reference` 每例启动 3 个独立 Node 进程，比较原始结果、几何与确定性；不调用 Python 假布局。
Node 版本记录在每份 observation；保存的官方快照来自 Node 24.19.0。

## 工具和实际范围

| 工具 | 实际工作 |
| --- | --- |
| `scripts/check.py` | 新会话一键检查，保存实际命令、日志、退出码和源 SHA |
| `scripts/validate_layout.py reference` | 校验全部发行文件，独立进程采集 graph/错误/副作用/关闭观察 |
| `scripts/validate_layout.py candidate` | 调用指定 Python 适配器；缺 API、超时、非零退出为采集失败 |
| `scripts/validate_layout.py compare` | JS→Python 差分、双方重复确定性、独立几何 |
| `scripts/validate_layout.py replay` | 两份官方采集的重现检查，不计 Python 通过数 |
| `scripts/validate_layout.py selftest` | 官方正例和破坏坐标/字段/端点/顺序/seed/错误等负控制 |
| `scripts/validate_layout.py pair` | 两个 observation 的完整 JSON 差分，仅用于排查 |
| `scripts/validate_layout.py json` | 任意原始JSON/元数据完整比对；--kind graph可应用几何数值容差 |
| `scripts/validate_layout.py verify` | 文件 SHA、案例/重复次数分母、输入指纹和引擎身份 |
| `scripts/generate_validation_cases.py` | 在新目录生成自行编写的输入，不生成预期坐标 |

当前为 25 个项目自行编写案例：22 个成功布局、3 个错误案例。覆盖空图、单节点、链、分叉/汇合、四方向菱形、长边、环、自环、多边、断开组件、不同/零尺寸、padding/spacing、组件分离开关、9 个首版选项的完整 ID、构造缺省与调用选项替换、未知端点/算法和缺失 graph。
这不是完整上游断言清单或 243 选项兼容率。输入见 [cases.json](../tests/fixtures/validation/cases.json)，真实结果见 [index.json](../references/layout/index.json)。

## 官方采集与重现

```shell
python scripts/validate_layout.py reference --out test-runs/oracle-01 --repeat 3
python scripts/validate_layout.py verify test-runs/oracle-01
python scripts/validate_layout.py selftest --reference test-runs/oracle-01 --out test-runs/controls-01
python scripts/validate_layout.py replay --reference references/layout --candidate test-runs/oracle-01 --out test-runs/replay-01.json
```

`--package` 默认 `.local/npm-elkjs/package`，`--node` 默认 `node`。每次采集核对锁里的全部发行文件，不只看版本号。
`--repeat` 默认 3；采 1 次仅用于诊断，compare/replay/selftest 的确定性不会通过。
至少需 2 次与明确非零整数 seed。当前图在根选项固定 seed=7，缺失 graph 的负例在调用选项固定 seed。
seed=0、未显式指定或非法 seed 为 `NOT_ESTABLISHED`，不算确定性通过。

元数据重采后也可直接比对原始文件：

```shell
node tools/reference/capture_metadata.cjs .local/npm-elkjs/package test-runs/metadata-01
python scripts/validate_layout.py json --expected references/metadata/options.json --actual test-runs/metadata-01/options.json --out test-runs/options-diff-01.json
```

同样方法用于 algorithms/categories。原始图文件可加 `json --kind graph`，只对几何数值应用容差，不能替代完整套件验收。

## Python 实现完成后接入

[run_pyelk_candidate.py](../scripts/run_pyelk_candidate.py) 直接导入目标环境安装的 `pyelk.ELK`，调用真实 `ELK(options)` / `layout(graph, arguments)`，采集结果、错误和副作用。
用候选环境解释器生成 argv JSON，自动处理 Windows 路径转义：

```shell
python scripts/validate_layout.py candidate-command --out test-runs/candidate-command-01.json
python scripts/validate_layout.py candidate --command-json test-runs/candidate-command-01.json --out test-runs/python-01 --repeat 3
python scripts/validate_layout.py compare --reference references/layout --candidate test-runs/python-01 --out test-runs/compare-01.json
```

`candidate-command --python` 可指定已安装真实候选 wheel 的 Python 完整路径；默认当前解释器。
命令带 `-I`，适配器不把仓库 src 加入导入路径；开发时先安装项目，发行验收时安装待验 wheel。
记录实际模块位置、Python 版本和包源 SHA，方便排查导入错环境。
**当前 candidate 应失败**：缺 `pyelk` 或 `ELK` 时进程退出 2，capture 为 `INCOMPLETE`，没有成功布局观察。
不得以读取 golden、Node fallback 或复制输出补齐适配器。

自定义 `--command-json` 是非空字符串 argv 数组，执行时追加 `REQUEST_JSON NEW_OBSERVATION_JSON` 两个绝对路径参数，不经过 shell。
请求含 `schema=py-elk-layout-request/v1`、constructor、graph、layoutArguments。
响应为 `py-elk-layout-observation/v1`，必须含原始请求字节 SHA、引擎身份、returned/result 或 threw/error，以及 inputAfter/constructorAfter/argumentsAfter。
参照两份适配器；不得把导入失败包装成 ELK 错误契约通过。

## 比较规则

不平移、缩放、排序或删字段。对象键顺序不影响 JSON 语义；数组顺序保留。
数字 1/1.0 相等，布尔 true 与数字 1 不相等。重复键、NaN、Infinity、溢出成非有限值拒绝。
缺失/新增/类型/值差异全部输出，不截断；路径用 RFC 6901 JSON Pointer，如 `/result/edges/0/sections/0/startPoint/x`。
同时输出 exact 与 coordinateTolerance：

```text
abs(a-b) <= max(1e-6, 1e-9 * max(abs(a), abs(b)))
```

这是本项目既定政策，不是 ELK 官方通用标准。仅用于 result/inputAfter 中形状 x/y/width/height、端口/标签、section 起终点/折点、junctionPoints 数值。
ID、选项、业务数据、错误名/消息和其他字段严格比较。报告实际/允许误差与最大坐标偏差。
inputAfter 也按几何数值规则比较，因为 bundled/FakeWorker 实测修改输入图。
项目原有 Python 输入不变目标仍保留；报告单列 referenceInputPreservation/candidateInputPreservation 的完整差异。
当前合同 profile 是严格上游副作用对比，原生输入保留与这条 JS 路径的差异需要 M1 显式适配决策，不能据此自动改写产品目标。
GWT `$H` 字段和生成 section ID 原样保留，参与当前严格比对；若后续区分私有字段，须评审显式 profile、保留原始差异和负控制，不能默删。

engine 身份/环境、原始错误 stack、termination 观察不属于布局合同相等字段，raw observation 全保留。
错误合同比较 name/message；跨 JS/Python 的异常名映射由真实 API 明确提供。
termination 双方原样列出为 `NOT_ASSESSED`，不声明生命周期兼容。官方 FakeWorker terminate 的 TypeError 记录为 throws。
result 内的计时/日志也严格比较，当前没有偷偷忽略 timing 路径。

## 独立几何约束与适用条件

`basic-flat-orthogonal` 仅验平面根图、给定节点尺寸、单源单目标 extended edge 和单条正交 section。
每例显式给 direction/padding/nodeNode/betweenLayers 和正向 DAG 开关：

- 根/节点有限坐标与非负尺寸、唯一字符串 ID、节点/边身份/顺序、给定尺寸。
- 根 padding、兄弟节点不重叠、同层节点间距。
- 显式 DAG 的边方向和层间距；环/自环关闭此断言，不误判反向边。
- 端点归属、平面 edge container、section ID/连接、起终点在所属节点边框。
- 每段水平或竖直、路由在根范围内、不穿非关联节点内部；边相互交叉不自动判错。
- 仅对显式声明的矩形组件测试验组件包围盒间距，不泛化到任意形状打包。

端口、标签布局、嵌套/跨层级、其他坐标模式和复杂 section 得到 UNSUPPORTED，不算通过；未声明 profile 为 NOT_CHECKED。
递归 JSON 差分仍报告这些结构的完整字段/坐标，但没有它们的独立几何证明。
semanticConstraintsPassed 只表示所列约束通过，坐标失败仍使整体失败。
确定性按完整合同 exact 检查，与跨实现容差独立；目前仅新进程重复，不覆盖同实例污染、并发、取消、重复关闭、恢复。

## 报告与退出码

capture 内有原样 suite.json、当时 upstream-lock.json、各例请求和每次 observation/stdout/stderr/command。
index.json 记录套件/请求/全部文件 SHA、来源/版本、工具源 SHA、实际案例/重复次数分母。
compare 核对双方套件/输入、完整案例集和产物 SHA；空集、漏例、换 seed 的输入、损坏文件或未完成采集拒绝。
SHA 用于追溯/漂移检查，不是远程签名或实现独立性的密码学证明。
原始 references/layout 与请求目录在 .gitattributes 中禁用文本转换，避免 Git 换行转换破坏字节 SHA。

| 退出码 | 含义 |
| --- | --- |
| 0 | 当前命令限定范围通过，需阅读 status/limitation |
| 1 | 完成比较/自测，发现差异或断言失败 |
| 2 | validate_layout 的参数/输入/来源/进程/完整性错误，无法验收 |

check.py 汇总任一步非零为 1，保留子命令原退出码。compare 成功称 SCOPED_CASES_MATCH，不自动改兼容账本或发行状态。
pair 仅作 JSON 差异诊断，不能替代 suite/几何/确定性/来源门禁。

## 增加案例

编辑 tests/fixtures/validation/requests 与 cases.json，注明来源、预期成功/错误、几何适用条件；固定非零 seed，保留模型顺序和业务字段。
生成器可在新目录重建这批输入；新增/改动时同步生成器或明确转为人工维护，回归会检测漂移。
用 reference --cases 采到新目录，运行 selftest/replay 审查真实差异，再明确更新版本化 reference 和 UPSTREAM.referenceFixtures 的路径/计数/index SHA。
旧结果保留，不原地刷新掩盖失败。来源/许可、完整上游断言映射、Python 算法、生命周期和正式包验收继续按 [TASKS](TASKS.md) 完成。
