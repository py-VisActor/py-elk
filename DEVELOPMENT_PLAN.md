# py-elk 开发计划入口

先交付可独立使用的基础py-elk并发布正式Python包，py-mermaid集成拆成后置独立步骤。
唯一行为基线保持elkjs0.12.1；不维护旧ELK兼容分支。当前仍无布局实现或已发布包。

实现采用可追溯的语义移植：保留默认策略/处理顺序/排序/随机/数值行为，用Python组织模块与有序模型，逐轮通过固定参考差分和独立几何验收。
E07已实现有序模型/配置/context之上的真实ELK四方向、多组件、多重图/长边切片，下一轮按[E08 brief](docs/iterations/E08.md)处理API/错误/生命周期，再按E09–E12收口并正式发布。来源gate仅对ADR0006的33组件固定生成源切片verified，精确外部Java构建仍unresolved；完成状态以机器索引为准。

- [完整实施方案](docs/IMPLEMENTATION_PLAN.md)：架构、来源缺口、全范围与阶段门禁。
- [Python实现策略](docs/IMPLEMENTATION_PLAN.md#2a-python实现策略)、[具体迭代执行计划](docs/ITERATION_PLAN.md)：每轮任务、代码落点、前置与验收。
- [机器进度索引](docs/iteration-plan.json)：E01–E21与I0–I3的实际状态、依赖、门禁和M工作包对应。
- [每轮并行协作规范](docs/PARALLEL_EXECUTION.md)：root+A/B/V分工、文件归属、交接/反审、稳定验收与逐轮复盘。
- [首个正式包范围](docs/FIRST_RELEASE_SCOPE.md)：基础0.1.0的能力、限制和发行验收。
- [逐项任务](docs/TASKS.md)：M0–M8主线及独立I0–I3。
- [接口契约](API_COMPATIBILITY.md)、[当前状态](docs/RELEASE_STATUS.md)、[启动入口](docs/NEW_SESSION.md)。
- [测试/发布](docs/TEST_AND_RELEASE.md)、[独立集成](docs/MERMAID_INTEGRATION.md)。

| 阶段 | 内容 |
| --- | --- |
| M0 | 骨架、来源/元数据锁、清单、开发检查与本地骨架验证 |
| M1 | 首版所需source/license、断言、API/JSON/options、官方oracle |
| M2 | 原生基础layered真实垂直切片 |
| M3 | 基础输入/9选项/错误/API/坐标闭环 |
| M4 | 独立候选包、平台、生命周期/限制、基本性能和真实布局安装 |
| M5 | 首个正式Python包0.1.0：上传、索引、下载核SHA和布局复验 |
| M6 | 端口/标签/层级、完整layered策略/路由及适用选项 |
| M7 | 其他11个算法分别扩展和验收 |
| M8 | 全量兼容、可靠性、平台/规模和后续正式发行 |
| I0–I3 | 使用已发布py-elk的py-mermaid能力核对、适配、回归和集成交付 |

原草案的25/50/100样例数保留为首批组织/压力输入参考，完成标准由声明范围的断言决定。
12算法/243选项/8类别完整分母不因基础版先发布而删除；基础包不等待全量扩展或上层集成。

本地起点没有.git；2026-11-03已核实组织仓库 [py-VisActor/py-elk](https://github.com/py-VisActor/py-elk) 并连接main，保留远端初始提交历史。实际源码同步状态见RELEASE_STATUS和GitHub提交记录。
原始四份文件已有修改前副本。当前结构骨架只用于本地检查；正式发布必须先满足真实功能、许可、候选和发行门禁。
