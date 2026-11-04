# E10 平台与性能验证

本轮仅增加安装、宿主生命周期和性能专项，复用 E09 产品，不执行项目全量或旧 181/144 矩阵重采。实际进度与完成状态见 iteration-plan.json、RELEASE_STATUS 和本轮变更记录；本页命令是操作说明，不代表尚未完成的检查已通过。

## 离线重核已保存的原始观察

在仓库根目录使用 CPython 3.11+，无需安装 pyelk、Node 或其他依赖。每次换新的输出文件名：

```shell
python scripts/iteration/e10_runtime.py --out test-runs/e10-batch-recheck-01.json
python scripts/iteration/e10.py references/e10-platform-matrix.json --matrix --out test-runs/e10-matrix-recheck-01.json
python scripts/iteration/e10.py references/e10/windows-3.13-sdist.json --out test-runs/e10-windows-sdist-recheck-01.json
python scripts/iteration/e10.py references/e10/linux-3.14-sdist.json --out test-runs/e10-linux-sdist-recheck-01.json
```

首条为本批统一纯重算，检查平台、源码安装代表、性能与六份独审；也可只运行受本次修改影响的下面单项。性能与插桩的独立入口：

```shell
python scripts/iteration/e10_benchmark.py references/e10-benchmark.json --out test-runs/e10-performance-recheck-01.json
python scripts/iteration/e10_instrument.py references/e10-instrumented.json --public references/e10-benchmark.json --out test-runs/e10-cost-recheck-01.json
```

本轮实际14项针对性测试、八个wheel格及两个sdist代表格通过；三档公共调用中位约76/83/236ms，仅为本机Linux3.14。精确原值及来源在 references/e10-runtime-audit.json，不将该数字外推到其他机器或图规模。

矩阵固定八格：Windows/Linux × CPython 3.11/3.12/3.13/3.14。每格六个原始请求，包含四个布局正例与两个错误；另核真实异步元数据、关闭后错误、观察到运行进度与活 PID 后的取消/回收，以及随后一次链图恢复。索引引用原 cell 字节，cell 内保留原始 observation、请求、命令及日志字节；检查器重新比较实际几何和原始官方结果，不读取旧 PASS 作为结论。

sdist 本轮仅实测 Windows 3.13.15 和 Linux 3.14.10，其他六个 sdist 版本格未测。Windows 直接离线安装源码归档；Linux 在独立构建环境由同一源码归档生成 wheel，再装入另一新环境，构建 wheel 的 SHA 单独保存。八格 wheel 使用同一原始 wheel；Linux 的 sdist 构建 wheel 与它的 ZIP 字节不同，运行文件与 METADATA 另核一致，不将两个 SHA 混作同一发行物。

## 需要新实际执行时

采集入口为 tools/platform/capture_e10.py；Windows runner 为 tools/platform/windows_e10.py，Linux runner 为 tools/platform/linux_e10.py。用各自 `--help` 查看参数；Windows runner 自动创建仓库外新 venv，Linux runner 应在仓库外目录执行其 run 子命令。固定输入在 tests/fixtures/suites/E10/cases.json，不能临时减分母或以 queued 取消代替 running 取消。

Windows 单格示意（替换解释器、wheel 与新输出目录）：

```shell
python tools/platform/windows_e10.py --python C:/tools/python311/python.exe --minor 3.11 --wheel C:/artifacts/py_elk-0.0.1a0-py3-none-any.whl --out test-runs/e10-win311-new
```

实际 child 以 `-I`、空 PATH、无 Python/Node override 环境运行；完整模块/许可/METADATA 身份由已安装包与 wheel 核对，不能导入 src 目录替代。sdist 使用固定离线 setuptools/wheel/packaging 构建依赖，下载与版本来源单独记录。

采集器只记录其真实执行闭包：自身、wheel 身份 helper、六份请求与 suite、取消原请求，共十项；开始前读取并在结束后核不变。纯检查器 SHA 写在新的核验报告中，修改纯检查器只重核旧 raw，不改旧执行 SHA。公共采集器变化则只重采受影响格。

## 性能方法

tools/platform/benchmark_e10.py 在 Linux 对三档固定输入顺序采样：3 节点/2 边、4 节点/4 边、8 节点/28 边；每档一次预热、五个正式样本。所有输入均在已支持域内，“大”只表示本域的相对规模。先等平台重负载结束，不能并行测吞吐后宣称单请求延迟。

每个样本使用新 driver，只等待一个真实布局 worker；公共调用 elapsed 使用 perf_counter_ns，CPU 与各进程峰值 RSS 来自真实 getrusage。Linux ru_maxrss 的 KiB 乘 1024 转字节，父/子峰值分别报告；不相加成同时树峰值，也不作减法得到增量。父峰值包括 driver 准备阶段；公共调用计时包含 spawn、IPC 与真实布局，构造及安装身份检查在计时前。仍存活且未被 wait 的 resource tracker 明确单列，不冒充 worker 资源。

ELK 返回的 executionTime 沿用上游特殊标尺，不能用作普通秒或 CPU 时间。可选的 phase/import/export 明细使用单独 instrument_e10.py 与独立样本，不混入公共调用的五次统计。未测量的指标明确标未测，不编造内存/CPU 硬配额、无界大图能力或整体提速比例。

平台与资源门禁只依据最终专项记录提升；最终全量仍留全部 E09–E21 迁移功能完成之后。
