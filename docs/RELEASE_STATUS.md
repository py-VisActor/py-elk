# 当前发行状态

**[py-visactor-elk 0.1.1](https://pypi.org/project/py-visactor-elk/0.1.1/)** 已正式发布。
[同组工件发行流水线](https://github.com/py-VisActor/py-elk/actions/runs/42378501323)通过
Windows/Linux各自的wheel和sdist安装；Trusted Publisher上传后，再核实PyPI实际
Documentation链接、用户README描述、两个下载SHA，并独立安装实际下载的两类工件。
[GitHub Release](https://github.com/py-VisActor/py-elk/releases/tag/v0.1.1-docs.1)
使用相同已验证字节，精确来源与首次失败见[发行证据](releases/0.1.1-publication.json)。

本版更新文档与项目链接，布局实现和运行依赖不变，运行文件仅更新版本字面量。
用户入口为[文档目录](README.md)，维护入口为[开发指南](development/README.md)。
原`v0.1.1`标签的YAML首失败保留，实际发布使用不可变`v0.1.1-docs.1`标签；
以下0.1.0验收统计和限制均为历史事实，不改称本版重新执行。

# 0.1.0历史发行与验收状态


原生 Python ELK 迁移及独立包交付已按 E01–E21 的明示有限条件完成验收。正式实现为 `src/pyelk`，12 个算法、243 个选项、8 个类别、196 个 Python 模块／208 个运行文件。py-mermaid 的 I0–I3 集成继续单独后置。

**[py-visactor-elk 0.1.0](https://pypi.org/project/py-visactor-elk/0.1.0/)** 已通过 GitHub OIDC 实际发布、PyPI 下载和外部 wheel／sdist 安装；导入名为 `pyelk`。当前 208 个运行文件与实际发布 payload 逐 SHA 一致，纯验收资料更新没有重发或覆盖该版本。见 [发行证据](releases/evidence/published-0.1.0/publication.json)。

[最终逐条件审计](iterations/E20_E21_ACCEPTANCE.md)覆盖原 M8 条件、[M6](iterations/E13_E15_ACCEPTANCE.md)、[M7](iterations/E16_E19_ACCEPTANCE.md)、[90／121 分支矩阵](iterations/FULL_DECLARED_BRANCH_MATRIX.md)、[243 选项角色](iterations/FULL_OPTION_ROLES.md)、平台／状态／资源及实际发行。原 37 步／917 测试（含 1 skip）和 Windows／Linux × CPython 3.11–3.14 的 8 wheel／2 sdist 代表单元保留执行版本 0.0.1a0；当前版本／MrTree 修复另有受影响证据，不把旧运行改称新执行。

39 个性能配置／195 次正式测量及 6 个迭代观察保留实际版本；发布版仅为 MrTree 增加 3 配置／15 次正式测量。新总 gate 离线重核 66 个正常 Layered／40 个其他 provider 的完整结果与调用方输入，临时恢复 661 份选项输入并实际重算原效果账本，同时核 39 配置的五份输出 SHA；均未启动布局、Source、安装或平台任务。

完成验收不代表无限输入或所有选项组合已证明正确。原 73 项几何／15 项状态、去重 82 项的效果账本不变；独立角色见证 87 项，156 项仍无独立角色消费见证，完整 243 项语义通过数为 0。PARTIAL／NOT_ASSESSED、Source 错误／非有限值／seed0 宿主熵、8 个工厂异常名、23 个内部身份顺序和 11 个 Radial 私有浮点差异保留。MrTree 的 Source RangeError／原生 RecursionError 终止修复见 [ADR0015](decisions/0015-mrtree-recursive-cycle.md)。

离线重核完成条件：

```shell
python scripts/iteration/migration_acceptance.py --check --require-complete
```

后续修复只验证影响范围；新发行绑定自己的候选字节及实际下载。不要因文档更新重跑已过数学／跨平台全量。历史进度不替代 [机器账本](implementation-backlog.json)和 [机器计划](iteration-plan.json)。
