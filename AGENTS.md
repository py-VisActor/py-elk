# py-elk 会话入口

先读 [新会话入口](docs/NEW_SESSION.md)、[实现策略](docs/IMPLEMENTATION_PLAN.md#2a-python实现策略)、[具体迭代计划](docs/ITERATION_PLAN.md) 和 [布局校验手册](docs/LAYOUT_VALIDATION.md)，实际完成状态以 [RELEASE_STATUS](docs/RELEASE_STATUS.md) 为准。
执行进度/依赖见 [iteration-plan.json](docs/iteration-plan.json)：当前下一轮E01。E01–E12交付独立基础正式包，E13–E21扩展全量能力；所有实现迭代当前为planned。

从本项目根目录、CPython 3.11+ 执行：

```shell
python scripts/check.py --out test-runs/session-01
```

每次使用新输出目录；report.json 保存命令、退出码、日志和源 SHA。该命令无需 Node/网络/安装依赖。
Node 可用时按手册执行官方重采；真实 Python 实现完成后按 candidate-command → candidate → compare 接入。

当前只有包骨架和验证工具，没有 Python ELK/layout API、算法或正式发行包。工具自测/官方回放成功不等于 Python 算法通过。
唯一行为基线为 elkjs 0.12.1，完整默认目录分母12算法/243选项/8类别不删减；现有25例是项目自行编写输入，不是完整上游断言集。
Python运行时目标为原生计算，无Node/JVM/浏览器/Canvas fallback。先完成独立基础包并正式发布0.1.0，py-mermaid集成后置独立步骤。
后续任务、来源/许可缺口、严格JS副作用与Python输入保留目标的待决策差异见上述文档，保留原始结果与失败证据。
