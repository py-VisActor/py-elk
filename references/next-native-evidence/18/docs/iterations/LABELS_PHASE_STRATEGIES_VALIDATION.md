# 18 批标签与阶段策略校验

当前正式归档及源码检查点以机器计划 `parallelPreparation.progressRecord` 为准。开发中的新文件可以领先归档；恢复时不要覆盖仍在使用的 `.local/migration-next`。每个新完整 caller、prepared 对象和单叶负控制都绑定其执行时的源码 SHA，后续修复不能改写历史绑定。

本批完成真实 Polyline、两种 LongestPath、DepthFirst、SimpleNodePlacer，以及高级标签处理器。prepared 图验证真实阶段数学和可变引用；完整 JSON caller 验证注册、持久缓存、阶段选择、导入和导出。中间层、宽度或节点位置由测试提供的对象，不得描述为完整图布局。

新会话先运行归档中的纯绑定脚本：

```powershell
python references/next-native-evidence/18/progress-bindings/check_progress.py
```

这只核不可变源码、材料与限定审查，不执行产品。确有对应代码变化时，阶段比较器使用五个位置参数；下面的全大写名称是需要替换的参数：

```powershell
python tests/fixtures/suites/next-native/compare_polyline.py SOURCE REQUEST ORIGINAL OUTPUT PROBE
```

`SOURCE` 是冻结源码树的 `src`，其余依次是请求、原版观察、候选报告和实际原版 probe 文件。精确路径以对应 `command.json` 的 argv 为准；脚本会校验 request/probe/worker SHA。调用统一 runner 时先创建新的唯一输出目录，保留 `command.json`、执行脚本、stdout、stderr 和首份报告。不要覆盖旧目录，也不要默认重跑旧 Spacings、Cell、Overlap、NS、BK、自环、平台或默认阶段组。

标签需特别区分下列证据口径：

| 对象 | 新证据 | 不扩大的结论 |
| --- | --- | --- |
| Inserter/Remover | 实际插入、给定层及几何、真实移除，两方向及引用写回 | 中间几何由测试提供 |
| Selector | 六模式、真实 gather、物理 null 标记、独立 ceil 负零修复 | 不以六例声明所有长 dummy-run 分支都运行过 |
| Switcher | 六策略、物理 null 首 HAS、UP 宽度零及空间策略；真实 splitter 产链 | 层与宽度显式给定；首 HAS 后 GET 使用属性声明 MEDIAN_LAYER |
| EndPre/Post | 两方向非空真实 Cell 生成、五个 cardinal 端口、重叠、原位 margin/rect 和前后处理 | 中间 node.pos 显式给定；没有重跑旧 Cell/Overlap 数学组 |
| 管理回调 | 缺省成功；False/0/空串/空列表真实失败 | 编译版本的 null-only 行为，不是假实现任意 label manager |

EndPre 首原观察器错误地把 primitive Number 当作 `.value_0` 对象，导致厚度值字段省略。Source02 只改成真实 double unbox，两个受影响对象重采，其余全部值由保存数据严格核为一致；候选仅执行一次。保留 Source01，不把它称为厚度值证据。

LongestPath 使用显式 continuation frames 保持原 postorder，两个类各自持有共享配置。未经环消除的 raw 非自环循环在原版栈耗尽，候选主动抛 RecursionError：只核实际保留状态，不声称异常类、文本或时机等同。DepthFirst 的新通用反转保持 collector 创建/复用、标签翻转和旧折点引用，Restorer 每个当前 port 单独取 outgoing 快照，不先取全图边集合。

完整 JSON 原始新增形状 `$H` 差异继续保留，只使用已批准的显式形状投影；业务字段、节点顺序和坐标不随之归一化。旧 external 原始 23 项顺序差异和 SPLINES logging=true 原版故障继续单列。全部迁移功能完成后再统一全量，未授权时不提交、推送或发布。
