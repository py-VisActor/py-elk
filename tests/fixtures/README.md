# 共享输入与预期结果

[cases.json](cases.json)当前只有一个自行编写的双节点输入，状态 planned；没有 Python 或 JS 布局结果。
实际可执行验证使用 [validation/cases.json](validation/cases.json)：25个自行编写请求，22个成功/3个错误，固定参数与非零seed。
真实官方输出、错误与副作用见 [references/layout](../../references/layout/index.json)，每例2次独立进程；新采集默认3次。
没有 Python 布局通过结论，也不是完整上游断言覆盖。
生成器只产生输入，不计算预期坐标。新增案例与重采流程见 [操作手册](../../docs/LAYOUT_VALIDATION.md)。
正式 case 包含稳定 ID、上游路径/symbol/assertion、source SHA、constructor/args、原始 graph、
随机种子、预期结构/错误/副作用、比较 profile 和证据。多断言、参数组合、负例分开登记。
不得通过排序 children/ports/edges、删字段或重新中心化坐标来隐藏差异。
