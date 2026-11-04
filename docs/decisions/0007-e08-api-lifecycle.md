# ADR0007：受限公开API与Python执行生命周期

状态：accepted-for-implementation，E08-01，2026-11-03。本文冻结接口与宿主设计，不代表运行验收完成。行为基线仍为elkjs 0.12.1；E07的33组件来源批准和8原始节点/28边域不变。机器合同见[host contract](../../references/e08-host-contract.json)。

## 官方事实与宿主决定

`elk-api.js`的构造注册、递增消息ID/resolver、三个Promise查询与layout参数由固定发行文件解释。独立Node探针保留在`test-runs/20261103-E08-01/V`，会由版本化采集器重采。官方空算法列表仍注册fixed/box/random；模块静态registry跨实例累计。默认12/243/8、空列表3/94/8、仅layered 4/183/8不能当作Python能力。

Python实例隔离注册，默认只注册受限layered。`algorithms=[]`构造仅查询实例：算法/类别为空，九项已实现解析选项仍可查询；布局明确拒绝。短`layered`与规范ID规范为同一实际注册，重复去重；未知ID与已知未实现分别报错。九项解析能力与实际布局边界分别描述；算法描述不宣称端口、标签或层级支持。查询每次返回独立数据。

Python `None`作为省略构造/调用参数的宿主便利保留；其他容器要求mapping。JS非法值的宽松接受、异步worker未捕获错误和Python明确验证分别记录。显式`workerUrl`/`workerFactory`不调用用户函数，抛同时属于`UnsupportedFeatureError`及`NotImplementedError`的异常。官方FakeWorker重复terminate会抛TypeError且未关闭；Python真实幂等关闭是有意的宿主设计。

日志/计时参数省略或false保持E07路径；true仍显式unsupported，不借本轮API验收扩展算法处理器或日志树。完整日志/计时分支归E09声明收口，原始合同及分母保留。

## 冻结公开接口

`ELK(options=None, *, max_pending=16, timeout=None)`；`async layout(graph,args=None)`；三个async元数据查询；同步`terminateWorker()`；独立拷贝的`last_trace`。额外两个keyword是Python宿主扩展：max_pending必须是1–64的整数（排除bool），含running与queued；timeout为有限正数秒或None，覆盖排队、启动及执行，到期任务失败并回收。没有默认硬CPU或内存上限承诺。

沿用ValidationError(code,path,message)及其原分类。新增UnknownAlgorithmError、UnsupportedAlgorithmError和UnsupportedWorkerError。ResourceClosedError保留UnsupportedFeatureError/ValidationError兼容和RESOURCE_CLOSED代码。ExecutionError(RuntimeError)使用同样结构字段；QueueFullError、ExecutionTimeoutError（同时TimeoutError）、WorkerExecutionError分别处理容量、总期限和内部启动/进程/协议故障。取消保留asyncio.CancelledError；不把内部bug改成用户unsupported。

## 调度与状态

实例new→open→closing→closed。每实例一个真正spawn子进程工作槽，FIFO队列，任务queued→running→returned/failed/cancelled。短生命周期调度线程负责spawn/IPC/reap，空闲自动退出；事件循环只处理Future/通知。新任务只携带安全JSON快照，worker执行原create_context→validate_slice→layout_context，算法/context/options文件只读。

ExecutionController(constructor, *, max_pending=16, timeout=None).execute(graph,args=None)返回ExecutionResult(graph,trace,job_id)，close()同步幂等，snapshot()返回独立诊断。A只传规范化构造参数，不把Python调度选项带进E07 scope。消息绑定job_id，kind为progress/result/error；错误只按冻结白名单还原，未知或不完整消息为协议错误。结果、trace和错误字段必须验证，不接受任意远端类实例。

无pending/running时可在另一事件循环复用实例，保留既有多次asyncio.run调用；有活动任务时跨loop明确EVENT_LOOP_CONFLICT，不隐含多线程并发提交承诺。线程与进程身份、队列和回收状态作为开发诊断，不进入ELK JSON。

## 取消、关闭与结果竞争

queued取消或到期任务不得启动。running取消/超时先terminate，必要时kill，join并关闭连接/进程句柄，回收调度槽后才向调用方完成取消/超时。重复取消不能绕过cleanup。关闭先拒绝新工作，再取消queued、停止并回收running任务/调度线程，最后closed。已完成且发布的结果优先；取消/关闭先获状态权时不发布旧结果。

last_trace在有效layout调用进入时清空，只发布最后有效提交job的成功trace；失败/取消/关闭后保持空，旧任务不能覆盖新请求。输入、构造、args与返回值无共享可变状态；每worker新建context/RNG。

## 验收与来源

A核API/注册/元数据固定源与已有九项schema；B明确进程/线程/超时/容量为原创新宿主实现；V独立审事实、返回隔离、错误分类与真实生命周期。来源文件含固定文件SHA、实际callee/guard/范围及许可；独立复审闭合后才更新能力状态。

真实CPU阶段可用仅观察的trace-list append记录progress，保持原trace与处理器顺序，不加入算法取消检查点。实际running取消须有真实phase事件、活PID、未返回结果、取消后PID/线程回收及后续成功；屏障测试只证明竞争次序，不代替真实计算。心跳、双实例重叠、排队取消、超时/崩溃恢复与同实例FIFO分别实测。

root先封存E07 wheel/声明/README/METADATA并将其审计明确切为historical；旧包不执行。当前E08必须新建同一wheel，以-I/空PATH运行API/生命周期和21/36/52/72同包布局回归。原profile/几何容差/原始请求不改，三平台full及最终完成元数据门禁保留；正式发行、完整算法与py-mermaid集成状态不提前提升。
