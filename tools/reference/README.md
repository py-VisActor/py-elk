# 官方 elkjs 参考工具

Node 仅用于研发，不是布局运行时依赖。已实现元数据和真实 graph/错误/副作用采集。
命令、协议、容差与适用条件见 [布局校验手册](../../docs/LAYOUT_VALIDATION.md)。

```shell
python scripts/upstream.py fetch
python scripts/validate_layout.py reference --out test-runs/oracle-01 --repeat 3
python scripts/validate_layout.py selftest --reference test-runs/oracle-01 --out test-runs/controls-01
python scripts/validate_layout.py replay --reference references/layout --candidate test-runs/oracle-01 --out test-runs/replay-01.json
```

[capture_layout.cjs](capture_layout.cjs) 每例独立进程/实例，校验全部发行文件 SHA；保存 graph、构造/调用参数的副作用和 result/error/terminate 观察。
单例格式为 `node tools/reference/capture_layout.cjs PACKAGE REQUEST NEW_OUTPUT`；批处理使用 Python 入口以保留日志/环境/分母。

元数据单独采集：

```shell
node tools/reference/capture_metadata.cjs .local/npm-elkjs/package test-runs/new-metadata
```

输出目录必须不存在。工具核对锁定包/入口 SHA，保存原始算法、选项、类别 JSON 和环境/哈希。
不得把元数据快照装入 Python 可用注册表。该命令使用 bundled 入口默认注册，graph 布局由另一个命令采集。

真实观察：该发行物 bundled 模式的 `terminateWorker()` 抛出
`TypeError: this.worker.terminate is not a function`。采集器把这一明确的已知结果记录为
`contractObservations.outcome = throws`，不把它标为生命周期通过；其他异常直接失败。
首次采集的原始失败也保留于本轮 test-runs。M1 须分别冻结 FakeWorker/真实 Worker/重复关闭/关闭后调用语义。

graph oracle 每个 case 使用独立 Node 进程，保存 constructor/args/输入/原始输出、
错误、状态副作用和 Node/包/资源 SHA，隔离模块级 registry 状态。
比较器分 exact、既定坐标容差、semantic-only；未知字段、数组顺序、section/container 坐标均保留。
图字段、端点、section 折点、选项默认值、随机流和错误类型的破坏负控制必须能被检出。
