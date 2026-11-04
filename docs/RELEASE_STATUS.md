# 当前状态

功能迁移已完成，首个独立发行 **[py-visactor-elk 0.1.0](https://pypi.org/project/py-visactor-elk/0.1.0/)** 已正式发布并完成 PyPI 下载、wheel/sdist 安装复验。导入名保留 `pyelk`。全部声明分支的 E20/E21 验收仍在继续；权威状态见 [任务账本](implementation-backlog.json)及 [实际发行证据](releases/evidence/published-0.1.0/publication.json)。

正式源码是 `src/pyelk`：196 个 Python 模块、208 个运行文件，12 个算法、243 个选项、8 个类别。`py-mermaid` 集成后置。实现接线完成不等于所有输入、选项值和组合的行为均已验证。

已完成的校验包括冻结 0.0.1a0 的 37 步／917 测试、该包的 Windows/Linux × Python 3.11–3.14 wheel 矩阵及两个 sdist 代表；选定公共输入的原版对比；0.1.0 候选安装和 Windows 3.13 的性能测量。各结果保留原版本与源码绑定，不将它们改称新修复代码的执行结果。

已修复 MrTree BFS 的兄弟控制环：原版抛 RangeError，原生现在按活动调用路径检测并抛 RecursionError，差异明确保留。正常公共输入、共享节点合法重访和 1500 层链通过；新 0.1.0 候选已完成 Windows wheel/sdist 双安装及 Linux wheel 受影响安装。

剩余工作：

- 完成有限声明分支和 243 选项角色的证据映射，关闭确实缺失的见证；当前 73 项 scoped geometry／15 项 scoped state 和便携归档已收口。
- 复用已归档的真实状态 DTO、旧枚举和 Source 边界；只为仍无证据的明确分支补最小见证，不重跑未变数学组。

E16–E19 的明示条件已按 [独立算法清单](iterations/E16_E19_ACCEPTANCE.md)在实际证据范围内收口；E17 私有目标值的 11 个严格差异保留。新增[高级几何约束](ADVANCED_GEOMETRY.md)的 24 个公共结果及 4 个堆叠状态提供 154 项增量检查，无已适用失败，14 个公共结果仍为 PARTIAL。E13–E15／E20／E21 的未完验收继续明确列出。

当前选项覆盖和高级几何仅作其声明范围内的证明，未评估项继续保留；独立算法几何的 28 个观察另有双方各 10 PASS／4 NOT_ASSESSED，见 [独立算法几何](INDEPENDENT_ALGORITHM_GEOMETRY.md)。详见 [选项账本](iterations/FULL_OPTION_COVERAGE.md)、[性能边界](FULL_PERFORMANCE.md)及 [发行说明](releases/0.1.0.md)。

执行政策：先实现所有功能，再统一校验和修复；修复只检查受影响项，最后全量验收。已通过的数学组和平台矩阵不因无关改动重复运行。以前逐批进度文案已移至 [历史副本](RELEASE_STATUS.history-20261104.md)，不得作为当前状态。
