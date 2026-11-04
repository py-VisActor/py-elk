# 19 批执行 brief

用户最新要求已改为[先完成全部功能，再统一校验修复](../IMPLEMENTATION_FIRST.md)，覆盖下方旧逐包源审/差分安排。当前 A 全部中间59与工厂，B 全P1/P2，V 全P3/P4后继续其它11算法，Root公共API/worker/metadata/defaults/typedJSON/包接线。只做syntax/import/接口检查；不采原、不运行布局、不差分、不等待逐模块独审；新代码未验证。所有功能实装并接线后才统一验证与修复。

以下为本批开始时的历史细分任务，后续以最新完整工作流为准，不据旧门禁中断实现。

按机器计划定位 18 批不可变 checkpoint，先核其纯绑定脚本和限定 code receipts。已有完整 caller 不重跑作为启动检查，所有新的原版输入采一次，观察器问题优先用保存数据复核。

| owner | 单写范围 | 本批交付 |
| --- | --- | --- |
| A | factories/provider 与剩余中间处理器 | 保持已验路由、分层、环消除、放置及标签调用；推进 comments 等真实完整链，并为新已审策略接一个新的 selected caller |
| B | Coffman–Graham / 后续 P2/P4 策略 | 先批准完整来源，再实现真实 comparator、transitive reduction、队列与 driver；整数 identity、逆迭代异常行为及优先队列 tie 按实际 source，不照教科书修复 |
| Root | 其它 P1、共享默认值、源/码审与归档 | 实现其它真实 cycle 策略；核实际 InternalProperties 默认桥及 SPLINES logging=true 已知失败路径，使用保存原版及受影响对象；分担 A/B 阻点独审 |
| V | 独立审查与新对象/消费者 | 优先审即将被真实调用的 body，再审最小工厂增量和保存结果；不重复 Root 已承接的源审，不因其它算法家族未完成而阻塞单个完整交付 |

Source/helper 边界仍按 [18 批校验入口](LABELS_PHASE_STRATEGIES_VALIDATION.md)和并行规范：共享文件单 owner，接口先定、源批先于数学实现、独审后接消费者。不得用 no-op、bbox、固定输入答案或假集合补数学。原始差异、首次失败、执行 SHA、实际调用数和未完成范围要明确区分。

已知单列：旧 external 身份顺序 23 项，SPLINES logging=true Source 日志收集 NPE，raw cycle 跨运行时异常类/文本边界，所有未实现策略及公开 API/发行整合。完整算法仍须按原分母验收，全部功能后统一全量，不自行提交、推送或发布。
