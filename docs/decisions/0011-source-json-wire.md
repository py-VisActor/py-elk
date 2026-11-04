# 算法内部数值与最终 JSON 输出

固定参考捕获器最终使用 `JSON.stringify(observation)`。原 `JSONNumber` 及对象赋值保留 NaN、正无穷和负无穷；最终 JSON 字段输出 `null`。原 worker 三项 helper 的实际观察与原字节来源保存在 `tests/fixtures/suites/next-native/json-wire-*`，独审为 `json-wire-source-review-01.json`。

原生 `json_wire` 在返回 JSON 图时复制数据，将生成的非有限 float 转为 Python `None`。它不改变 Session、属性、坐标或算法中的内部数值。输入仍按原生既定有限值规则校验。字符串 `"NaN"`、用户业务字段、字段存在性和其它 JSON 类型保持各自含义。

径向 `radial-wedge-polar-rotate` 的原输出本身包含空坐标。对此记录 `sourceWireParity=true`、`validFiniteGeometry=false`、`upstreamNonfiniteGeometry=true`。这与两个正常有限几何样例分开统计，不能把 JSON 对照一致称为有效几何通过。算法内部不会为使结果有限而钳制、补零或更换计算公式；原几何检查与容差也不修改。

该转换在算法及观察行为之后执行。原 API 在收集计时信息时产生的异常仍须保留；它不会通过 JSON 转换变成成功结果。一个新增 MrTree 官方计时请求已实际触发原上游 `java.lang.NullPointerException`，具体高级诊断和错误映射继续在宿主阶段实施。

Session语义几何已在finite校验后落实binary64表示，包含shape/port/label几何与point；缺省为0.0。`numeric-import-*`原版小探针及`compare_numeric_import.py`核了两例大整数舍入、负零、最小subnormal与最大finite，保留随后一次加法的真实结果。新来源见`references/next-numeric-import-sources.json`及独审，不增加图数或数值上限，不转换整数ID或业务字段。完整DOUBLE选项存储和其他数值层仍待继续，不能据两个几何helper样例声明整个数值层或算法完成。
