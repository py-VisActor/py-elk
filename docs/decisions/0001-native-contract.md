# ADR-0001：原生Python合同与显式比较profile

状态：**frozen-design，revision 1**。日期：2026-11-03。profile ID：`native-basic-layered-v1`。
机器合同见 [native-contract.json](../../references/native-contract.json)。这是E02的设计与校验工具合同，不表示已有Python ELK API、算法或生命周期实现。
规则冻结与探针receipt封存分别处理；V最终交付后核对原请求字节、requestSHA和raw observation SHA，不能用规则冻结代替事实验证。

## 背景与已验证事实

锁定参考为elkjs0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`，bundled入口固定SHA。
原始strict合同同时比较result/error和graph、constructor、arguments的调用后状态。参考FakeWorker会修改输入图；Python目标是调用方输入不变。
因此需要显式记录宿主差异，同时保留全部原始差分，避免为模拟GWT私有数据污染Python接口。

本轮固定源与[官方探针](../../references/e02-contract-probes.json)确证：

- JS构造/调用参数缺省、undefined与显式null不同；null外层构造/调用参数抛同步TypeError。
- JS可以接受部分false/0/空串形态，`layoutOptions`中的null/falsy值也可能成功；这不自动成为原生profile支持范围。
- 调用提供的layoutOptions替换构造默认值，包含显式空mapping；root局部选项再覆盖所选全局值。
- 成功调用中reference inputAfter与result exact相等，constructor/arguments保持不变。同一图先开启logging，再缺省调用，参考会在原图上创建并清除logging。
- 原root/child缺少`$H`时会生成GWT身份hash；用户已有的0/false/null会被参考覆写。测试过的字符串/正整数与嵌套business/data同名字段保留。
- 未知端点/算法错误时，测试输入只增加了原本缺失的形状`$H`；去掉这些新增键后可exact恢复原图。
- 当前FakeWorker terminate抛TypeError，之后layout仍能成功；该现象不是Python正常关闭的合同。

事实仅对应记录的入口/参数/探针，不泛化成全部Worker、API、JSON值或生命周期通过。Java精确构建来源仍单独保留E01 open项。

E01固定worker的缺省证据为：padding四边12、同层/层间/组件间距各20、分离组件true、randomSeed1、layered路由ORTHOGONAL。
direction属性缺省是UNDEFINED，之后依据aspectRatio等条件解析；不能把某个缺省探针观察到RIGHT直接写成所有图的属性缺省。
现有项目样例显式给出的层间30、组件40、seed7仍是测试配置，不是这些默认值。本轮比较profile不替代E03的实际默认值/解析实现。

## 决策一：原始strict与公开合同分开报告

`strict`继续是默认模式；原有exact/coordinateTolerance的含义保持为完整原始合同差分。
显式原生profile另报rawStrict、publicContract、每一项adaptation、candidate inputPreservation和所选profile的passed。
原生通过不覆盖strict差异，不自动表示独立几何/确定性通过，也不提升Python算法/API/生命周期状态。
官方replay仍用strict；原始json诊断不自动应用原生profile。

公开result保留完整字段、数组、section ID和所有非适配数值。几何数值继续使用既定`1e-6/1e-9`，不平移、缩放、居中或重新排序。
logging/measureExecutionTime未设置或布尔配置可以诊断，但result中的日志模块名、日志内容和计时值仍strict；没有时间字段忽略名单。
错误stack只属于已有diagnostics排除边界；业务数据中的`error.stack`仍是普通业务字段，不得递归删除同名字段。V探针已保留这类业务值。
测时值不确定导致的差异照常失败。此profile不能据此宣称计时或其他日志扩展兼容，后续扩大规则须另行记录依据。

## 决策二：必须使用真实请求字节

native比较必须另提供原始UTF-8 JSON bytes或读取其字节的Path。比较器自身计算SHA256，双方observation的requestSha256均须匹配。
只给解析后的dict、重新序列化的替代请求、缺请求、重复键、非有限数或指纹不符均拒绝。
schema为`py-elk-layout-request/v1`，constructor/graph/layoutArguments均来自同一原始请求；比较器不得修改请求或原始observation。
probe的JS undefined使用显式kind记录，不把它伪装成JSON null。

## 决策三：原生输入保留

candidate的inputAfter、constructorAfter、argumentsAfter必须分别与原graph、constructor、layoutArguments **exact相等**，包括键是否存在、业务字段、原有几何和参数。
输入保留不使用坐标容差；候选输入的微小修改也失败。
reference constructorAfter/argumentsAfter发生未知改动时暂不支持原生适配。

成功参考调用仅在inputAfter exact等于result时使用已观察的原地回填适配：公开输入期望为原请求graph，完整参考副作用仍出现在rawStrict和adaptation记录。
错误参考调用仅允许经核实的原root/child缺失`$H`新增；剥离这些符合规则的新键后必须exact等于原图，否则fail closed。
这项输入所有权映射不能推导出任何输出业务字段可忽略；candidate result仍完整对照reference公开result。

## 决策四：只适配有前提的参考新增形状hash

只允许`/result/$H`和`/result/children/<原模型索引>/$H`；错误时同样的inputAfter路径仅用于核对已知副作用。
每个适配都必须满足：

1. 对应原始形状没有该key，reference实际新增的是有限整数，bool不算整数。
2. 原始、reference和candidate的形状ID、child数量与顺序对应，不能排序或换ID后配对。
3. candidate不得新增未由原始输入提供的shape `$H`，即使值等于reference也拒绝。
4. 每条实际适配记录具体路径、值、规则和前提；原始reference字节与差异始终保留。

用户原有的shape `$H`不适配。须检查reference和candidate对应result/inputAfter都保留其原key/value；reference覆盖0/false/null即前提失败，即使candidate也复制了同一覆写值、使两结果相等，仍不能通过。
业务/data/options/logging/edge/section等其他路径的`$H`严格比较，不做同名通配删除。生成section ID、数组顺序和几何值均不属于私有hash适配。

这里的碰撞fail closed是**比较profile的支持边界**，不等于Python运行时可以丢弃该业务字段，或必须拒绝调用方传入0/false/null。
Python输入保留目标仍成立；若需要对该JS碰撞支路声明兼容，必须形成另外有证据的显式策略，而非抹去冲突。

## 决策五：保守限制v1返回域

成功域为平面root/children、字符串身份、给定有限非负节点尺寸、单源单目标extended root edges与正交路由。非空端口/标签/嵌套图、primitive/hyperedges和其他坐标模式不纳入v1。
constructor、layoutArguments及出现的选项容器必须为mapping或按schema缺省；显式null/falsy scalar即使JS成功，也暂不纳入该成功域。
可诊断错误仍以完整named error和原输入对照，不能从某个错误通过推断整个注册/解析范围支持。

成功算法选择仅接受缺省layered、`layered`或`org.eclipse.elk.layered`；选择key仅接受`org.eclipse.elk.algorithm`与`elk.algorithm`。
路由key仅接受`org.eclipse.elk.edgeRouting`与`elk.edgeRouting`，成功值为缺省/ORTHOGONAL。
先取root局部值，再取显式调用layoutOptions；只有调用该字段缺省才取构造defaultLayoutOptions。
同scope存在两种alias，即使值相同也先拒绝；裸后缀、未知选择形式和未列适配不得靠truthiness补全。
这些是校验profile边界；更完整resolver属于E03，并须用新增来源/断言及明确版本化规则扩展。

constructor显式出现workerUrl/workerFactory时均不进入原生profile，包含null/false。strict仍可报告参考的实际行为。
成功域若显式设置constructor.algorithms，必须是包含短名`layered`的string list；省略则按参考默认注册上下文处理。
额外string条目只作为本次layout的诊断上下文，不构成其他算法或元数据兼容声明。不能让排除了layered的`[]`/`['stress']`配上伪造的returned图进入成功域。
坐标控制检查全局及所有root/child形状局部layoutOptions；v1显式shapeCoords/edgeCoords仅接受INHERIT，其他frame和INCLUDE_CHILDREN层级处理均域外。
profile定义本身须为frozen-design、revision为严格整数1；draft、bool冒充版本号或未知定义均拒绝。

## 决策六：错误与Python宿主设计

error.name/message一律exact。比较器不把任意ValueError/TypeError/NotImplementedError统一改名Error，也不删Java限定名、路径或消息内容。
未来兼容异常可明确公开JS兼容name；导入错误、adapter失败、缺少真实ELK等必须继续是harness失败，不能伪装成ELK错误契约通过。

Python外层`options=None`、`args=None`作为省略参数的便利形式属于明确的宿主API设计，不声称JS null等价。
内部显式null、false、0、空串与missing仍要按键存在性分辨，不能让这些值意外触发构造缺省合并。
调用选项替换、局部优先级和每次执行独立工作图在E03实现；当前没有原生API实测结果。

拟定Python关闭目标为幂等、不再接收新的layout并释放自身资源，不复刻FakeWorker terminate异常。
正在执行/排队任务的具体关闭策略、同实例排序/隔离、并发调度、取消检查点/恢复和资源限制，由E08实际实现与测试后声明。
`async def`不自动承诺CPU并行、立即取消或时延保证；本轮所有lifecycle/concurrency/cancellation acceptance仍为false/NOT_ASSESSED。

## 验收与后续

B按冻结规则实现显式profile，V提供独立原始探针和碰撞/非适配路径/错误/指纹反例；root在稳定屏障核对完整产物与复盘。
不得为取得全部官方探针“通过”而扩大适配；范围外结果可以明确失败，来源事实与原生设计分别报告。
本轮可验证比较器与设计自洽性，不能因此将生产能力、完整上游断言覆盖或正式包状态升级。
最终source引用统一为sourceId/path/commit/sha256；receipt封存后更新的只是实际观察身份，规则变化须单独修订ADR/profile版本。
