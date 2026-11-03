# py-elk

中文 | [English](README.en.md)

面向 Python 的原生图布局引擎，目标是实现 Eclipse Layout Kernel（ELK）的布局能力，并对齐 JavaScript 版本 **elkjs** 的公开接口和 ELK JSON 数据格式。

**当前状态：已有包骨架、来源/元数据锁、迭代计划及真实参考采集/布局校验脚本；没有可运行的 Python ELK/layout API、布局实现或已发布 Python 包。** 当前包只公开版本信息。

## 项目目标

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

真实默认注册元数据为 **12 个算法、243 个选项、8 个类别**，均已登记在[兼容清单](docs/compatibility.json)，Python 实现状态全部待完成。64 个 elkjs 源文件（含 14 个 Mocha 文件）是来源索引，不是断言通过数。Java 算法源码与生成 worker 的精确对应仍待审计，见[来源说明](references/README.md)。

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

来源检查需要 Git/首次下载网络；Node 只用于[开发参考采集](tools/reference/README.md)，不是运行时依赖。当前没有算法可调用，不能把 bootstrap 检查当作布局通过。
已提供真实官方布局采集、完整差分、独立几何、确定性和负控制脚本，新会话见 [布局校验手册](docs/LAYOUT_VALIDATION.md)。

## 目标调用方式

以下是**拟实现接口**，目前不能执行：

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
    result = await elk.layout(graph, {"layoutOptions": {
        "elk.algorithm": "layered", "elk.direction": "RIGHT"
    }})
    print(result)

asyncio.run(main())
```

兼容层保留 `defaultLayoutOptions`、`layoutOptions`、`measureExecutionTime` 和 camelCase 方法名。Python 风格的别名和同步便利接口属于扩展项，不能改变兼容入口的语义。

## 文档

- [接口对齐要求与兼容矩阵](API_COMPATIBILITY.md)：API、数据模型、选项、算法、异常与验收标准。
- [开发计划](DEVELOPMENT_PLAN.md)：里程碑、架构、差分测试方案和首批任务。
- [上游基线记录](UPSTREAM.json)：可供后续测试工具读取的版本和来源信息。
- [新会话入口](docs/NEW_SESSION.md)、[完整实施方案](docs/IMPLEMENTATION_PLAN.md)、[逐项任务](docs/TASKS.md)。
- [Python实现策略](docs/IMPLEMENTATION_PLAN.md#2a-python实现策略)、[具体迭代计划](docs/ITERATION_PLAN.md)、[机器进度索引](docs/iteration-plan.json)：先12轮交付基础正式包，再9轮扩展；当前下一轮E01。
- [首个正式包范围](docs/FIRST_RELEASE_SCOPE.md)：先完成独立基础版并发布正式 0.1.0，再单独进行 py-mermaid 集成。
- [测试与发布](docs/TEST_AND_RELEASE.md)、[当前状态](docs/RELEASE_STATUS.md)、[py-mermaid 集成](docs/MERMAID_INTEGRATION.md)。
- [源码与元数据](references/README.md)、[可运行范围示例](examples/README.md)、[许可状态](THIRD_PARTY_NOTICES.md)。

## 实现状态

| 能力 | 当前状态 | 计划阶段 |
| --- | --- | --- |
| 骨架、来源锁、元数据分母、规划和检查工具 | 已建立；限定验证见状态页 | M0 |
| ELK JSON 模型、异步 API、参考样例工具 | 已有25例真实参考/比对脚本；Python模型/API未实现，M1未完成 | M1 |
| 平面图 layered 核心流程 | 未实现 | M2 |
| 基础输入/选项、API/错误与坐标闭环 | 未实现 | M3 |
| 独立候选、平台/生命周期/基本性能与真实布局安装 | 未验收 | M4 |
| 正式 Python 包 0.1.0、许可与下载复验 | 未发布；仅可本地检查骨架 | M5 |
| 高级端口/标签/层级、完整 layered 策略与选项 | 未实现 | M6 |
| 其他 11 个算法 | 未实现 | M7 |
| 全量可靠性与后续正式发行 | 未验收 | M8 |
| py-mermaid 后端适配与集成 | 后置独立步骤，不阻塞基础包发布 | I0–I3 |

实现状态必须以测试证据更新。名称相同或能够返回坐标，并不代表算法行为或坐标已经与 elkjs 一致。

## 上游与许可

本仓库是独立的 Python 实现项目，不是 ELK 官方发行版。上游 elkjs 的许可证标识为 `EPL-2.0 OR GPL-3.0-or-later`。当前未复制上游实现代码；后续若移植源码，应逐文件保留版权及许可声明，记录来源。本仓库的发行许可在首次代码发布前确定。
