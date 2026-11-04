# 18 批复盘

本批从多个孤立阶段推进到真实调用：Polyline 完整 JSON、LongestPath 两种完整分层选择，以及 DepthFirst 和 Simple 的完整路径依次通过。每个新阶段先做源审、独立代码审和新 prepared 对象，再接真实工厂及完整调用，不用旧小切片的入口替代通用算法。

Root 分担 B 的 Polyline、LongestPath 和 Simple 源码及代码审，B 反过来为 Root 的 DepthFirst 定义原版控制、审查代码与保存结果；A 单写 factories/provider 和标签产品，V 专注标签对象与新调用差分。此交叉分工减少同一个 reviewer 的串行等待，同时维持实现与独审分离。阶段本体接受后立即交 A 接入，不等待整个阶段家族的全部实现。

新 DepthFirst 控制由 B 在未读实现前定义，覆盖 source 优先、非连通、自环、平行边、collector 创建与复用、真实标签及折点克隆，首候选即严格一致。Restorer 新写通用薄调用者，复用这次独审的通用反转数学；旧 cycles 有限输入检查及旧证据保留，避免在原模块中悄悄删 guard。

标签 Source 准备和观察器有两次具体纠正：V 的 Inserter/Remover 原准备误用 indexed setLayer 签名，修正 Source 后只用首候选保存结果重核，保留原 32 项差异；Root 的 EndPre 厚度 primitive 观察误取 `.value_0`，仅重采两个受影响 Source 对象，非厚度数据完全一致，候选仍只运行一次。以后先复用已验证构造器、setter 和数值 unbox 接口，减少准备错误。

独审还发现 Selector 的 ceil(-0.2) 应为 -0。仅新增这个原版单叶及旧码负控制、修后正控制；已有六模式通过结果保留原源码 SHA，不重跑。Switcher 首 HAS 物理 null 则使用属性自身 MEDIAN_LAYER 默认，并立即停止扫描；最初错误说明单独由 Source02 覆盖，原提案与审查字节不改。

EndPre/Post 的新两方向对象真正生成 LabelCell、执行重叠与原位 margin union，再按显式给定 node.pos 写回。该执行为原约 0.129 秒、首候选 0.369 秒；DepthFirst 原 0.121、首候选 0.381 秒；这些范围不同，不能合成整体提速倍数。纯保存数据和源码审查均不启动产品，未重复旧默认或平台矩阵。

下一批继续剩余 Layered 策略和其它中间处理器。B 推进 Coffman–Graham 的 boxedInteger、特殊 reverse-iterator、优先队列及 transitive reduction；Root 补 P1 其它策略，并处理实际属性默认桥和已知日志失败路径；A 推进 comments 等真实调用链；V 继续独审和新消费者验证。开发维持变更校验，全部功能后才全量；未将私有阶段通过提升为完整算法或正式发行。
