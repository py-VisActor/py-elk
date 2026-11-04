# E10 平台与测量接口

本轮只新增平台/性能/资源专项，复用E09未变的43文件wheel与sdist；不跑全项目full，不重采旧181/144矩阵。Windows/Linux × CPython3.11/3.12/3.13/3.14各一个实际cell，patch版本和发行来源如实记录。

## 文件归属

| owner | 独占路径 |
| --- | --- |
| root | 本文、tests/fixtures/suites/E10/**、平台artifact清单/全局进度与文档 |
| A | tools/platform/capture_e10.py、tools/platform/windows_e10.py、tests/platform/test_e10_capture.py |
| B | tools/platform/linux_e10.py、tools/platform/benchmark_e10.py、tests/platform/test_e10_benchmark.py |
| V | scripts/iteration/e10.py、tests/platform/test_e10_validation.py |

先交单cell小正本，源/包/参考请求不变时复用已经完成的实际数据。采集器执行依赖和纯校验器SHA分开；纯校验变化只重核原raw。不得改旧收据执行SHA。平台采集可并行，性能采集须在其它重负载结束后顺序执行。

## 平台collector

CLI：`CANDIDATE_PYTHON -I tools/platform/capture_e10.py --wheel WHEEL --suite SUITE_DIRECTORY --out NEW_JSON`。

runner在仓库外新venv无依赖安装同一wheel，child PATH为空，移除PYTHONPATH/PYTHONHOME/NODE_OPTIONS/NODE_PATH；记录原argv/cwd/环境策略、launcher PID、Popen PID、日志/exit和原observation字节。只在安装器阶段允许pip；实际布局只运行Python。

observation schema为 `py-elk-e10-platform-observation/v1`：

- `engine`：name=pyelk、version、python完整版本、versionInfo前3整数、executable及SHA、prefix/basePrefix、sys.flags.isolated、platform.system/release/machine、pid/parentPid、pathEmpty/overridesAbsent。
- `executionDependencies`：采集文件、scripts/verify_installed_wheel.py、suite定义与实际请求文件的原SHA；不绑定纯验证代码/可变进度文档。
- `installed`：原verify_installed_wheel.verify的完整结果。capture通过importlib加载这一既有helper，不把src加到sys.path。当前源码43file/README/METADATA的纯验证在V另做。
- `cases`：suite六个请求，逐项保留id、requestSha256、原request、input/constructor/arguments before/after、真实result/errorDetails、trace摘要、close后controller.snapshot。observation结构沿E09 layout observation原字段，error名称及code/path/message保留。测量的clock字段为整数startMs/endMs，只处理源生成monitor树的计时叶。
- `metadata`：三个真实async查询及close后layout/query错误；保留原返回，不只存计数。close后必须无pending/worker/dispatcher。
- `cancel`：复用E08 native-request中cpuGraph，观察实际running progress、活任务、PID，再取消/回收并用chain恢复。原before/after snapshot、cancelled异常类别、未完成前置条件、恢复结果/trace原样保存；不宣称硬CPU/内存配额。

若本机无法实际观察running取消，明确失败/未测，不凭queued取消冒充。每cell执行一次即可；没有代码变化不重复三次大矩阵。

## portable cell receipt 与纯验证

schema `py-elk-e10-platform-cell/v1`：`id`、`os`、`pythonMinor`、`wheel`/`wheelSha256`、`candidatePython`、`actualSourceRoot`、`launcherPid`、`command`、stdout/stderr原bytesBase64、`observationBytesBase64`/SHA。

V提供 `validate_cell(value, root=ROOT)` 返回passed/errors；`validate_matrix(cells, root=ROOT)` 必须检查恰8个不同OS/minor cell，不用一个版本代表另一格。原capture package/version/绝对且非源码模块路径与当前43file/METADATA核对，PID接受真实direct或Windows shim；参考结果取E09已保存的同request案例并重算比较/几何，不用saved PASS。

V仅为新协议补4类必要负控：错平台/版本、包/metadata变化、输入或几何变化、错误PID/缺cell；不重复E09已经通过的25整包变异。

## benchmark

与平台collector分开：三个固定bounded请求small/medium/large（均≤8 nodes/28 edges）。标准public调用每档1次warmup、5次样本；报告每次原始elapsed、父/子CPU、父/子峰值内存、机器/负载/clock及聚合分位数。Linux ru_maxrss以KiB记录，不将父子不同时间的peak相加冒充同时总peak。

需各phase/import/transfer明细时，用明确标注的单独instrumented native worker样本，在真实monitor begin/done及import/export边界加观测，保持原数学与消息协议；旁路文件记录高精度perf_counter_ns/process_time。只用于成本分解，不冒充未插桩public吞吐。源JSON executionTime仍保留原ms×1000×1e-9，不能当普通秒。

benchmark执行记录依赖collector/请求/wheel/解释器及环境，pure校验器的修改不让已经完成的无关平台计算自动失效。所有报告fullValidation=false，最终全量留E21功能完成后。
