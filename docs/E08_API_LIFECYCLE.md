# E08 API、元数据与执行生命周期

本页是 E08 的历史范围；E09 已在 [ADR0008](decisions/0008-e09-diagnostics-coverage.md) 续接日志/计时 true。下述 E08 的拒绝与31/48步计数仅对应当轮，当前状态及命令以机器计划和状态页为准。

本页说明[ADR0007](decisions/0007-e08-api-lifecycle.md)及[机器合同](../references/e08-host-contract.json)对应的受限公开接口。实际完成范围以[发布状态](RELEASE_STATUS.md)及机器证据为准；局部测试或示例成功不代表完整算法或正式发布通过。布局继续使用E07的受限算法，原有[72个输入与几何规则](E07_DIRECTIONS_COMPONENTS.md)保持不变。

## 最小调用与独立例子

```python
import asyncio
from pyelk import ELK

async def main():
    elk = ELK(max_pending=2, timeout=5.0)
    try:
        algorithms = await elk.knownLayoutAlgorithms()
        options = await elk.knownLayoutOptions()
        categories = await elk.knownLayoutCategories()
        result = await elk.layout({"id": "root"})
        print(len(algorithms), len(options), len(categories), result)
    finally:
        elk.terminateWorker()

if __name__ == "__main__":
    asyncio.run(main())
```

保存为独立`.py`文件再运行。执行采用`spawn`，主入口须加`if __name__ == "__main__"`，避免子进程导入主模块时再次启动父调用。

[完整例子](../examples/api_lifecycle.py)查询1个算法、9项选项和1个类别，执行真实双节点布局，验证调用方图及业务字段不变，并在`finally`中关闭实例。它直接导入`pyelk`，不修改导入路径、不读oracle。

已安装当前候选包时可运行：

```shell
python -I examples/api_lifecycle.py
```

这条命令必须使用实际安装了候选包的Python；缺包会明确失败。本轮同一新wheel的正式安装验收仍由集成记录确认，不能用源码导入替代。开发阶段验证当前源码，可临时指定`src`，例如PowerShell：

```powershell
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Resolve-Path src).Path
    python examples/api_lifecycle.py
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
```

Linux源码验证为`PYTHONPATH="$PWD/src" python examples/api_lifecycle.py`。源码示例的实际命令和输出保存于本轮`test-runs/20261103-E08-01/A/new-docs`；它仅证明该次源码示例执行。

## 构造、注册与查询

接口为`ELK(options=None, *, max_pending=16, timeout=None)`。`options`为mapping，`None`是Python宿主提供的省略便利。支持`defaultLayoutOptions`与`algorithms`；调用级`layoutOptions`显式出现时替换构造默认，包括空mapping，随后根节点局部选项按既有resolver覆盖。构造、图和调用参数被复制，返回值及`last_trace`也不与后续调用共享可变内容。

缺省注册受限layered。`algorithms`可包含`layered`或`org.eclipse.elk.layered`，重复和两种别名归一、去重；混入其他已知算法会明确拒绝，未知名称使用不同错误。`algorithms=[]`构造metadata-only实例：算法及类别查询为空，九项解析选项仍可查询，布局报`ALGORITHM_NOT_REGISTERED`。

三个查询都是async方法，各次返回独立JSON值：

| 方法 | 缺省实例返回范围 |
| --- | --- |
| `knownLayoutAlgorithms()` | 1个受限layered描述，实际`knownOptions`交集为8项 |
| `knownLayoutOptions()` | 9项已有解析选项，包含算法选择器 |
| `knownLayoutCategories()` | 与该实际注册算法相关的1个layered类别 |

选项保留固定参考的id/name/description/group/type/targets；存在与省略的字段均保留原形。`native`对象另列`valueType`、`defaultValue`、`acceptedValues`与`constraints`，区分解析域和可布局域。例如seed0和对象padding可被内部解析，当前布局分别要求非零seed及完整四边padding字符串。direction的声明默认仍是`UNDEFINED`；不能从某次结果为RIGHT改写属性默认。准确字段与顺序见[元数据schema](../references/e08-metadata-schema.json)。

算法描述限制为平面root/children、0–8个原始子节点、最多28条原始边、四方向和弱连通分量，支持受限环、自环及平行边。`supportedFeatures`仅列`SELF_LOOPS`和`MULTI_EDGES`，不宣称端口、标签或compound。所有数值、选项和图形限制继续由E07 guard检查，查询到某个选项不表示其全部上游取值已实现。

完整参考目录仍单独保留12算法/243选项/8类别。固定elkjs的空列表仍注册fixed/box/random，其模块静态注册还会跨实例累积；Python采用实例隔离。官方FakeWorker缺少terminate实现、会抛TypeError，Python正常关闭属于明确宿主设计。这些原始事实继续单独采集，不以Python返回值覆盖参考目录。

## 调度、容量、期限与关闭

每实例有一个实际spawn子进程工作槽，按FIFO执行；不同实例各自隔离。`max_pending`限制running与queued的总数，默认16，仅接受1–64的整数，bool不算整数。超限立即报`QueueFullError`，没有自动扩容或默认无限队列。

`timeout`为有限正数秒或`None`，覆盖提交、排队、进程启动及执行直至结果，不是仅计算算法的计时。到期任务停止并回收资源，抛`ExecutionTimeoutError`。这是任务总期限政策，不是OS级硬CPU配额，也没有默认硬RAM限制；同步JSON输入复制、系统调度和资源回收不构成硬实时保证。

实例空闲时可以在不同的`asyncio.run`/事件循环中顺序复用；已有活动任务时跨loop提交报`ExecutionError`，code为`EVENT_LOOP_CONFLICT`。这不承诺任意线程同时提交同一个实例。CPU布局在子进程中运行，管理线程在空闲后退出；输入快照的JSON检查与复制仍是调用方同步工作。

`terminateWorker()`同步关闭：先拒绝新工作，取消队列，停止并回收运行子进程及管理线程，关闭后查询和布局均报`ResourceClosedError`。它可等待资源回收；需要在`try/finally`中使用。重复正常关闭返回`None`；回收失败会明确报执行错误，不用“已关闭”掩盖未回收资源。

## 取消、错误与trace

通过`asyncio.create_task(elk.layout(...))`提交后，可调用`task.cancel()`并继续`await task`。排队取消不启动该任务；运行取消在停止、join并关闭进程资源后才向调用方完成`asyncio.CancelledError`。重复取消仍需完成清理。已经发布的成功结果可优先于后来的取消；仅请求取消或Future完成本身不能证明CPU已经停止。实际CPU、心跳、资源及恢复结论由独立生命周期收据确认。

公共输入错误继承`ValidationError`，都有`code`、`path`和`message`；`path`为JSON Pointer。执行错误继承`ExecutionError(RuntimeError)`，使用同样字段，保留内部失败和输入错误的区别。

| 情况 | 异常与典型code |
| --- | --- |
| 图结构或端点错误 | `ModelValidationError`，保留原类别和字段路径 |
| 选项容器、类型或值非法 | `OptionValidationError` |
| 未知选项 / 已知但未实现选项 | `UnknownOptionError(UNKNOWN_OPTION)` / `UnsupportedOptionError(UNSUPPORTED_OPTION)` |
| 未知算法 / 已知但未实现算法 | `UnknownAlgorithmError(UNKNOWN_ALGORITHM)` / `UnsupportedAlgorithmError(UNSUPPORTED_ALGORITHM)` |
| 实例未注册布局算法 | `UnsupportedAlgorithmError(ALGORITHM_NOT_REGISTERED)` |
| 显式`workerUrl`或`workerFactory` | `UnsupportedWorkerError(UNSUPPORTED_WORKER)`，同时属于`NotImplementedError`，不调用传入函数 |
| 关闭后调用 | `ResourceClosedError(RESOURCE_CLOSED)` |
| 容量 / 总期限 | `QueueFullError(QUEUE_FULL)` / `ExecutionTimeoutError(EXECUTION_TIMEOUT)`，后者同时属于`TimeoutError` |
| 子进程、导入、IPC或协议故障 | `WorkerExecutionError`，如`WORKER_EXITED`或`WORKER_PROTOCOL_ERROR` |

`logging=True`与`measureExecutionTime=True`目前仍明确unsupported，仅省略或false保留原E07路径；不会伪造日志树或固定耗时。完整日志/计时分支留待E09，原参考分母不减少。

每次进入layout先清空`last_trace`，只允许最后提交任务的成功trace发布；旧任务不能覆盖较新请求，失败、取消或关闭后保持空。读取返回独立副本。trace用于开发定位，不进入ELK JSON；合法空图可能有零个phase。进程/队列的内部snapshot是开发诊断，不是新增公开JSON协议。

## 当前校验与原始事实命令

从项目根目录使用新输出目录。局部回归可分别执行现有owner文件：

```shell
python -m unittest discover -s tests/api -p "test_e08_*.py" -v
python -m unittest discover -s tests/execution -p "test_e08_lifecycle.py" -v
```

固定官方采集器为`tools/reference/capture_e08_api.cjs`，由已存在的CLI驱动，保存原始请求、进程命令、日志、退出码和事件。当前定义为44例、每例3个独立参考进程；其中已知异步worker崩溃是保留的参考事实，不归一成成功API调用：

```shell
python scripts/validate_e08_api.py --with-reference --package .local/npm-elkjs/package --out test-runs/E08-api-reference-01
python scripts/validate_e08_api.py --verify-reference test-runs/E08-api-reference-01
python scripts/validate_e08_api.py --out test-runs/E08-api-offline-01.json
python scripts/validate_e08_runtime.py --out test-runs/E08-runtime-offline-01.json
```

前两条执行参考采集或核对指定收据；后两条核查版本化事实/当前包字节及收据一致性，**不重新执行候选布局**。集成材料尚未封存时明确失败是正常门禁，不能提前登记通过。

同一实际新wheel的21/36/52/72布局回归可用已存在的共享请求工具；路径须替换成本轮真实安装解释器和wheel：

```shell
python scripts/plan_suite_execution.py run --candidate-python <installed-python> --wheel <actual-wheel> --repeat 3 --jobs 2 --out test-runs/E08-current-layout-01
python scripts/plan_suite_execution.py verify test-runs/E08-current-layout-01
```

Windows解释器通常位于环境的`Scripts/python.exe`，Linux位于`bin/python`。工具绑定包、适配器、解释器、原请求及环境；181个suite用例、149种请求及每引擎三次独立重复不变。它不代替E08 API/生命周期安装验收。

同一安装包的API及真实生命周期采集和跨进程复验入口如下：

```shell
python scripts/validate_e08_api.py --candidate-python <installed-python> --wheel <actual-wheel> --repeat 3 --out test-runs/E08-current-api-01
python scripts/validate_e08_api.py --verify-candidate test-runs/E08-current-api-01/receipt.json
```

参考重采与候选采集分别保存原始字节；候选生命周期包括真实CPU阶段与心跳、running/queued取消、关闭/崩溃恢复、实例重叠及循环绑定。提交/启动期限与真正CPU执行取消分别报告；没有硬CPU/内存配额声明。实际安装包还可以用`<installed-python> -I tests/execution/test_e08_lifecycle.py -v`运行受控竞争和协议故障测试，该隔离入口不会插入src。

`export_e08_installed_evidence.py --run ... --api-receipt ... --out ...`只导出并审查真实收据，不创建新的运行事实。便携收据按内容摘要去重保存原始观察和原命令字节，每次按181个原始用例重新计算完整比较/几何/确定性；较大的差异视图只保存canonical摘要以避免重复存储，不能用该摘要跳过重算。参考strict原差异保留。完整离线入口为`python scripts/check.py --out test-runs/E08-full-01`，当前有31步；`--with-reference`另含官方采集，共48步。仅完成记录变化时才使用严格metadata收尾，源码/测试/参考/配置变化仍需full。
