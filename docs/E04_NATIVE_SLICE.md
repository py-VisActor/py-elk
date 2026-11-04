# E04 原生实验切片与验证

E04已接通真实Python`ELK`和默认处理链，21例真实安装对照通过，不是正式0.1.0发布或完整layered支持。
不调用Node/JVM/浏览器，不从reference/golden读取坐标。Node仅是开发oracle。

## 当前输入域

0–4个child的flat连通单向无环路径，字符串ID非空、给定有限非负尺寸，尺寸/三间距/四边padding各<=1e6；RIGHT或缺省UNDEFINED、ORTHOGONAL、非零signed32 seed、组件分离true。
节点和边的输入数组可错序。空图走源内leaf支路，非空图执行真实19调用，包括两次不同LayerSweep和真实随机消耗；13中间处理器保留源内有效写操作。
这是本轮源码审查与数值支路边界：不是4节点能通过便推断任意DAG或任意数值都支持。超域明确失败，不换算法、不返回原图伪造布局。

不支持fork/join/cycle/self/parallel/disconnected、ports/labels/compound、非空child/edge局部配置、legacy properties、已有root几何/child位置/edge sections/container、logging/timing真值或未知参数。
已有root logging及root/child直接`$H`触发参考的独立清理/身份cache分支，也暂为域外；业务嵌套`$H`、`error.stack`、null/false/0正常保留。所有已有edge几何按字段存在拒绝，空列表也拒绝。构造算法筛选只接受缺省或['layered']，worker参数一律拒绝。
有效显式padding须为`[top=12,right=12,bottom=12,left=12]`格式字符串；E03 Mapping解析不代表真实JS importer接受对象。只检查最终有效值，被call空配置或local字符串覆盖的旧Mapping可以保留。

## 调用与实际限制

实现落点（均在`src/pyelk`下）：

| 文件/符号 | 责任与证据 |
| --- | --- |
| `api.py:ELK`、`algorithms/layered/scope.py:validate_slice` | 最小公开调用、独立host admission、clone及关闭边界；API/scope负控制 |
| `algorithms/layered/pipeline.py:layout_context` | 实际按19调用调度、独立trace、空图源支路；native conformance |
| `algorithms/layered/graph.py` | 有序mutable LGraph/LNode/LPort/LEdge/Layer及身份邻接；A源host映射 |
| `algorithms/layered/import_export.py` | JSON导入、组件DFS顺序、原源combine/resize/回填；A源与中间状态对照 |
| `algorithms/layered/processors.py:INTERMEDIATE_PROCESSORS` | 13个具名intermediate的有效读写；A源guard/helper证明与processor回归 |
| `algorithms/layered/phases.py` | GREEDY/NETWORK_SIMPLEX/两次LayerSweep/BK/ORTHO与JavaRandom；B源、真实阶段/RNG对照和数值回归 |

这些是受审源分支的实际移植，不能把文件名相似当作完整ELK策略实现。当前19调用的配置不预设未来DAG一定相同。

安装当前开发wheel后：

```python
import asyncio
from pyelk import ELK

graph = {
    "id": "root",
    "children": [{"id": "a", "width": 40, "height": 30},
                 {"id": "b", "width": 30, "height": 20}],
    "edges": [{"id": "e", "sources": ["a"], "targets": ["b"]}],
}
elk = ELK()
result = asyncio.run(elk.layout(graph))
elk.terminateWorker()
```

graph/构造参数/调用参数保持不变；每call有独立工作图和RNG。`last_trace`返回独立研发快照，源内phase/RNG/port状态不混入result。
当前async方法在调用线程执行受限CPU计算，不承诺事件循环隔离、CPU并行或立即取消。terminateWorker做本地幂等关闭；完整API/元数据/错误/并发/取消/资源验收归E08，不能由这次小范围测试替代。
包版本仍0.0.1a0，未上传。完整12算法/243选项/8类别分母保留；只有受限native slice可调用，元数据目录不直接当注册表。

## 开发验证入口

默认离线一键检查仍不需Node或安装包；source conformance使用实际src算法对保存的真实oracle，不伪造candidate：

```shell
python scripts/check.py --out test-runs/e04-start-01
python scripts/build_slice_suite.py check --suite tests/fixtures/suites/E04
python scripts/validate_e04_source_bindings.py
python scripts/validate_e04_runtime.py
python scripts/validate_e04_source_bindings.py --with-upstream --out test-runs/e04-source-01.json
```

默认source校验只核离线结构/身份/proof引用/审批绑定，报告canonicalVerified=false；有固定Git/npm缓存的--with-upstream才重验实际blob/span/UTF16 function/callsite。数学等价论证仍由独立source review承担，工具不冒称自动证明。

在已安装项目`.[dev]`的独立开发环境内，先构建并安装到另一个新环境。以下为Windows命令，所有输出目录需新建；Linux把`Scripts/python.exe`换成`bin/python`：

```shell
python -m build --no-isolation --outdir test-runs/e04-build-01/dist
python -m venv .local/e04-candidate-01
.local/e04-candidate-01/Scripts/python.exe -m pip install --no-deps --no-index test-runs/e04-build-01/dist/py_elk-0.0.1a0-py3-none-any.whl
python scripts/check_e04_slice.py --candidate-python .local/e04-candidate-01/Scripts/python.exe --wheel test-runs/e04-build-01/dist/py_elk-0.0.1a0-py3-none-any.whl --out test-runs/e04-native-01
```

复用已有真实候选环境时，以解释器完整路径和同一wheel输入（Windows含空格路径用引号）：

```shell
python scripts/check_e04_slice.py --candidate-python .local/e04-candidate/Scripts/python.exe --wheel test-runs/REPLACE/dist/py_elk-0.0.1a0-py3-none-any.whl --out test-runs/e04-native-01
```

把REPLACE替换为实际新构建目录。该命令逐字节核对安装内容/许可与wheel，使用-I和清空PATH/PYTHONPATH/PYTHONHOME运行Python候选；另在正常开发环境跑同suite官方Node参考。
同时核wheel/已安装METADATA的name/version、真实import路径和当前src包字节，避免导入错环境或用旧wheel证明新代码。
双方同21个输入、相同原请求字节SHA、至少2次重复（默认3），native profile、独立geometry和exact重复确定性共同验收，原strict差异仍完整显示。
E04 suite保留原25分母：5个master原字节+16个项目变体，20个原案例排除理由逐项可查。不得把排除当兼容通过。
轮次记录原始日志、实际wheel/source SHA和安装环境；命令或安装失败保持FAIL，不读取保存坐标补齐返回值。

省略seed的案例使用显式`--determinism-policy elkjs-0.12.1-default-seed-v1`，绑定固定源码声明默认1；只在有效seed所有别名缺省时推导。显式0、false、null、非法值或多别名歧义不能回退；仍需至少两份实际观察和完整合同exact重复。原默认`explicit-nonzero-seed`行为不变，21个请求字节不改。

本轮Windows CPython3.13.15实际wheel SHA为`7ebf9e042028bb4fdc3e73270066d398c285a1af2c5b2cb3cc7a39c5e30d95f7`，21例每端各3次通过native公开合同exact、geometry和确定性；原strict保留输入副作用/形状cache差异。[版本化安装收据](../references/e04-installed-check.json)是历史结果摘要，[runtime审计](../references/e04-runtime-audit.json)绑定来源/输入/数值回归。离线审计不重新执行历史wheel，也不自动证明数学等价。

## 来源与后续

实际源为固定elkjs0.12.1生成worker；[组件审批](../references/e04-component-approvals.json)、[A源](../references/e04-source-components-A.json)、[B源](../references/e04-source-components-B.json)和版本化独立source review对应具体guard/helper/数值语义。
原EPL/GPL声明、LICENSE与NOTICE随包保留；精确外部Java构建和项目自身发布许可仍是不同问题，未因source gate核实而伪称已解决。
E05前先读E04复盘，对新增DAG/长边/更多节点与数值支路重新核source；不能移除guard后直接宣布全layered兼容。
