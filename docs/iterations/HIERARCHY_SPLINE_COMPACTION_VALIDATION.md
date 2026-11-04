# 层级、Spline 与矩形凸包变更校验

16 批承接默认 19 阶段和自环 23 阶段，新增层级导入、compound 前后处理、层级尺寸调整、Spline 数据及排序、矩形凸包与正交南北轴。完整 compound 布局、Spline driver/Final 和 connected compactor 各按独立范围继续，不能因 helper 通过称全部完成。

新会话先运行当前归档的绑定检查，核源码对象、执行材料及审查范围，不启动产品：

```shell
python references/next-native-evidence/16/progress-bindings/check_progress.py
```

恢复工作区按 `docs/changes/20261104-next-native-16.json` 的 checkpoint.path，使用 `next_workspace.py restore --destination 新目录 --manifest 该路径`。工作区可领先快照；每份实际结果只对应它自己的 sourceFilesSha256，不给旧执行绑定新代码。

以下入口位于 `tests/fixtures/suites/next-native`，只在相关实现或真实 caller 改变时使用。`PRIVATE_SRC` 为冻结目录中的 `src`，`ORIGINAL` 为已经保存的原版 observation，`NEW_REPORT` 必须是新路径；不重采同一份原版。

| 新范围 | 脚本与参数 | 已保存材料 |
| --- | --- | --- |
| 层级尺寸调整 | `compare_hierarchy_resize.py PRIVATE_SRC hierarchy-resize-request.json ORIGINAL NEW_REPORT` | `HOST16/root/hierarchy-resize-original-01` 与 `hierarchy-resize-native-01`：4 组，strict 0 差异 |
| 矩形凸包 | `compare_recthull.py PRIVATE_SRC recthull-request.json ORIGINAL NEW_REPORT` | `recthull-original-01` 与 `recthull-native-01`：3 组几何、3 组退化失败阶段 |
| 凸包调用顺序修复 | `compare_recthull_order.py PRIVATE_SRC ORIGINAL NEW_REPORT` | `recthull-order-original-01`、旧码 negative-01、新码 native-01：只核受影响空输入的真实委托调用顺序 |
| 南北正交路由 | `compare_orthogonal_axes.py PRIVATE_SRC orthogonal-axes-request.json ORIGINAL NEW_REPORT` | `orthogonal-axes-original-01` 与 `orthogonal-axes-native-01`：4 组，真实冲突拆分、RNG、bend/JP 与引用 |

上表 HOST16 指 `test-runs/20261104-HOST-16`。本地目录不存在时，按 16 批 JSON 的 evidence 键找到归档副本。完整源码、真正执行过的 checker/probe、原始报告和命令分别保存；表内命令仅示参数，运行时应填完整路径。

四组尺寸检查包含 root、带外部端口的 child、普通 child 和旧尺寸为零的 IEEE 运算；固定 graphSize 的层级 caller 仍实际调整尺寸。检查真实 LPort ORIGIN 与相似字典的类型分支、原位置/列表引用、minimum 修改及 monitor 完成。

凸包退化案例只比较失败发生于 `of` 或 `split`，分别保存上游和 Python 异常，不声称跨语言异常类型或文本一致。随后代码审查发现“四次 sweep 后再加凹角”的调用顺序差异；旧六例保存不改，只为该变更新增真实委托叶子和旧码负控制。不得把旧六例重绑修复后的 SHA。

南北轴环形冲突两例均实际从 3 个 segment 拆为 4 个，RNG bounds `[3]`、4 个 slot；共享源和 self-loop 两例各 1 slot。新模块复用既有一般标量数学，不修改旧 direction0，也不以整图旋转替代实际策略。

compound pre/post 的几何输入为显式供给，用于隔离检查真实变换与标签、端点、JP 和 dummy 生命周期；它不证明已经运行整个 hierarchy scheduler 或 routing。Spline foundation、ranking 的 source/code receipt 也只批准各自范围；后续 producer/driver/Final 分开接通。

全部迁移功能完成后再执行全量验收。当前不重跑旧默认、自环、NS/BK、平台或安装矩阵。
