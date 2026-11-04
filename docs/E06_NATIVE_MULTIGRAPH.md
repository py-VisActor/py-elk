# E06 原生多重图切片

当前实现对齐固定 elkjs 0.12.1 生成 worker，支持单弱连通、0–8原始节点、最多28原始边的平面图。允许环、自环和独立平行边，保留E05全部DAG/长边范围。RIGHT/缺省方向、ORTHOGONAL、给定尺寸及spacing/padding上界1000000，默认seed1或有效非零signed32 seed；显式padding使用字符串。公开ports、labels、嵌套及高级策略仍在后续迭代。

先读[ADR0005](decisions/0005-e06-multigraph.md)、[组件批准](../references/e06-component-approvals.json)和[最终记录](changes/20261103-E06.json)。27组件来源批准不等于完整算法验收；实际运行验收以最终记录和[状态页](RELEASE_STATUS.md)为准。
实现与工具的独立终审也已版本化：例如[来源校验](../references/e06-reviews/Validator-by-B.json)、[R执行链](../references/e06-reviews/Root-code-by-B.json)、[当前包与导出](../references/e06-reviews/Current-receipts-by-B.json)及[20项导出负控](../references/e06-export-controls.json)。私有阶段/收据自洽与公开运行验收分别记录。

## 执行与验证

在项目根目录运行，所有输出目录必须是新目录：

```shell
python scripts/check.py --out test-runs/session-e06-01
python scripts/build_e06_suite.py check --suite tests/fixtures/suites/E06
python scripts/validate_e06_source_bindings.py --require-approved
python scripts/validate_e06_source_bindings.py --require-approved --with-upstream
python scripts/validate_e06_runtime.py
```

离线检查执行实际Python布局、真实已保存oracle、来源依赖及当前包收据。它不重新运行历史Node采集。真实重采与安装验证需要开发环境中的Node、固定上游和构建工具：

```shell
python -m build --no-isolation --outdir test-runs/e06-build-01/dist
python -m venv .local/e06-candidate
.local/e06-candidate/Scripts/python -m pip install --no-deps --no-index test-runs/e06-build-01/dist/py_elk-0.0.1a0-py3-none-any.whl
python scripts/check_e06_slice.py --candidate-python .local/e06-candidate/Scripts/python --wheel test-runs/e06-build-01/dist/py_elk-0.0.1a0-py3-none-any.whl --repeat 3 --out test-runs/e06-installed-01
python scripts/export_e06_installed_evidence.py --run test-runs/e06-installed-01 --out test-runs/e06-installed-receipt-01.json
```

POSIX环境把`Scripts/python`改为`bin/python`。候选实际使用`-I`、空PATH、无PYTHONPATH/PYTHONHOME；完整Python文件、所有随包许可及METADATA须与新wheel一致，旧wheel不能认证当前src。发布版本仍是开发版0.0.1a0。

同一个新wheel还需执行`check_e05_slice.py`的36例与`check_e04_slice.py`的21例回归。旧E04/E05的原wheel、原声明和收据保留在`references/history/`；`validate_e04_runtime.py --historical`和`validate_e05_runtime.py --historical`只核历史材料，不导入运行或认证新代码。

## 准确性边界

正式suite52例：25个master中15个选入、10个明确排除，另37个项目变体。两个引擎均至少3次重复；默认seed必须解析为1，不能省略确定性检查。几何数字容差abs1e-6/rel1e-9，section ID、业务字段、端点、数组顺序严格。原始JS字段缓存及输入变更差异保留；仅使用既定`native-basic-layered-v1`的两项适配。

普通图19调用；含selfloop图23调用。自环真实Pre隐藏原边/端口，Restorer恢复NORTH端口，Router计算slot/bends/margin，Post恢复原边；并非绘制模板。平行边默认不合并，每边两个独立端口。破环消耗真实GWT48 RNG，恢复原方向和bend顺序。粗界176内部节点/196段/392端口；普通路由私有临时segment每层边界最多56个。真实压力输入观测到134节点。

零尺寸环的几何规则使用显式`rankSeparation`与原图简单环来源lemma，详见ADR；不是按case ID、SCC或候选改写后的端点豁免。重叠和路由检查继续保留。

私有阶段观察只用于开发测试，不能进入运行时或分派结果。可从真实三引擎capture提取：

```shell
node tools/reference/trace_e06_graph.cjs .local/npm-elkjs/package tests/fixtures/suites/E06/requests/project/e06-selfloop-double.json test-runs/e06-trace-01
python scripts/export_e06_phase_observations.py --capture test-runs/e06-trace-01 --request tests/fixtures/suites/E06/requests/project/e06-selfloop-double.json --stage LabelAndNodeSizeProcessor --out test-runs/e06-stage-01.json
```

extractor核原请求字节、工具SHA、固定worker、三引擎结果/输入和真实调用序列，不重算预期坐标。NORTH tiny-width阶段测试保留逐次浮点加法与负零；不能用宽度除端口数替代。

导出工具自身也要验证正常捕获与隔离破坏输入；先完成上面的真实安装和trace，再运行：

```shell
python tools/reference/check_e06_export_controls.py --installed-run test-runs/e06-installed-01 --phase-capture test-runs/e06-trace-01 --phase-request tests/fixtures/suites/E06/requests/project/e06-selfloop-double.json --out test-runs/e06-export-controls-01
python scripts/check_fresh_copy.py --out test-runs/e06-fresh-01
```

这些命令不修改原capture或仓库index；临时副本在指定新输出中，负控前先核正控。Git过滤检查不含`.git`/`.local`缓存，必须在没有网络/Node的条件下完成离线入口。

本轮不接受完整layered/API或正式发布；完整算法数仍0，12算法/243选项/8类别与25master分母保留。生命周期、其余方向/多个组件、发行许可和精确外部Java build见后续迭代。
