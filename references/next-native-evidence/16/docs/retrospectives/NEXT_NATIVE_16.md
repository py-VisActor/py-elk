# 16 批复盘

层级导入、compound pre/post/models/dummy、hierarchy driver 的限定代码审查推进完成；层级尺寸调整四个真实对象严格一致。Spline foundation 与排序各完成独立审查，后续 producer/driver 和 Final 继续独立交付。Root 新增矩形凸包及南北正交策略，复用已验大数学，避免修改和重跑无关方向。

Root 分担 A 的 compound post、hierarchy resize、B 的 Spline driver 源审和层级尺寸原对象检查；V 保持 code 独审，审查队列的实际依赖先于归档。A 发现 hierarchy 路由需要真实 dir1/2，Root 优先补这个阻点，再继续 connected compactor。后续仍按共享文件单 owner，临时调度调整及时通知。

矩形凸包首次六例值一致，但 V 发现内部调用顺序与源不同：应四次 maximal sweep 后再按 Q1/Q2/Q3/Q4 加凹角。Root 拆开辅助函数，仅新增受影响空输入顺序控制；旧码负控制失败、修复后通过，旧六例不重跑、不重绑新 SHA。后续应在首次实现时同时核数学结果和实际调用顺序，减少事后补叶。

CT 源审还纠正一个尚未进入实现的容器假设：placeholder 的 Pair 值采用字段组合 hash，不能给 Pair 申请身份 hash。原提案保留，更正放进审查记录，避免为了“native 重写”随意改动可观察的集合遍历行为。数学和容器协议分别审，不能由一个样例的结果倒推完整正确性。

新增校验均限新对象和变化调用，原版每份输入采一次。层级尺寸首次四组原/候选约 0.128/0.314 秒，南北轴约 0.133/0.261 秒；这些是单命令实测，未建立整体速度比较，不宣称新的倍数。纯绑定检查留给新会话，不默认再跑产品。

用户明确完全独立重写文件使用 MIT，已补进发行决定。实际仍有逐函数移植代码，逐文件按来源分类，不一概改写许可头，也不因来源核对中断其它迁移工作。

下一批先补齐实际 hierarchy handlers 并接真实 compound consumer，继续 Spline producer/driver/Final，再实现已审的 component transformer/controller 与 connected compactor。完整算法和 public 包的验收仍待；继续变更校验，全部功能后再全量。
