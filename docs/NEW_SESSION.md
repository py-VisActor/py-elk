# 新会话入口

项目目录为 `py-visactor/py-elk`。先检查当前文件与适用指令并保留用户修改。
当前已有骨架、来源锁与真实布局验证工具，**没有 Python ELK API、算法或已发布包**，实际证据见 [RELEASE_STATUS](RELEASE_STATUS.md)。
原来的四份设计文件保留为根入口；实现架构见 [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md)，
工作包见 [TASKS](TASKS.md)，公开行为设计见 [API_COMPATIBILITY](../API_COMPATIBILITY.md)。
实际写Python代码前读 [实现策略](IMPLEMENTATION_PLAN.md#2a-python实现策略) 与 [迭代执行计划](ITERATION_PLAN.md)，从 [iteration-plan.json](iteration-plan.json) 读取下一轮和依赖门禁。
当前nextIteration=E01，全部实现轮次为planned；E01–E12对应独立基础正式包，E13–E21为发布后扩展，I0–I3单列。

唯一基线是 elkjs 0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`。
py-mermaid 将接入 py-elk，不建立旧 ELK 兼容版本分支。Python 运行时不调用 Node、JVM、浏览器或 Canvas。
标签尺寸由上层提供；py-elk 计算几何。

优先顺序：M1–M4完成独立基础能力和候选验收，M5发布正式Python包0.1.0，随后单独执行I0–I3 py-mermaid集成。
首版单层layered/核心选项范围见 [FIRST_RELEASE_SCOPE](FIRST_RELEASE_SCOPE.md)；高级与全量能力后续扩展，不能阻塞基础包先发布。

先读本页、实现策略/迭代计划、[布局校验操作手册](LAYOUT_VALIDATION.md)、首版范围与任务清单，再读取 [UPSTREAM](../UPSTREAM.json)、
[来源](../references/README.md)、[测试与发布](TEST_AND_RELEASE.md)和 [compatibility](compatibility.json)。
仓库根目录、CPython 3.11+；不需 Node、网络或安装开发依赖，即可检查现有工具：

```shell
python scripts/check.py --out test-runs/session-01
python examples/show_scope.py
```

每次换新目录。report.json 保存实际命令、退出码、日志与源 SHA；成功为 DEVELOPMENT_CHECKS_PASS，Python 算法通过数仍为0。
包含 bootstrap、比较器回归、25个官方正例与20个工具控制（2个匹配正控制、18个破坏负控制）。
失败先查对应 `*-command/stderr.log`，不要扩大容差或刷新快照掩盖问题。

有 Git/Node 时验证真实参考运行：

```shell
python scripts/upstream.py fetch
python scripts/check.py --with-reference --out test-runs/session-oracle-01
```

官方重采核对全部发行文件SHA，每例3次独立进程。Python实现完成后，用 candidate-command → candidate → compare 接入真实环境；命令见[手册](LAYOUT_VALIDATION.md)。
当前缺 ELK 的 candidate 必须失败为 INCOMPLETE，不得读 golden 或 fallback 补齐。

需开发包时使用 CPython 3.11+ 新环境并执行 `python -m pip install -e ".[dev]"`；
这只安装本地版本骨架，不提供 ELK/layout API，也不表示包已发布。

现有默认元数据为 12 算法/243 选项/8 类别；Python 全部 planned。
Java 算法源码与发行 worker 的精确对应仍 unresolved；不能从外部 master 移植后冒称锁定来源。
FakeWorker terminateWorker 实测 TypeError 已留证；M1 需冻结生命周期映射，不隐去异常。
官方 bundled 会修改输入并生成 `$H`，原始字段与副作用都参与比对；不能默删。
exact、既定1e-6/1e-9容差、独立几何分开报告；几何通过不能覆盖坐标失败。
独立几何当前仅平面node-only正交图，端口/标签/层级/其他坐标模式未验。
当前确定性仅新进程重复，不覆盖同实例、并发/取消/关闭/恢复。

下一轮执行E01：来源/默认路径审计，建立首版source→assertion→Python symbol映射；源码缺口与算法移植门禁单独记录。
随后E02处理原生profile/副作用/私有字段与宿主合同，E03实现有序模型和选项；满足组件来源与合同门禁后E04接入真实候选。
已有25例工具不等于M1完成，阶段suite也不等于完整首版通过。profile选择、suite构建器及算法测试等待建能力不得当成当前已有命令。
每轮记录源SHA、实际命令/退出码、差异/限制/下一步，再更新机器索引；完成状态以真实证据为准。
