# 新会话入口

项目位于 `C:/code/py-visactor/py-elk`，不是环境可能显示的 `py-mermaid`。当前工作树是权威状态，先看 [任务账本](implementation-backlog.json)及 [发行状态](RELEASE_STATUS.md)。

全部功能已迁入 `src/pyelk`，正在统一校验及定向修复。12 个算法、243 个选项、8 个类别已注册；这些数量不代表所有选项值和组合都验证正确。`py-mermaid` 集成及绘制不在当前目标中。

`py-visactor-elk 0.1.0` 已通过 `v0.1.0` / `bfac8a0` 正式发布；PyPI 下载字节与实际上传 artifact 一致，wheel/sdist 均已真实安装。见 [实际发行](releases/evidence/published-0.1.0/publication.json)。MrTree 控制环已修复。接下来继续 E20/E21 声明分支验收，不重做发行或重绑旧观察。

接续顺序：

1. 查看 [机器任务账本](implementation-backlog.json)、[迭代计划](iteration-plan.json)和 agent 实际状态，避免覆盖仍在执行的工作。
2. 先读 [有限声明矩阵](iterations/FULL_DECLARED_BRANCH_MATRIX.md)及其归档；90 个核心 factory 已有分范围终态，补充枚举另列，不把两者混成全部通过。先确认 agent 是否仍持有文件写入权。
3. 用 `declared_branch_matrix.py --check` 和 `option_roles.py --check` 离线核映射，只为确实缺失的有限分支准备最小状态/效果见证。不要重采 52、72、81、151 已过矩阵。
4. 收口 E13–E21 逐项退出条件，保留部分评估、未验证和 Source 失败；首个独立包发布不代表全部迁移目标完成。
5. 已发布 0.1.0 不覆盖重传；若运行代码需修复，按影响检查并准备后续版本。纯证据和文档更新不重建未变发行包。

E16–E19 已按 [逐条件清单](iterations/E16_E19_ACCEPTANCE.md)收口，E17 保留私有目标数组的 11 个严格浮点差异；这不阻止如实记录已观察最终几何，也不证明任意近似平局选择一致。[高级几何增量](ADVANCED_GEOMETRY.md)补齐固定端口、最小尺寸、样条、标签间距及真实 section 连接约束，部分评估仍保留。

可复用证据：冻结开发全量 37 步／917 测试、原 0.0.1a0 的八格 wheel 与两个 sdist 代表平台、当前候选的逐算法性能、独立几何谓词及选项效果账本。每项都只支持其执行版本、源码和适用范围。见 [完整实现](FULL_NATIVE_IMPLEMENTATION.md)、[性能报告](FULL_PERFORMANCE.md)、[选项覆盖](iterations/FULL_OPTION_COVERAGE.md)。

便携选项证据的恢复与严格检查：

```shell
python scripts/iteration/option_evidence.py --restore
python scripts/iteration/option_coverage.py --check --evidence-manifest references/full-native-closure/options.manifest.json
```

原始根目录改变时使用脚本的显式 `--root-map ORIGINAL=CURRENT` 参数；不要偷偷回退读取旧工作区。`--check-structure` 只检查结构，不是效果证据验收。

变更校验使用 `scripts/iteration/ci_selected.py` 和 [当前 manifest](iterations/full-native-ci-checks.json)。完整校验入口 `scripts/check.py` 留给最终验收，不因检查工具或文档变更重复运行。来源固定、分工、证据和负控制规范见 [实现策略](IMPLEMENTATION_PLAN.md)、[并行规范](PARALLEL_EXECUTION.md)和 [校验政策](VALIDATION_POLICY.md)。

以前逐批追加的入口文案见 [历史副本](NEW_SESSION.history-20261104.md)，不得用其中“正式 src 仍 E11”“完整算法仍 0”等历史描述替代当前工作树。
