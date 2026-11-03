# 当前状态

2026-11-03：**结构、规划与布局验证工具阶段，没有 Python 布局实现，没有正式发布 Python 包。**
本地 `0.0.1a0` 只公开版本信息，不能调用 README 设计稿中的 ELK/layout。

源码仓库已核实为 [py-VisActor/py-elk](https://github.com/py-VisActor/py-elk)，默认分支main。
2026-11-03本地Git初始化并连接origin，以远端初始README提交`8288240963843e7295a55550c12eea30f3f72b67`为基础同步现有结构、工具和规划，保留历史。
源码提交不表示Python包已发布；实际推送与CI结果以GitHub对应提交/Actions为准。

2026-11-03新增实现策略与具体迭代规划：[实现策略](IMPLEMENTATION_PLAN.md#2a-python实现策略)、[21轮执行计划](ITERATION_PLAN.md)、[机器索引](iteration-plan.json)。
E01–E12交付基础正式包，E13–E21扩展全量能力，I0–I3仍为独立集成；下一轮E01，各实现迭代均planned。
本次仅落地规划和入口文档，Python实现/来源缺口/profile适配/发布状态未因此提升。记录见 [20261103-implementation-strategy.json](changes/20261103-implementation-strategy.json)。

本次新增真实官方布局验证工具：一键检查、独立进程JS/Python适配器、完整JSON差分、既定几何数值容差、平面正交几何、确定性、负控制和来源指纹校验。
25个自行编写案例的官方快照已保存，每例2次独立Node进程；新重采默认3次。
操作入口为 [NEW_SESSION](NEW_SESSION.md) 与 [LAYOUT_VALIDATION](LAYOUT_VALIDATION.md)。

2026-11-03实际验证：

- Windows / CPython 3.13.15：14项bootstrap、42项校验回归、25例官方快照与20项控制通过；Node 24.19.0真实重采/回放通过。
- WSL Ubuntu / CPython 3.14.4：离线一键检查已通过；具体最终命令、退出码与范围见本次变更记录。
- 安装的旧版本骨架缺少ELK时，真实candidate运行失败，原始ImportError/退出码留存，未生成成功布局观察。
- 所有Python算法/API/坐标兼容状态仍未实现；严格JS输入副作用与Python不修改输入目标的适配决策仍待M1解决。

证据和文件指纹见 [20261103-layout-validation.json](changes/20261103-layout-validation.json)。
CI增加工具自测/官方重采回放配置，未宣称远端CI执行成功。Python3.11/3.12和Windows3.14本轮未执行。

以下为2026-11-02项目骨架与来源验证记录，保留原有范围：

已建立：src 包元信息/类型标记和职责目录、pyproject/开发依赖、双语入口、M0–M8 及独立 I0–I3、
首版0.1.0范围/机器profile、兼容账本、来源工具、bootstrap/负控制、CI配置、范围查看例子。
当前 CI 是配置，未把它写成远端执行成功。

已真实核实的来源与范围：

- elkjs 0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`；npm gitHead一致，tarball integrity/SHA及12个发行文件固定。
- 64个elkjs Git文件含14个Mocha文件，11个关键canonical blob SHA固定；不是断言通过数。
- 官方bundled默认注册元数据为12算法、243选项、8类别；Python实现全部planned。
- bundled/FakeWorker调用terminateWorker实测TypeError，初次采集失败已保留；修订采集器明确记录throws，不称生命周期通过。

Java算法源码与生成worker的精确对应仍unresolved；自有发行许可待确定。
起点目录没有.git；预期组织仓库访问未核实，未宣称创建/发布/推送成功。

本轮验证记录见 [20261102-project-structure.json](changes/20261102-project-structure.json)。
来源检查、结构/负控制、元数据重采与本地骨架打包的实际命令、退出码和SHA各自记录；
它们不能提升任何算法为已实现，也不满足正式包的真实布局门禁。

本轮实际限定验证（Windows / CPython 3.13.15 / Node 24.19.0）：

| 检查 | 实际结果与范围 |
| --- | --- |
| bootstrap 与负控制 | 14项测试通过，包括分母删除、伪验证、缺证据、元数据/来源漂移、archive越界及首版集成依赖错误 |
| 上游来源 | 固定Git提交/关键blob、64文件索引和npm发行文件核验通过 |
| 官方元数据重采 | 默认12/243/8原始目录与保存快照一致，terminate异常独立记录 |
| 本地骨架构建 | wheel/sdist构建通过，未上传 |
| 隔离安装/导入 | 新环境、仓库外-I、移除PATH/PYTHONPATH/PYTHONHOME；包从site-packages导入，只公开版本信息 |

Linux及Python3.11/3.12/3.14本轮未执行；CI矩阵不替代实际结果。没有任何Python算法/API/坐标通过数或正式发布结论。

当前优先顺序是M1–M4独立基础功能/候选验收 → M5正式Python包0.1.0发布 → 后续M6–M8扩展。
py-mermaid集成单独后置I0–I3，不作为基础包发布前提，也不维护旧ELK兼容分支。
