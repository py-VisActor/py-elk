# 官方 elkjs 参考工具

Node 仅用于研发，不是布局运行时依赖。已实现元数据和真实 graph/错误/副作用采集。
命令、协议、容差与适用条件见 [布局校验手册](../../docs/LAYOUT_VALIDATION.md)。

E07新增`trace_e07_directions.cjs`、`trace_e07_components.cjs`与`check_e07_export_controls.py`，完整复跑见[E07手册](../../docs/E07_DIRECTIONS_COMPONENTS.md)。方向/组件observer对原请求运行bundled/pretty/instrumented，核public结果/输入完全相等，再读取真实变换模式、原方向端口、分量顺序/共享RNG/previous filling与边界状态；观察器不生成期望布局。只读私有观察的局限单独保留。
E06历史工具为`trace_e06_graph.cjs`和`check_e06_export_controls.py`，命令见[E06手册](../../docs/E06_NATIVE_MULTIGRAPH.md)。trace对同原请求运行bundled/pretty/instrumented，核public结果与输入完全相等，再记录19/23真实调用、hidden selfloop对象及RNG；extractor不重算期望。
导出负控先重验真实正控，再破坏单项raw/metadata；不启动引擎或安装器。E07工具只核新的installed协议，不混用旧phase协议；`check_e05_export_controls.py`保留默认E05入口并被E06wrapper参数复用。收据自洽无法认证完全伪造的历史链，真正重执行使用`check_e07_slice.py`。

```shell
python scripts/upstream.py fetch
python scripts/validate_layout.py reference --out test-runs/oracle-01 --repeat 3
python scripts/validate_layout.py selftest --reference test-runs/oracle-01 --out test-runs/controls-01
python scripts/validate_layout.py replay --reference references/layout --candidate test-runs/oracle-01 --out test-runs/replay-01.json
```

[capture_layout.cjs](capture_layout.cjs) 每例独立进程/实例，校验全部发行文件 SHA；保存 graph、构造/调用参数的副作用和 result/error/terminate 观察。
单例格式为 `node tools/reference/capture_layout.cjs PACKAGE REQUEST NEW_OUTPUT`；批处理使用 Python 入口以保留日志/环境/分母。

元数据单独采集：

```shell
node tools/reference/capture_metadata.cjs .local/npm-elkjs/package test-runs/new-metadata
```

输出目录必须不存在。工具核对锁定包/入口 SHA，保存原始算法、选项、类别 JSON 和环境/哈希。
E01新增默认路径探针：固定PRETTY worker仅在内存副本插桩，原发行文件不变。

```shell
node tools/reference/trace_layered_path.cjs .local/npm-elkjs/package tests/fixtures/validation/requests/layered-diamond-right.json test-runs/path-trace-01
```

每请求分别运行bundled、PRETTY、插桩PRETTY，保存完整结果/实际处理器顺序/源SHA。额外启用logging、关闭测时，原请求字节SHA与实际参数覆盖分开记录。
它不代表Python实现或同引擎重复确定性。19调用、默认值、源码范围和适用条件见 [路径审计](../../references/e01-layered-path-notes.md)。
不得把元数据快照装入 Python 可用注册表。该命令使用 bundled 入口默认注册，graph 布局由另一个命令采集。

真实观察：该发行物 bundled 模式的 `terminateWorker()` 抛出
`TypeError: this.worker.terminate is not a function`。采集器把这一明确的已知结果记录为
`contractObservations.outcome = throws`，不把它标为生命周期通过；其他异常直接失败。
首次采集的原始失败也保留于本轮 test-runs。E02只冻结已采的bundled/FakeWorker事实和Python宿主设计；真实Worker/并发/取消尚未验收。

graph oracle 每个 case 使用独立 Node 进程，保存 constructor/args/输入/原始输出、
错误、状态副作用和 Node/包/资源 SHA，隔离模块级 registry 状态。
比较器分 exact、既定坐标容差、semantic-only；未知字段、数组顺序、section/container 坐标均保留。
图字段、端点、section 折点、选项默认值、随机流和错误类型的破坏负控制必须能被检出。

E02参数/副作用探针（56组，每组独立进程）：

```shell
node tools/reference/capture_contracts.cjs .local/npm-elkjs/package test-runs/contracts-01
python scripts/validate_e02_contract.py --replay test-runs/contracts-01/index.json
```

目录必须全新；`--only PROBE_ID`可单例诊断，`--timeout-ms`设置超时，`--summary NEW_JSON`另存摘要。
单例不能代替完整56组回放。原请求字节和哈希随摘要保存，缺省/undefined/null分开描述；清理超时也判采集失败。
摘要只移除工具自身error记录stack，原始输出完整保留，业务字段stack不变。
profile适用域和退出码见[验证手册](../../docs/LAYOUT_VALIDATION.md#显式原生合同profilee02)。

## E05 DAG阶段与证据导出

```shell
node tools/reference/trace_e05_dag.cjs .local/npm-elkjs/package tests/fixtures/suites/E05/requests/project/e05-crossing-six.json test-runs/NEW-E05-trace
python scripts/export_e05_phase_observations.py --capture test-runs/NEW-E05-trace --request tests/fixtures/suites/E05/requests/project/e05-crossing-six.json --stage OrthogonalEdgeRouter --out test-runs/NEW-E05-route.json
node tools/reference/probe_e05_routing_helpers.cjs .local/npm-elkjs/package test-runs/NEW-E05-helpers.json
```

三个独立引擎保持原layoutArguments：bundled、固定pretty、内存插桩pretty。仅开发基础设施替换workerFactory，原发行文件不写入。输出summary及三份实际引擎JSON；导出器重读真实outcome/result/inputAfter、request/worker/tool SHA与调用序列，不仅相信summary的布尔声明。
阶段snapshot包含所选临时对象身份、层/端口顺序与几何、边/bends、RNG bits/状态。空图没有phase，同类LayerSweep两次策略分开；V8计数/membership是观察，缺项不证明未执行。整数port.id及部分Forster私有状态未被观察，不宣称全私有状态exact。
helper工具执行24组显式构造前置下的固定生成函数，保留memory bridge/SHA；这是helper控制，不能增加公开布局分母。版本化阶段收据用于开发测试，生产包不读取它们。
真实安装、同suite比较、收据导出、干净副本与反例复跑见[E05手册](../../docs/E05_NATIVE_DAG.md)。

## E04 阶段与 RNG 真实 oracle

[trace_e04_slice.cjs](trace_e04_slice.cjs) 和 [probe_e04_rng.cjs](probe_e04_rng.cjs)
用于研发时检查锁定的生成 worker，不是 Python 运行时后端，也不进入 wheel。
命令均从项目根目录执行，输出目录或 JSON 文件必须不存在：

```shell
node tools/reference/trace_e04_slice.cjs .local/npm-elkjs/package tests/fixtures/suites/E04/requests/project/e04-default-chain-unequal.json test-runs/NEW-E04-phase-trace
node tools/reference/probe_e04_rng.cjs .local/npm-elkjs/package test-runs/NEW-E04-rng-oracle.json
```

阶段工具的通用接口是 `node tools/reference/trace_e04_slice.cjs PACKAGE REQUEST NEW_OUTPUT_DIRECTORY`。
`REQUEST` 是真实 `py-elk-layout-request/v1` 请求，包含 `constructor`、`layoutArguments` 和 `graph`；
工具复制原请求字节，核对锁定包文件 SHA，再用三个独立进程分别运行 bundled、PRETTY 和内存插桩 PRETTY。
实际 layout 参数原样传递，包括 logging/timing 字段，不额外开启日志。
PRETTY 通过开发用 `workerFactory` 选择固定 worker，这项基础设施覆盖单独记录；原发行文件保持不变。

输出目录包含 `request.json`、三个引擎的原始观察 JSON、各自的命令/退出码和 stdout/stderr，
以及汇总 `summary.json`。汇总记录结果与输入的跨引擎 exact 比较、实际处理器序列和 RNG primitive draw 数；
引擎失败或超时不能得到通过结论。`instrumented.json` 额外保存逐处理器前后工作图快照、
映射回原 worker 行号/偏移的 V8 函数与代码块计数、按顺序的 RNG 状态与 reseed 事件。
原请求 SHA、原始/插桩源码 SHA、精确内存变换、实际参数及工具 SHA 均随记录保留。

快照只覆盖 E04 平面工作图和选定内部属性，并非所有状态；快照相等不能证明某阶段无作用。
V8/JIT 运行下的 coverage 是观察性诊断数据，不能当作稳定、完整的执行集合：
即使原请求和插桩源码字节相同，独立进程的函数成员清单也可能不同；本轮未确定这种差异的具体原因。
缺少某函数条目不能单独证明它未执行，覆盖清单也不应成为布局正确性的逐字相等门槛。
函数/代码块计数不等于完整动态调用图或未测分支的覆盖证明，来源闭合仍须结合源码推导及生产输入守卫。

RNG 工具的通用接口是 `node tools/reference/probe_e04_rng.cjs PACKAGE NEW_OUTPUT_JSON`。
它核对包 SHA，仅在内存中为固定 worker 的 seeded Random 方法增加导出桥，输出六个种子、108 次操作的
原始结果及前后状态，包括有符号数提取、`nextLong` 和 reseed，同时保存源码/桥接/工具 SHA。
生成的 GWT 数值行为是这里的 oracle，不代表所有 JVM 数值边界；seed-zero 的未固定随机分支不在本工具验收内。
上述工具采集的是官方生成源码行为，不构成 Python 完整布局、正式包或整个算法目录的验收。
