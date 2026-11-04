# 11 批复盘

本批接通实际递归协调器，完成 pool/deprecated、owned traversal、inside-loop 和 7 个递归 helper 的独立审查。新增普通递归 2 例、Topdown 1 例、DisCo→Fixed 共享池 1 例严格差异为 0；本地属性导入 14 DTO 严格投影一致，原始异常差异单独保留。完整 Layered、公开 API 和独立正式包仍未完成，完整算法验收数保持 0。

并行效果来自任务重分配：B 完成 RectPacking 后先交 helper/inside-loop，再补阻断 Topdown 的本地导入；Root 实现主调度并审核 B 的短闭包；A 持续推进 Layered crossing/动态流水线；V 负责独立来源、代码与真实原版对象。普通递归、Topdown、共享池候选分别只需约 0.12–0.19 秒，未重跑旧算法组或全平台套件。

发现并修正三类问题：源导入器会忽略无效 padding，严格 API 解析器不能直接作为其实现；原版 probe 的注册算法集必须与 native catalogue 分母一致，否则后缀歧义会形成错误 oracle；判断 individualSpacings 存在性需要真实对象类型，不能只检查原始键存在。比较器也从泛删 `$H` 改为只过滤真实图元素上的生成标记，并用保存数据与负控制重核，未重跑布局。

工具问题均保留首次失败。Root 两次审核脚本分别漏算 span 末尾 LF、猜错 request 文件名，修正后用新目录执行；后续从实际 command/handoff 读取路径，源码片段同时核 base64 和摘要。B 的首次 comparer 未即时存副本，旧字节仅作后验恢复并明确标注；后续每次执行立即存 `checker-executed.py`。

下一批将 B 转入通用 Network Simplex，减少完整 Layered 依赖由 A 串行承担。A/B 的明确文件与接口边界见 [12 批 brief](../iterations/NEXT_NATIVE_12.md)。本批没有建立同分母的整体提速比例，不能把单次校验耗时当作项目整体速度提升。
