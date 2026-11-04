# E07：四方向、连通分量与基础选项

本轮在固定 elkjs 0.12.1 生成 worker 上续审33个组件，完成原生 Python 执行链。实际验收状态和包指纹只读[状态页](RELEASE_STATUS.md)及[本轮记录](changes/20261103-E07.json)，不从本文的命令示例推断已经执行。

## 输入范围

平面图共0–8个原始节点、最多28条原始边；允许孤立节点、多弱连通分量、环、自环、独立平行边及长边。支持 RIGHT/LEFT/DOWN/UP，UNDEFINED按固定默认aspectRatio解析为RIGHT；只接受ORTHOGONAL。给定尺寸、三项spacing及四侧padding为有限非负值，最大1,000,000；seed为非零signed32整数或整数字符串，省略为1。

九项选项：algorithm、direction、padding、spacing.nodeNode、layered.spacing.nodeNodeBetweenLayers、separateConnectedComponents、spacing.componentComponent、edgeRouting、randomSeed。使用完整`org.eclipse.elk.*`或`elk.*`别名；同作用域重复别名即使值相同也拒绝。调用中存在`layoutOptions`就整体替换constructor默认，根节点local再覆盖选中值。显式padding须为完整四侧字符串。叶节点local只支持padding；无标签、空node-size constraints时其尺寸贡献分支未启用，该限制经来源def-use审查，不能推广到嵌套图。

公开ports、labels、嵌套图、预存几何、其他策略/选项、seed0及完整调度/取消/元数据API均在后续轮次。输入、constructor和调用参数精确保留；计算仍在调用线程执行。

## 真实执行协议

先按原数组顺序导入、按原方向创建隐式端口，并全图prepare一次。RNG、processor tuple与受限spacing投影浅共享。separate=true执行真实有序DFS；false返回原图本体。每个分量执行19个普通处理器，任意原始分量有自环时全局选23个；非RIGHT首尾再各有GraphTransformer，共21/25个。DIRECTION属性始终保留原值。

PRE先归一化真实工作节点/端口/尺寸/padding；POST在长边与自环恢复后还原。false分支的NETWORK_SIMPLEX仍执行自己的真实分量驱动，保留前序层占用参与平衡。完成各分量后清层、稳定按面积进行SimpleRow打包、resize一次，再纯几何导出；不会重复finish或在最终JSON上套旋转模板。

内部界为176节点、196段、392端口；路由临时segment每边界最多56，与原始28边分别计数。完整算法验收数仍0；12算法/243选项/8类别/25master分母不变。

## 新会话复跑

从仓库根目录执行，每次使用新输出目录：

```shell
python scripts/check.py --out test-runs/session-e07-01
python scripts/build_e07_suite.py check --suite tests/fixtures/suites/E07
python scripts/validate_e07_source_bindings.py --require-approved
python scripts/validate_e07_runtime.py
```

离线入口不需要Node、网络或依赖安装。72个输入为22个master原字节加50个项目变体；3个master错误输入保留排除理由，不计入成功错误合同。官方快照每例独立3次；切片测试比较实际Python结果、输入保留、确定性、阶段顺序与独立几何。

需要Git/npm缓存及Node的来源复核和真实安装对照：

```shell
python scripts/validate_e07_source_bindings.py --with-upstream --require-approved
python -m build --no-isolation --outdir test-runs/e07-dist
python -m venv .local/e07-candidate
# 激活该新环境后安装本次实际wheel，随后退出激活环境。
python -m pip install --no-deps --no-index test-runs/e07-dist/py_elk-0.0.1a0-py3-none-any.whl
python scripts/check_e07_slice.py --candidate-python .local/e07-candidate/Scripts/python.exe --wheel test-runs/e07-dist/py_elk-0.0.1a0-py3-none-any.whl --repeat 3 --out test-runs/e07-installed
python scripts/export_e07_installed_evidence.py --run test-runs/e07-installed --out test-runs/e07-installed-receipt.json
python tools/reference/check_e07_export_controls.py --installed-run test-runs/e07-installed --out test-runs/e07-export-controls
```

Linux将candidate路径换成`.local/e07-candidate/bin/python`。构建工具固定版本见pyproject；不要把示例中的安装解释器误用为仓库运行环境。check脚本核所有Python/许可文件和METADATA与当前源/README一致，候选使用`-I`及空PATH。同一个新wheel还应运行check_e06_slice.py、check_e05_slice.py和check_e04_slice.py，分别对照52/36/21例。

导出控制工具先验证原始及复制正本，再逐项破坏真实raw/索引/命令/metadata并要求拒绝；只读校验、不启动引擎或安装器。实际run与全新out须在当前checkout且互不包含。它不复用旧phase trace协议，也不能认证完全伪造的历史链。

## 几何与证据边界

原始strict差异保留，native-basic-layered-v1仅允许既定的两项适配。坐标容差abs1e-6/rel1e-9；ID、业务字段、端点、顺序与重复确定性严格相等。

`independent-components-v1`仅在原输入的有效CC=true时避免跨分量猜测同层；`default-layered-components-v2`只从原图DAG可达对或严格简单环证明不同rank。方向、padding及spacing政策绑定原始有效选项，候选不能改拓扑获取豁免。重叠、边界、原端点、正交路由和无关节点穿越仍独立检查。旧E06 v1规则不变。

E04/E05/E06的固定历史包和声明只读归档、不导入执行、不认证当前源。E07安装收据须来自当前新建wheel；修改README/pyproject/源/许可后必须重新构建。来源收据、阶段探针、全算法对照、静态收据一致性各有独立用途，均不构成自动数学等价证明或正式发布许可。
