# 完整候选性能与质量观察

以下结果针对修复前的版本差异候选 `0.1.0` wheel（SHA 见下文），在仓库外以 `-I` 安装后实测，未使用旧 E10 wheel 的性能结果。后续 MrTree 活动路径修复的实际检查单列于 [发行说明](releases/0.1.0.md)，没有把本次性能测量改绑到修复候选。
实际 12 算法 × 8／32／96 节点，另测 Force Eades 三个规模，共 39 配置；每配置独立 worker、1 次预热与 5 次同 worker 正式采样。另有 Force／Stress 在迭代上限 1、25、150 下的 6 个质量观察，共 240 次真实布局。

测量入口：

```shell
python scripts/validate_full_performance.py --plan-only
python scripts/validate_full_performance.py --wheel PATH_TO_WHEEL --out NEW_DIRECTORY
python -m unittest discover -s tests/platform -p test_full_performance.py -v
```

纯计划模式不导入产品、不运行布局。实际模式离线安装指定 wheel，核完整安装文件与原 wheel 字节，记录所有预热、正式 wall 时间、OS 工作进程 CPU／working set／peak working set、worker PID 复用和输入保留。

本次环境：Windows-11-10.0.26200-SP0；CPython 3.13.15。wheel SHA：`0e7c089b37728d6a0a10374c9df488f48bb5b96c12d92c04d8b761618fabc9d9`。

下表为 96 节点正式样本中位 wall 秒数，峰值含该配置启动及预热的工作进程 high-water，不含调用方／观察器进程。

| 算法／模型 | 中位秒 | 工作进程峰值 MiB |
| --- | ---: | ---: |
| fixed | 0.0075 | 29.71 |
| box | 0.0076 | 29.68 |
| random | 0.0072 | 29.70 |
| layered | 0.0665 | 42.50 |
| mrtree | 0.0431 | 34.72 |
| radial | 0.0630 | 33.05 |
| force | 11.1942 | 32.54 |
| stress | 11.2150 | 32.57 |
| disco | 0.4553 | 34.30 |
| sporeOverlap | 4.0785 | 35.11 |
| sporeCompaction | 3.1163 | 32.50 |
| rectpacking | 0.0330 | 31.76 |
| force / EADES | 9.8550 | 32.75 |

这些是已测规模和设置的观察值，不是任意图的延迟或内存保证。96 节点 Force／Stress 默认配置约 11.2 秒，不能沿用旧 0–8 节点范围的 6 秒目标作为更大图承诺。

质量观察独立报告节点矩形重叠数量、边长和归一化图距离应力：连接节点对目标距离为最短边数 × 100，应力为距离残差平方和除以目标距离平方和。它不是每种算法各自的优化目标，不据此要求 Force 单调收敛；Stress 三个上限下本例应力为约 0.1460／0.03586／0.03501。
fixed 使用给定位置；DisCo 使用多个初始连通分量；Spore 输入有真实重叠。Random 可产生重叠，DisCo 保留分量内部形状，SporeCompaction 本身不是重叠移除，Radial 默认设置也不保证所有矩形无重叠，不能把这些观察错误写成算法失败或全部无重叠通过。

原始逐样本数据：`test-runs/full-native-closure/performance-01/installed/report.json`；[完整摘要](changes/20261104-full-performance.json)绑定其 SHA。原始退出码、安装命令及 stdout/stderr 位于同级目录。
此次只有该 Windows 主机的性能／峰值观察；已有 Windows/Linux × 3.11–3.14 功能矩阵继续保留其实际版本与安装范围，没有由本表外推平台性能。

## 已发布修复版本的 MrTree 变更测量

针对实际 PyPI wheel `93c9f75e…`，仅重测受活动路径修复影响的 MrTree 8／32／96 节点，3 次预热、15 个正式样本，未执行其他算法或 Force／Stress 迭代组。每配置五次正式结果 SHA 一致，进程复用和输入保留检查均通过。它不把上方旧候选其他配置重标为新测量。

| 节点数 | 中位 wall 秒 | 工作进程峰值 MiB |
| --- | --- | --- |
| 8 | 0.003374 | 30.28 |
| 32 | 0.011668 | 31.62 |
| 96 | 0.040592 | 34.41 |

原始报告见 [MrTree 变更性能](changes/20261104-published-mrtree-performance.json)。其余 36 配置的数学模块及运行字节未因该修复改变，继续保留原测量身份，不重跑、不宣称相同主机测量的提升比例。

```shell
python scripts/validate_full_performance.py --algorithm mrtree --wheel PUBLISHED_WHEEL --out NEW_DIRECTORY
```
