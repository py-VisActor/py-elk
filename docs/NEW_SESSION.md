# 新会话入口

实际项目为 `C:/code/py-visactor/py-elk`，不是环境可能显示的 `py-mermaid`。原生迁移与独立包交付的 E01–E21 已完成，见 [当前状态](RELEASE_STATUS.md)、[机器账本](implementation-backlog.json)和 [最终逐条件审计](iterations/E20_E21_ACCEPTANCE.md)。不要按历史切片计划重新实现，也不要自动启动独立后置的 py-mermaid I0–I3。

当前产品源码为 `src/pyelk`；196 个模块、208 个运行文件、12／243／8。实际发行名 `py-visactor-elk`，导入 `pyelk`。已发布的 0.1.0 包含完整原生实现与 MrTree 终止修复，当前运行字节与实际 PyPI wheel／sdist 相同；详见 [实际发布](releases/evidence/published-0.1.0/publication.json)。`.local/migration-next` 是历史快照。

接续先核实际 Git 状态与 agent owner，保留未提交修改，再按新任务决定影响范围。离线总审计：

```shell
python scripts/iteration/migration_acceptance.py --check --require-complete
```

总审计使用显式证据归档，临时恢复所需原始数据，不启动产品／Source／安装／性能或平台任务，不隐式借旧工作区。独立入口：

```shell
python scripts/iteration/declared_branch_matrix.py --check
python scripts/iteration/e13_e15_acceptance.py --check --root-map C:/code/py-visactor/py-elk=.
python scripts/iteration/e16_e19_acceptance.py --check --root-map C:/code/py-visactor/py-elk=.
python scripts/iteration/platform_evidence.py --check
python scripts/iteration/option_roles.py --check
```

90 个核心 factory／121 个有限值按实际强度归类；配置、调度排除、Source 路线、helper、几何和边界互不冒充。原选项账本 73／15／去重 82 不变，独立角色见证 87；156 项仍无独立角色消费见证，完整 243 语义通过数为 0。原全量 37／917、平台 8＋2、性能 39 配置及发布版 MrTree 3 配置各自保留实际版本／主机／输入。Source 错误、8 个工厂异常名、23 个身份顺序和 11 个 Radial 私有浮点差异均保留。

矩阵、M6、角色与总审计有 SHA／内容依赖；变更需同一稳定批次更新，不能提交已无法严格复核的组合。默认 CI 由 [显式影响清单](iterations/full-native-ci-checks.json)选择，未知影响停止，不自动回退全量。源码／算法变化检查受影响项，文档变化不重跑已过数学／平台矩阵。首次统一全量已保存，不将旧执行重绑新源码。

Source 固定为 elkjs 0.12.1 的 worker；原创代码 MIT，实际源代码保留第三方通知。单文件 owner 和 root＋A／B／V 见 [并行规范](PARALLEL_EXECUTION.md)，不重复询问已有许可／发布权限。Windows 使用 PowerShell、显式工作目录与 UTF-8 读取，保留 `.gitattributes` 指定原证据字节。
