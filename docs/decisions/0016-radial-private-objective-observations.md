# ADR 0016：Radial 私有优化目标的已观察浮点差异

状态：记录并保留；不修改比较容差、算法代码或已发布包。

对四种 `radial.optimizationCriteria` 的实际私有 Eades/factory/evaluate 调用完成了有限状态对照。NONE 实际返回空 optimizer、没有 evaluate；三个 optimizer 各实际 evaluate 360 次。已观察案例中，最终所有节点几何、控制状态和选中最优 offset 均精确相同。

内部目标数组存在原始严格差异：EDGE_LENGTH 的 360 项中 9 项不同，其中 7 项为 1 ULP、2 项为 2 ULP，最大绝对差 `2.84e-14`；EDGE_LENGTH_BY_POSITION 的 360 项中 2 项不同，均为 1 ULP，最大绝对差 `5.68e-14`。这些项目继续保持 `exactObjectives=false`，不能计成内部标量精确通过，也不能套用坐标容差将其涂成 PASS。

两位独立审阅者核对了固定 Source 与 Python 的加减乘、`sqrt(x*x+y*y)`、原 root/edge 访问顺序、clip、加法累计和原 360 offset 遍历，未发现公式简化、补偿求和或重排。V8 Math 与 CPython 宿主数学函数的中间舍入是候选原因；现存记录没有每个 offset 的中间三角函数和分边项，因此不能确定首先发生差异的 primitive，也不假定任意输入的最优角保持一致。当前 EDGE_LENGTH 最小与次小值本就非常接近。

验收应分开记录：实际分支选择及调用得到见证；该有限案例的最终几何与最优 index 精确匹配；私有目标数组的严格差异明确公开。它不是七次新增公共 API 整调用，也不是一种新的全局数值兼容 profile。已有公共调用、既有坐标规则和其他失败／未评估状态保留原证据范围。

原始对照与 ULP 诊断随 E17 验收材料归档，入口见 [E16–E19 条件清单](../iterations/E16_E19_ACCEPTANCE.md)。以后若需保证该私有目标函数或近退化选择的 V8 位级一致，应单独建立中间运算对照；本记录不以未测的泛化保证结束该问题。
