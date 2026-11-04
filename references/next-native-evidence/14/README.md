# py-elk

中文 | [English](README.en.md)

面向 Python 的原生图布局引擎，目标是实现 Eclipse Layout Kernel（ELK）的布局能力，并对齐 JavaScript 版本 **elkjs** 的公开接口和 ELK JSON 数据格式。

**当前状态：原生 Python `ELK` 实验切片提供受限 layered、异步进程执行和实例隔离的元数据查询；尚未正式发布。** 输入范围为0–8节点、最多28条原始边，支持四方向、多连通分量、环、自环、独立平行边及长边。布局使用真实方向变换、组件拆分与打包、破环、分层和正交路由执行链。API、取消/关闭与资源边界见[E08手册](docs/E08_API_LIFECYCLE.md)，72输入布局范围见[E07手册](docs/E07_DIRECTIONS_COMPONENTS.md)，实际验收以[状态页](docs/RELEASE_STATUS.md)为准。完整算法和正式发行仍需后续验收。

## 项目目标

E09 实验接口支持 `await elk.layout(graph, {"logging": True, "measureExecutionTime": True})`：日志树采集自真实处理器调用，根 `logging` 为保留字段，嵌套业务同名字段保留。`executionTime` 延续固定 elkjs 的整数 wall 毫秒差乘1000再乘1e-9，不能当作普通秒或CPU时间。运行示例见 [diagnostics.py](examples/diagnostics.py)，精确规则见 [ADR0008](docs/decisions/0008-e09-diagnostics-coverage.md)；本轮最终验收仍以状态页和同包证据为准。

- 在 Python 中实现布局算法；运行布局不依赖 Node.js、Java、浏览器或对 elkjs 的子进程调用。
- 兼容 elkjs 的 `ELK` 入口、异步布局调用、元数据查询、选项命名及输入输出字段。
- 优先完成 `layered`：分层布局、节点定位、边路由、端口与层级图，再逐步扩展其他算法。
- 通过固定版本的 JavaScript 参考实现建立差分测试，持续记录支持范围和数值差异。
- 适用于流程图、数据流图，以及 py-mermaid 等上层图形项目的布局后端；本项目只计算几何信息，不承担渲染。
- py-mermaid 后续将布局后端替换成 py-elk，以本项目的 elkjs 0.12.1 为唯一行为基线，不建立旧 ELK 版本的兼容分支。

## 对齐基线

| 项目 | 基线 |
| --- | --- |
| JavaScript 参考实现 | [kieler/elkjs](https://github.com/kieler/elkjs) |
| 固定版本 | [elkjs 0.12.1](https://github.com/kieler/elkjs/releases/tag/0.12.1) |
| 固定提交 | `624ae90aa37110033a8af59c5ccbb292708b4317` |
| 公开接口依据 | [该版本 TypeScript 声明](https://github.com/kieler/elkjs/blob/624ae90aa37110033a8af59c5ccbb292708b4317/typings/elk-api.d.ts) |
| 行为依据 | 该版本实际运行结果；M1 阶段采集参考样例 |
| Python 目标环境 | Python 3.11 及以上（初始设计） |
| 拟定发布名 / 导入名 | `py-elk` / `pyelk`；发布前确认名称可用性 |

基线在 2026-11-02 核验。升级参考版本时必须更新基线记录、重新生成样例并审查差异，不直接跟随上游开发分支。

真实默认注册元数据为 **12 个算法、243 个选项、8 个类别**，均保留在[兼容清单](docs/compatibility.json)。实验切片单列，不提升完整算法通过数。64 个 elkjs 源文件（含 14 个 Mocha 文件）是来源索引，不是断言通过数。精确外部Java构建仍未核实；当前移植使用独立审查的固定生成worker，见[来源说明](references/README.md)。

## 开始开发

以下命令在项目根目录使用 CPython 3.11+ 执行。先创建并激活独立环境，再安装本地开发骨架；这不是已发布产品的安装说明。

```shell
python -m venv .venv
```

激活环境后：

```shell
python -m pip install -e ".[dev]"
python scripts/check.py --out test-runs/start-01
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py fetch
python scripts/upstream.py check
python examples/show_scope.py
```

来源检查需要 Git/首次下载网络；Node 只用于[开发参考采集](tools/reference/README.md)，不是运行时依赖。离线入口包含实际Python切片对照；bootstrap检查本身只核结构与声明。
已提供真实官方布局采集、完整差分、独立几何、确定性和负控制脚本，新会话见 [布局校验手册](docs/LAYOUT_VALIDATION.md)。

## 实验切片调用

以下例子可以在当前本地开发包执行。更多输入限制见[切片说明](docs/E07_DIRECTIONS_COMPONENTS.md)：

```python
import asyncio
from pyelk import ELK

async def main():
    elk = ELK({"defaultLayoutOptions": {"elk.algorithm": "layered"}})
    graph = {
        "id": "root",
        "children": [
            {"id": "a", "width": 40, "height": 30},
            {"id": "b", "width": 40, "height": 30},
        ],
        "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]}],
    }
    try:
        print(await elk.knownLayoutAlgorithms())
        result = await elk.layout(graph, {"layoutOptions": {
            "elk.algorithm": "layered", "elk.direction": "RIGHT"
        }})
        print(result)
    finally:
        elk.terminateWorker()

if __name__ == "__main__":
    asyncio.run(main())
```

保留`defaultLayoutOptions`、`layoutOptions`和camelCase方法名；logging/timing仅接受bool，缺省为false，true采集真实执行诊断。实际CPU布局在Python spawn子进程执行，每实例单工作槽、FIFO队列；取消、超时与关闭会回收工作进程。`max_pending=16`限制运行加排队总数（可配1–64），`timeout=None`可改为包含排队/启动的总期限秒数；不承诺硬内存配额。三项查询只描述本实例实际注册的受限layered、九项解析选项及对应类别，不把官方12/243/8目录当作当前支持列表。原始输入保持不变，实例空闲时可跨多次`asyncio.run`复用；详见[E08手册](docs/E08_API_LIFECYCLE.md)。

## 文档

- [接口对齐要求与兼容矩阵](API_COMPATIBILITY.md)：API、数据模型、选项、算法、异常与验收标准。
- [开发计划](DEVELOPMENT_PLAN.md)：里程碑、架构、差分测试方案和首批任务。
- [上游基线记录](UPSTREAM.json)：可供后续测试工具读取的版本和来源信息。
- [新会话入口](docs/NEW_SESSION.md)、[完整实施方案](docs/IMPLEMENTATION_PLAN.md)、[逐项任务](docs/TASKS.md)。
- [Python实现策略](docs/IMPLEMENTATION_PLAN.md#2a-python实现策略)、[具体迭代计划](docs/ITERATION_PLAN.md)、[机器进度索引](docs/iteration-plan.json)：先12轮交付基础正式包，再9轮扩展；当前完成状态与下一轮以机器索引为准。
- [并行协作规范](docs/PARALLEL_EXECUTION.md)：每轮root+A/B/V、独占文件、交接/反审与复盘改进。
- [原生合同与比较profile](docs/decisions/0001-native-contract.md)、[E07复盘](docs/retrospectives/E07.md)、[E08分工](docs/iterations/E08.md)：来源、实现、反审与下一轮改进。
- [首个正式包范围](docs/FIRST_RELEASE_SCOPE.md)：先完成独立基础版并发布正式 0.1.0，再单独进行 py-mermaid 集成。
- [测试与发布](docs/TEST_AND_RELEASE.md)、[当前状态](docs/RELEASE_STATUS.md)、[py-mermaid 集成](docs/MERMAID_INTEGRATION.md)。
- [源码与元数据](references/README.md)、[可运行范围示例](examples/README.md)、[许可状态](THIRD_PARTY_NOTICES.md)。

## 实现状态

| 能力 | 当前状态 | 计划阶段 |
| --- | --- | --- |
| 骨架、来源锁、元数据分母、规划和检查工具 | 已建立；限定验证见状态页 | M0 |
| ELK JSON 模型、异步 API、参考样例工具 | 有序模型、九项解析、最小ELK入口与真实oracle；完整M1未完成 | M1 |
| 平面图 layered 核心流程 | E07限定四方向/多组件切片可调用，完整范围待收口 | M2 |
| 基础输入/选项、API/错误与坐标闭环 | 72输入的受限实验校验，实际验收见状态页 | M3 |
| 独立候选、平台/生命周期/基本性能与真实布局安装 | 实验wheel隔离安装通过；完整验收待完成 | M4 |
| 正式 Python 包 0.1.0、许可与下载复验 | 未发布；本地版本0.0.1a0 | M5 |
| 高级端口/标签/层级、完整 layered 策略与选项 | 未实现 | M6 |
| 其他 11 个算法 | 未实现 | M7 |
| 全量可靠性与后续正式发行 | 未验收 | M8 |
| py-mermaid 后端适配与集成 | 后置独立步骤，不阻塞基础包发布 | I0–I3 |

实现状态必须以测试证据更新。名称相同或能够返回坐标，并不代表算法行为或坐标已经与 elkjs 一致。

## 上游与许可

本仓库是独立的 Python 实现项目，不是 ELK 官方发行版。项目自行编写的代码使用 [MIT](LICENSE)。ELK 移植文件保留 `EPL-2.0 OR GPL-3.0-or-later`、来源及版权，Apache 辅助代码保留其许可与归属。发行包使用混合来源表达式 `MIT AND (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0`；具体范围见 [第三方通知](THIRD_PARTY_NOTICES.md)。
