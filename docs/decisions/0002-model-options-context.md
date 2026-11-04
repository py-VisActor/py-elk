# ADR-0002：E03有序模型、选项与调用上下文

状态：frozen-design，revision 1；2026-11-03。本轮run为`test-runs/20261103-E03-01`。
这是Python宿主数据基础的设计，不是Java算法移植或公开ELK API验收。E02合同、原始参考和12/243/8分母保持不变。

## 共享边界和错误

root独占`src/pyelk/_errors.py`、`_json.py`。`ValidationError(code, path, message)`公开给内部模块三个属性，path为RFC6901指针，根为`''`。
模型使用`ModelValidationError`；选项使用`OptionValidationError`，已知未实现和未知ID分别用其子类`UnsupportedOptionError`、`UnknownOptionError`；显式worker等域外能力用`UnsupportedFeatureError`。
这些内部异常不冒充JS name/message兼容。`clone_json(value, *, path='', error_type=ValidationError)`只接受JSON值和作为宿主便利的Mapping；深克隆、拒绝循环/非字符串key/非有限浮点/tuple和任意对象；非循环的重复引用分别克隆。
`pointer(path,key)`转义路径；`finite_number(value, *,path,nonnegative=False,error_type=...)`验证有限数值，bool不当作数值。

## A模型接口

`pyelk.model.Graph.from_json(mapping)`与`Graph.to_json()`双向深克隆，不补写缺省字段或生成任何坐标。root必须为映射且有id。
`Graph.root`为Node；`nodes`按preorder且包含root；`ports`及`edges`按所属node preorder和原数组顺序；tuple遍历与只读索引不排序。
`TypedId(kind,value)`只允许`kind='string'|'integer'`，Python str（含空串）和int（不含bool）为两种不同身份；float（含1.0）拒绝。
这是明确的Python身份设计，不宣称完整模拟GWT整数数值转换。node/port/edge共享全局typed身份唯一约束；标签可选id保留并验证类型，但不加入端点索引。
`node_index/port_index/edge_index`只读；`node(id)/port(id)/edge(id)`按原类型查找；坏引用、重复身份和无效尺寸报带输入路径的错误。
Node具备id/path/parent/children/ports/edges；Port具备id/path/owner；Edge具备id/path/sources/targets及解析后的端点。各自`to_json()`返回副本。
Node/Port/Edge提供`set_property(key,value)`用于修改独立工作副本；结构/身份字段不能经此改写造成索引失效，JSON与尺寸验证仍适用。该方法不做布局。
显式width/height须有限非负，缺失不补默认，null/bool拒绝；空children/ports/labels/edges保留，显式null结构容器拒绝。业务null/false/0、`$H`和`error.stack`完整保留。
所有已识别元素上的显式layoutOptions由模型验证为Mapping（含子node/port/edge/label/section）；仅验证容器，不解析内容，解析优先级仍归B。set_property保持同一约束。
数据模型可承载嵌套node、ports、labels和非空extended sources/targets列表（含hyperedge）；这不扩大首版或E02布局profile。primitive边本轮明确拒绝，不做静默转换。
内部`Anchor(x,y)`为有限坐标、`Margin(top,right,bottom,left)`为有限非负边距；不自动注入公开JSON。使用关键字参数避免边距顺序歧义。

## B选项接口

`resolve_options(*,constructor=None,layout_arguments=None,local=None)->ResolvedOptions`；ResolvedOptions至少有只读`values`、`origins`和`selected_global`。
None只作为外层省略便利；显式defaultLayoutOptions/layoutOptions/local选项容器须为Mapping，null/falsy scalar拒绝。
所有出现的选项容器均检查类型；只有被选中的映射内容参与解析。构造映射内未知key被call空映射替换后不泄漏，但构造容器本身为null仍拒绝。
按字段存在性选择调用layoutOptions或构造defaultLayoutOptions，调用`{}`会替换构造默认。仅解析选中的全局值，再由local覆盖；不从未选择的构造默认泄露选项。
同scope内全ID与elk别名指向同一选项时，即使同值也拒绝；跨scope覆盖合法；裸后缀暂拒绝。
只实现机器首版清单九项；243规范ID可内置为诊断常量，用于区分已知未实现与未知，不能作为可执行注册表，运行时不加载references。
OptionSpec记录声明默认；algorithm声明缺省为None，effective解析可按已核实的layout fallback选择规范layered，并将origin记作`layout-fallback`，不表示算法已注册。
其他默认：direction UNDEFINED（不推断RIGHT）、padding四边12、三项间距20、组件分离true、edgeRouting ORTHOGONAL、seed1。显式fixture30/40/seed7不是默认。
算法值只接受layered/规范ID；其他算法明确未实现。枚举只接受名称，不模拟ordinal。direction接受UNDEFINED/四方向；routing仅ORTHOGONAL。
间距接受有限非负数值或数值字符串，bool拒绝；seed接受有符号32bit整数或整数字符串，bool/float拒绝，0保留且不宣称确定性；boolean接受bool或大小写无关true/false字符串。
padding接受完整四边Mapping或ELK`[top=...,left=...,bottom=...,right=...]`四边字符串，四边有限非负；本轮不模拟缺边/重复key/其他宽松格式，明确拒绝。
`Padding`为不可变值，字段top/right/bottom/left；保留原值和解析值分别记录，来源/未支持语法写入本轮材料。

## B调用上下文接口

`ExecutionContext.create(graph, *,constructor=None,layout_arguments=None)`；另提供`create_context`同签名便利函数。
上下文保存原graph/constructor/arguments的独立深快照，`working_graph`为A模型的独立实例，`resolved_options`按root局部选项解析，`state`为每次全新dict，`seed`只保存配置。
快照以副本访问；workerUrl/workerFactory只要出现即明确拒绝。constructor.algorithms若出现须为string list；不把它转成可用注册表，也不忽略排除了effective layered的筛选。
不创建Python random冒充Java随机流，不实现async调度、关闭/并发/取消状态机，不宣称生命周期验收。模型中的业务修改和state写入仅作用于该上下文。

## 独占文件及验收

A：`src/pyelk/model/`、`tests/model/test_ordered_model.py`、`references/e03-model-sources.json`及run/A。
B：`src/pyelk/options/`、`src/pyelk/execution/context.py`和`__init__.py`、`tests/options/test_resolution.py`、`tests/execution/test_context.py`、`references/e03-option-sources.json`及run/B。
V：`tests/model/test_model_cases.py`、`tests/options/test_option_cases.py`、`tests/execution/test_context_cases.py`及run/V。root：共享模块、foundation测试、全局入口/审计/文档/计划/复盘。
局部测试限定owner文件；反审为A审B、B审V、V审A/root；先交接稳定，再集成全量。每条命令单独记录exit与日志；原失败保留。
输入、输出、跨调用隔离、结构不变量和错误路径各自验证，不只比较双方相等；参考源按固定commit/path/SHA绑定，host设计不能标为完整上游通过。
