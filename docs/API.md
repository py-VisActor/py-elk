# API 索引

面向使用已安装 `py-visactor-elk` 的应用。完整图示例见 [用户指南](USAGE.md)。
导入：`from pyelk import ELK`。

## ELK

```text
ELK(options=None, *, max_pending=16, timeout=None)
```

| 参数 | 作用 |
| --- | --- |
| `options` | 可选映射；包含 `defaultLayoutOptions` 与 `algorithms` |
| `defaultLayoutOptions` | 构造默认布局选项映射 |
| `algorithms` | 可选 provider 名称列表；影响该实例的注册范围与查询结果 |
| `max_pending` | 运行中加排队任务上限；整数1–64，默认16，bool不作整数接受 |
| `timeout` | 有限正数秒或 `None`；包含提交、排队、worker启动与执行 |

不支持 JavaScript 的 `workerUrl`/`workerFactory`。实例管理的是原生 Python worker。
provider 选择及其 core 注册行为与简单“算法白名单”不同，使用查询方法确认实例目录。

## 异步方法

| 方法 | 返回/行为 |
| --- | --- |
| `await elk.layout(graph, args=None)` | 布局后的独立图映射；失败抛异常，不返回伪造坐标 |
| `await elk.knownLayoutAlgorithms()` | 当前实例已注册算法的描述列表 |
| `await elk.knownLayoutOptions()` | 当前实例的选项声明列表 |
| `await elk.knownLayoutCategories()` | 当前实例对应类别描述列表 |

`layout` 的 `args` 可包含 `layoutOptions`、`logging` 和 `measureExecutionTime`。
后两者只接受 bool，默认 false。开启后会记录实际执行监视树；输出中根 `logging` 是保留字段。
计时沿用固定 elkjs 的生成标尺，不应直接解释为 CPU 时间或常规秒；仅需要诊断时再看
[计时规则](decisions/0008-e09-diagnostics-coverage.md)。

## 关闭与上下文

`elk.close()` 与 `elk.terminateWorker()` 同步、幂等地关闭并回收工作资源。
支持普通和异步上下文管理器；关闭后不再接受布局或元数据查询。
取消/超时会回收对应执行资源；不要将实例当作无限队列或硬内存配额机制。

`elk.last_trace` 是独立的开发诊断快照，不是返回 ELK JSON 的一部分，也不替代结果校验。

## 异常

下列类型均可从 `pyelk` 导入；异常有 `code`、JSON Pointer `path`、`message`。

| 类别 | 常用类型 |
| --- | --- |
| 输入/模型/选项 | `ValidationError`、`ModelValidationError`、`OptionValidationError` |
| 未知或不适用能力 | `UnknownOptionError`、`UnsupportedOptionError`、`UnsupportedFeatureError`、`UnknownAlgorithmError`、`UnsupportedAlgorithmError`、`UnsupportedWorkerError` |
| 生命周期 | `ResourceClosedError` |
| 执行 | `ExecutionError`、`QueueFullError`、`ExecutionTimeoutError`、`WorkerExecutionError` |

Python `asyncio` 取消仍按其取消语义传播。异常名称和固定源的 JavaScript 异常不保证逐字相同，
原始差异与具体适用范围见 [兼容说明](../API_COMPATIBILITY.md)。

## 进一步阅读

- [用户文档目录](README.md)
- [兼容合同及有限验证边界](../API_COMPATIBILITY.md)
- [维护者/agent入口](development/README.md)：源码、来源与旧阶段资料目录
