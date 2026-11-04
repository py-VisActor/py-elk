# 新会话入口

项目位于 `C:/code/py-visactor/py-elk`，不是环境可能显示的 `py-mermaid`。当前工作树是权威状态，先看 [任务账本](implementation-backlog.json)及 [发行状态](RELEASE_STATUS.md)。

全部功能已迁入 `src/pyelk`，正在统一校验及定向修复。12 个算法、243 个选项、8 个类别已注册；这些数量不代表所有选项值和组合都验证正确。`py-mermaid` 集成及绘制不在当前目标中。

MrTree BFS 的第二次 Walker 控制环已修复；新候选已完成 Windows wheel/sdist 和 Linux wheel 受影响安装。发行候选处于最终证据收口，尚未上传；不得用旧版本差异证明放行新源码。V 正在完成新增选项证据归档，A 核对退出条件，root 负责发行交付。

接续顺序：

1. 查看 [机器任务账本](implementation-backlog.json)、[迭代计划](iteration-plan.json)和 agent 实际状态，避免覆盖仍在执行的工作。
2. 修复后只运行受影响的 MrTree 检查，保存原版 RangeError 与 Python 异常的真实差异；不要重复采集已完成的 52 个正常非 Layered 输入。
3. 重建 0.1.0 wheel/sdist，在仓库外实际安装并验证修复；保留旧候选和旧执行，不重绑证据。
4. 收口选项效果账本、便携证据和 E11–E21 退出条件。有限证据必须保留其范围；未知项明确列出。
5. 用户已报告 `py-visactor-elk` 的 pending publisher 添加成功；候选通过发行审阅后上传，再下载核对实际上传产物 SHA 并安装。尚未发布不能标目标完成。

可复用证据：冻结开发全量 37 步／917 测试、原 0.0.1a0 的八格 wheel 与两个 sdist 代表平台、当前候选的逐算法性能、独立几何谓词及选项效果账本。每项都只支持其执行版本、源码和适用范围。见 [完整实现](FULL_NATIVE_IMPLEMENTATION.md)、[性能报告](FULL_PERFORMANCE.md)、[选项覆盖](iterations/FULL_OPTION_COVERAGE.md)。

便携选项证据的恢复与严格检查：

```shell
python scripts/iteration/option_evidence.py --restore
python scripts/iteration/option_coverage.py --check --evidence-manifest references/full-native-closure/options.manifest.json
```

原始根目录改变时使用脚本的显式 `--root-map ORIGINAL=CURRENT` 参数；不要偷偷回退读取旧工作区。`--check-structure` 只检查结构，不是效果证据验收。

变更校验使用 `scripts/iteration/ci_selected.py` 和 [当前 manifest](iterations/full-native-ci-checks.json)。完整校验入口 `scripts/check.py` 留给最终验收，不因检查工具或文档变更重复运行。来源固定、分工、证据和负控制规范见 [实现策略](IMPLEMENTATION_PLAN.md)、[并行规范](PARALLEL_EXECUTION.md)和 [校验政策](VALIDATION_POLICY.md)。

以前逐批追加的入口文案见 [历史副本](NEW_SESSION.history-20261104.md)，不得用其中“正式 src 仍 E11”“完整算法仍 0”等历史描述替代当前工作树。
