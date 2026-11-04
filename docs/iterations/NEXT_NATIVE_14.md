# 14 批执行 brief

承接 [13 批](../changes/20261104-next-native-13.json)：146 文件检查点 `1c086f0651c288c3086144c24cca544adebbb35aa82cd707ba36bdc676b1c4d7`。全局 optsToCfg、通用组件拆分/SimpleRow 和尺寸收尾已按范围独审；公开入口、完整 Layered 和正式包仍未完成，完整算法验收仍为 0。

| owner | 单写范围 | 首要交付 |
| --- | --- | --- |
| Root | components_general/resize_general、execution/options/metadata、归档 | 先独审 B 744860 适配器保存证据；继续三种外部 component placer 与 connected compactor 的真实源码和实现，参与默认入口接线 |
| A | native import/export、constraints、long edges、Layered provider | 接已批主阶段、尺寸和组件 ABI；最早交实际完整默认路径新请求，尚缺的 handler 明确列出，不能走旧受限入口代替 |
| B | 固定 native_adapters 744860；新 self_loops_general.py | SL-holder/innermost 新见证已交 Root；转入完整 holder 和四个自环阶段，旧 loops.py 只读。先独审来源，和 A 的 sl_ports/incoming_sl_edges/outgoing_sl_edges/l_edge 接口一致 |
| V | 独立来源、代码与新原版对象 | 优先完整导入和长边/约束新实现，保留所有失败版本；Root 分担 adapter 审核，避免队列全压 V |

共享 identity hash 已由 A 将 graph.identity_hash 接到 Session 同一 bound method。组件克隆传播此引用、source session、同一 RANDOM 对象与 PROCESSORS 列表；Integer sidecar 和 typed 属性浅复制。完整调用仍需实测这些关系，单个 helper 证据不代替整调用。

组件当前只有通用 split 与 SimpleRow 通过；三个外部 placer、Compactor 选中时明确 pending。Root 逐个补实际数学，不把它们静默映射到默认打包。resize 的 cleanup 只在主流程正常完成后调用，取消或异常后的行为由实际 caller 控制。

13 批全局配置的 Insets/Integer 观察器错误均保留首次进程退出 1，只重采受影响原例并复核保存 native 数据。后续超长键和大整数是实际产品缺陷，各有单独新控制和新源码，不重跑八例或 Box。比较器更新只核保存结果，产品变更才执行受影响产品。全部功能完成之后再全量，继续不提交、推送或发布。
