# 维护者与 AI agent / Development

本目录面向修改仓库、接续任务、来源复核与发行维护。安装使用请先读 [用户文档](../README.md)。
版本、依赖与构建配置从 `pyproject.toml` 读取；实际发行状态见状态记录。代码在 `src/pyelk`，`.local` 和历史切片不是生产实现。
AI agent 的适用范围、开始工作、仓库地图、命令、修改约束与完成条件统一见 [AGENTS](../../AGENTS.md)。

## 开始一次变更

1. 阅读 [AGENTS](../../AGENTS.md)，检查 `git status --short`，保留工作区修改。
2. 核对当前任务与文件 owner；需要继续旧任务时读 [NEW_SESSION](../NEW_SESSION.md)，
   再看 [发布/实施状态](../RELEASE_STATUS.md) 与 [机器任务账本](../implementation-backlog.json)。
3. 按影响范围选择检查，保留新命令日志和失败；文档整理不执行算法、构建安装或平台矩阵。
4. 来源独立期望、实现、实际执行与发布结果分开记录，不重绑旧执行SHA。

## 本地开发

需要源码开发环境时，在项目根目录创建独立虚拟环境并安装开发依赖：

```shell
python -m venv .venv
# 激活环境后 / after activating the environment:
python -m pip install -e ".[dev]"
```

以上是维护者操作，不是使用包的前置条件；本次文档整理未执行安装。
受影响检查按 [显式CI清单](../iterations/full-native-ci-checks.json) 与 [验证规则](../VALIDATION_POLICY.md) 选择。
未知影响先分析，不自动退回全量。`python scripts/check.py --out test-runs/UNIQUE`
是最终完整检查入口，仅在任务明确要求最终验收时运行。

## 当前工程资料

| 工作 | 资料 |
| --- | --- |
| 公共接口与宿主差异 | [API_COMPATIBILITY](../../API_COMPATIBILITY.md) |
| 生产实现总览 | [FULL_NATIVE_IMPLEMENTATION](../FULL_NATIVE_IMPLEMENTATION.md) |
| 验证与几何 | [LAYOUT_VALIDATION](../LAYOUT_VALIDATION.md) · [ADVANCED_GEOMETRY](../ADVANCED_GEOMETRY.md) |
| 并行所有权与交接 | [PARALLEL_EXECUTION](../PARALLEL_EXECUTION.md) |
| 测试与发行维护 | [TEST_AND_RELEASE](../TEST_AND_RELEASE.md) · [0.1.0发行记录](../releases/0.1.0.md) |
| 固定来源及第三方许可 | [UPSTREAM.json](../../UPSTREAM.json) · [来源索引](../../references/README.md) · [通知](../../THIRD_PARTY_NOTICES.md) |
| 原版采集工具 | [tools/reference](../../tools/reference/README.md)；仅研发使用，不是生产依赖 |

## 历史、审计与原始证据

这些入口保留当时的状态、边界与SHA，不作为新的默认待办或当前用户API指南。

- 规划与任务：[DEVELOPMENT_PLAN](../../DEVELOPMENT_PLAN.md)、[IMPLEMENTATION_PLAN](../IMPLEMENTATION_PLAN.md)、
  [ITERATION_PLAN](../ITERATION_PLAN.md)、[TASKS](../TASKS.md)、[iteration-plan.json](../iteration-plan.json)。
- 早期阶段：E04–E10等 `docs/E*_*.md`；例如 [E08生命周期切片](../E08_API_LIFECYCLE.md)
  的1算法/9选项边界与旧示例断言不代表0.1.0当前注册范围。
- 有限条件验收：[E13–E15](../iterations/E13_E15_ACCEPTANCE.md)、[E16–E19](../iterations/E16_E19_ACCEPTANCE.md)、
  [E20–E21](../iterations/E20_E21_ACCEPTANCE.md)。注册数量不能代替语义/坐标证据。
- 原始发行：[实际PyPI发布JSON](../releases/evidence/published-0.1.0/publication.json)。
  工作区文档更新不改写已发布包，也不能视作新发行或新安装验收。
- 复盘与决策分别保留在 `docs/retrospectives/`、`docs/decisions/`；不批量移动原始文件。
- 本次受众整理前的首页/agent/示例目录原文在
  [audience-before-20261107](../history/audience-before-20261107/AGENTS.txt) 同目录的 `.txt` 快照中。

py-mermaid 集成属于另一项目；不要仅因本仓历史I0–I3计划而自动发起跨项目任务。
## 文档分类索引

[逐文件受众清单](documentation-inventory.json)区分用户、开发、历史、证据与许可资料。旧路径保留来源上下文；清单不把旧验收提升为当前功能结论。
