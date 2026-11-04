# E05 原生 DAG 与长边使用、校验

当前来源范围已通过22组件独立审查，36输入在官方与新安装wheel中各重复3次通过公开合同、geometry和exact重复校验。同一个新wheel另通过原E04的21输入回归。最终迭代状态以 [RELEASE_STATUS](RELEASE_STATUS.md) 和 [E05运行证据](../references/e05-runtime-audit.json) 为准。
行为基线固定 elkjs 0.12.1，直接移植已锁定生成 worker；Python 运行时不读取参考坐标、不调用 Node/JVM。

## 可调用范围

单层、单连通简单 DAG，0–8原始节点，RIGHT/缺省方向、ORTHOGONAL、给定非负有限尺寸。尺寸、有效 spacing 和 padding 各不超过1000000；padding 显式值为参考 importer 接受的字符串。
支持分叉、汇合、多源/多汇和跨层长边，实际拆分并恢复 dummy，保持原始节点/边的 ID、顺序、业务值和端点。内部节点上限64与原始节点上限8分别检查。
seed 为非零 signed32；省略时显式校验 policy 证明源默认1。0、非法值、别名冲突不回退。层级、公开 ports/labels、环/自环/平行边、多分量、其他方向及已有几何等仍按 [ADR0004](decisions/0004-e05-dag-long-edge.md) 拒绝。

```python
import asyncio
from pyelk import ELK

graph = {
    "id": "g",
    "layoutOptions": {"elk.algorithm": "layered", "elk.direction": "RIGHT"},
    "children": [{"id": name, "width": 40, "height": 20} for name in "abcd"],
    "edges": [
        {"id": "ab", "sources": ["a"], "targets": ["b"]},
        {"id": "ac", "sources": ["a"], "targets": ["c"]},
        {"id": "bd", "sources": ["b"], "targets": ["d"]},
        {"id": "cd", "sources": ["c"], "targets": ["d"]},
        {"id": "ad", "sources": ["a"], "targets": ["d"]},
    ],
}
elk = ELK()
result = asyncio.run(elk.layout(graph))
assert "x" not in graph["children"][0]  # 调用者输入保留
assert [edge["id"] for edge in result["edges"]] == [edge["id"] for edge in graph["edges"]]
```

async 方法目前在调用者线程执行有界计算；完整调度/并发/取消/关闭语义留给 E08。`last_trace` 是独立开发快照，不是公开布局 JSON；临时对象 traceId 与用户 ID、源内可变整数 ID 分开。

## 新会话的离线入口

```shell
python scripts/check.py --out test-runs/session-e05-01
python scripts/build_e05_suite.py check --suite tests/fixtures/suites/E05
python scripts/validate_e05_source_bindings.py --require-approved
python scripts/validate_e05_runtime.py
python scripts/validate_e04_runtime.py --historical
```

每次使用新输出目录。离线入口真正执行当前 Python 算法对照原始官方观察，并独立核几何、输入/顺序/端点、dummy 恢复与 RNG。
E05 suite 为12个原始 master 加24个自编变体，共36；原25 master及13个排除理由保留。输入选择和原始官方采集的准备状态是历史事实，不回写为当前 Python 通过。
E04 的21例和数值控制继续回归；原始 E04 包与声明封存于 `references/history/E04`，历史审计不拿旧包认证新源码，不导入或运行归档包。

## 真正构建、隔离安装与同 suite 比较

先固定所有 owner 文件，确认来源完整，再构建。示例在仓库根执行，Linux 将候选解释器路径换成 `.local/e05-candidate/bin/python`。

```shell
python -m pip install build==1.6.1 setuptools==84.2.1 wheel==0.48.0
python -m build --no-isolation --outdir test-runs/e05-dist-01
python -m venv .local/e05-candidate
.local/e05-candidate/Scripts/python.exe -m pip install --no-deps --no-index test-runs/e05-dist-01/py_elk-0.0.1a0-py3-none-any.whl
python scripts/upstream.py fetch
python scripts/check_e05_slice.py --candidate-python .local/e05-candidate/Scripts/python.exe --wheel test-runs/e05-dist-01/py_elk-0.0.1a0-py3-none-any.whl --repeat 3 --out test-runs/e05-installed-01
```

脚本核实际 wheel/METADATA/导入路径、全部 Python/许可文件与当前 src 字节，候选进程用 `-I`、空 PATH、无 PYTHONPATH/PYTHONHOME。新旧源码不同须重新构建和安装。
JS 与已安装候选使用同36输入、各3次独立进程；显式 `native-basic-layered-v1` 与 `elkjs-0.12.1-default-seed-v1`。公开合同 exact、既定 abs1e-6/rel1e-9 几何容差、独立 geometry 和 exact 重复分别报告。
原 strict 输入变更/`$H` 差异保留；不新增投影规则、放宽容差或把生命周期未评估算通过。

成功的实际 run 可压缩成新版本化收据，原始日志与差异仍留原目录：

```shell
python scripts/export_e05_installed_evidence.py --run test-runs/e05-installed-01 --out test-runs/e05-installed-receipt.json
```

此导出不批准或认证历史执行；当前审计还检查收据中的请求、命令角色、policy、全部分母和当前包字节。

## 定位阶段差异

```shell
node tools/reference/trace_e05_dag.cjs .local/npm-elkjs/package tests/fixtures/suites/E05/requests/project/e05-crossing-six.json test-runs/e05-phase-01
python scripts/export_e05_phase_observations.py --capture test-runs/e05-phase-01 --request tests/fixtures/suites/E05/requests/project/e05-crossing-six.json --stage OrthogonalEdgeRouter --out test-runs/e05-route-phase.json
node tools/reference/probe_e05_routing_helpers.cjs .local/npm-elkjs/package test-runs/e05-route-helpers.json
```

trace 工具在内存插桩固定源码，分别运行原 bundled、原 pretty、插桩 pretty，比较 result/inputAfter 与原参数。导出器重新核三份实际捕获与 summary，不仅相信其布尔声明。
每个阶段保留真实 before/after、有序对象身份与 RNG primitive bits/state。空图没有 phase；同类 LayerSweep 两次策略调用分别保存。V8 coverage 缺项不能证明代码未执行，选定字段快照也不能证明所有私有状态相等。
已封37个非空实际路由阶段（含64内部节点、负的中间 y 和真实 critical splitter RNG），另有7组数值和24组真实 helper 控制；后两者是显式构造的私有 helper 输入，不能算新增公开布局案例。
先定位第一个不同阶段，检查列表重挂载、getter presence/克隆、逐步浮点运算和 RNG；不要简化源码运算顺序或用新 golden 掩盖差异。

已有真实安装run和上述三引擎phase捕获后，可重跑两种exporter的独立反例。工具先验证正常输入，再复制并破坏逐repeat数组、索引角色/SHA、raw结果/输入/策略等，确认被拒；不重跑引擎或安装，不改原记录。两个run与新输出均放在当前checkout内。

```shell
python tools/reference/check_e05_export_controls.py --installed-run test-runs/e05-installed-01 --phase-capture test-runs/e05-phase-01 --phase-request tests/fixtures/suites/E05/requests/project/e05-crossing-six.json --out test-runs/e05-export-controls-01
python scripts/check_fresh_copy.py --out test-runs/e05-fresh-01
```

完整算法分母仍12、选项243、类别8，完整 Python 算法通过数仍0。当前为本地实验包；正式0.1.0、精确外部 Java build 和项目发布许可仍按后续门禁处理，py-mermaid 集成另列。
