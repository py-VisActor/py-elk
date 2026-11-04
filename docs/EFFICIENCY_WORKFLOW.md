# 开发、验收与提速操作规范

用户最新规则：持续goal完成剩余E09–E21迁移；[变更校验政策](VALIDATION_POLICY.md) 优先。开发只运行变更相关校验，全部功能完成后再统一全量；下文旧逐轮full要求不再作为当前收口前置。

适用E08及后续批次；首次实施和实际收益见[E08-00执行安排](iterations/E08-00.md)与[批次记录](changes/20261103-E08-00.json)。完整默认验收、来源/许可、原始比较、几何与确定性门禁继续保留。

## 1. 先预检，再并行写入

root保存完整起点文件指纹，冻结接口与单文件owner。准备时检查api/layered/conformance目录的unsupported与assertRaises清单，逐项判定保留、历史策略或迁为已实现能力的正控；文本清单本身不代表支持。

```shell
python scripts/preflight.py --baseline test-runs/<本批次>/starting-snapshot.json --out test-runs/preflight-01
python scripts/preflight.py --baseline test-runs/<本批次>/starting-snapshot.json --inventory-only --out test-runs/inventory-01
```

第一条真实执行最小API及E07布局对照；第二条仅生成清单，状态为INVENTORY_ONLY，不声称冒烟通过。迁移判定和证据由本轮root记录，不能因all([])给空执行颁发通过状态。E07旧DOWN误拒可被API冒烟提前发现。

A/B稳定的模块立即交接，root尽早接公共入口；V并行准备官方事实与反例。交接只报告变化、目标错误、阻塞、代码SHA及原始收据；实现结束的lane可明确转交新文件后审工具/文档，原owner文件继续冻结。

若改变线程/进程执行边界，还需先检查全部`patch`/`patch.dict`/mock及回调观察仪器实际在哪个进程生效。父进程补丁不会自动进入spawn worker；算法故障注入和禁外部engine守卫必须在真正kernel进程内执行，明确kernel-only仪器不能冒充公开API正本。先跑完整受影响conformance组，再开始三端full；E08首次完整检查曾因此发现4个失效负控，迁移后保留全部原断言并新增真实child守卫反例。

所有SHA绑定的版本化原始记录在首采时核Git过滤后的字节。含CRLF的既有记录应按`.gitattributes`保留原字节；不得为适应checkout擅自重绑原SHA。用小型真实Git stage/export先验证，再跑全新副本，避免到最终full才发现规范化差异。

## 2. 开发阶段按变更选择

```shell
python scripts/check.py --affected --changed tests/api/test_e04_api.py --out test-runs/affected-01
python scripts/check.py --affected --baseline test-runs/<本批次>/starting-snapshot.json --out test-runs/affected-02
```

已知依赖选择相关测试组，单一测试文件使用owner的`-p`模式。共享helper选择整组；未知脚本、配置、源码许可或来源ADR变化退回全量。模型变化覆盖layered直接依赖。源码/测试新增与删除都检查，夹具内部名为build/dist/test-runs的真实输入不被忽略。

affected报告明确标注非最终验收；即使未知变更退回跑完整集合，也不能以affected标签冒充最终full。完整入口保持：

```shell
python scripts/check.py --out test-runs/full-01
python scripts/check.py --with-reference --out test-runs/full-reference-01
```

证据目录放当前checkout的test-runs下或checkout外，避免将生成日志误作被测输入。full记录完整输入指纹及执行前后变化，任何owner写入漂移使本轮失败。

## 3. 缩短审计，保留负控

审计夹具从真实验证依赖构建副本，保留所需源/许可/案例请求、声明、历史包、元数据及负控可能引用的有效目标。oracle原始进程日志未被该审计读取时不反复复制。新增依赖先由正本检验；变异之后仍必须命中目标错误，不以别的缺文件伪造拒绝。

来源读取只在一个只读check作用域内复用raw、解析后的JSON、指纹及固定文本索引。独立check必须重新读当前字节；嵌套来源检查可复用本次数据。退出时复核文件和严格JSON类型/内容，异常清理context；普通load仍返回自身可修改数据。mtime、文件大小、已通过状态均不能作为跨调用命中依据。假symbol/错UTF16/tuple替换/非字符串key/内存污染与并发隔离都有独立负控。

## 4. 同一候选合并重复执行

```shell
python scripts/plan_suite_execution.py plan --out test-runs/suite-plan.json
python scripts/plan_suite_execution.py run --candidate-python .local/e07-candidate/Scripts/python.exe --wheel test-runs/<实际构建>/dist/py_elk-0.0.1a0-py3-none-any.whl --repeat 3 --jobs 2 --out test-runs/suites-reused
python scripts/plan_suite_execution.py verify test-runs/suites-reused
```

Linux换成实际bin/python路径。当前四suite仍为21/36/52/72共181个用例，149份不同原始请求。只在同一新run、同一执行身份内复用；3次独立重复必须真实启动，不把一次运行复制成三次。key绑定请求字节、角色、包/wheel、解释器/Node、适配器及依赖、配置环境和重复索引。候选先以-I/空PATH核全部包与METADATA，README/pyproject变化也使旧身份失效。

每个真实进程保存原请求/argv/cwd/log/exit/观察，多个case以来源对象引用，不伪造旧capture index或旧export协议。每套件自己的公开比较、geometry、输入保留与determinism仍独立执行。失败、未知身份或缺证明不能复用。原12/243/8/25及各套件分母保持。

执行复用与只读收据复验分开：run内key绑定实际完整子进程环境摘要，启动前后核真实环境；后来新进程的verify核记录中的环境证明、角色清洁策略、context和原始命令/对象，不要求后来进程的瞬态变量与旧进程相同。这不能用于新环境下复用旧执行。初版因此误拒正常历史收据的问题及修复前测量保留，最终计时采用修复后的新run。

## 5. 完成记录的专项收尾

三平台完整验收后，若仅更新批准范围内的完成记录、brief、复盘或进度状态，可执行：

```shell
python scripts/validate_completion_state.py --report test-runs/full-01/report.json --out test-runs/completion-01.json
```

它要求新的真实full报告、当前完整31或48条命令的正确argv/完整discover范围、原始日志/command.json一致；绑定当前解释器/平台及相关环境摘要，复核全部输入。E08增加独立API合同及当前包审计，with-reference另增真实API重采；E08-00历史29/45条记录保留，不能认证新增代码。源码、测试、reference、包/README、验证器、配置或未知输入变化必须重新全量。门禁定义/依赖不是可自由修改的完成字段；完成记录不得新增全算法/发布声明。正常metadata与进度证据校验仍执行；该工具不声称重跑布局或认证历史执行。

## 6. 衡量实际提升

```shell
python scripts/benchmark_checks.py --baseline test-runs/<本批次>/baseline-source --out test-runs/check-benchmark-01
```

同机同解释器，在无其他重负载的屏障内顺序运行原版与改造版完整入口，核旧方法保留、实际测试数、每步与wall time。新增守卫单列。原E07的323秒仅作历史参考，不替代本次前后对照。

请求去重使用同jobs配置，分别加`--no-reuse`和默认复用做两个真实run；1086→894是进程次数节省，不能冒称wall time也必然减少17.7%。缓存首败、错误预检及性能回退都保留，最终记录公布实测、局限和下一批改进。
