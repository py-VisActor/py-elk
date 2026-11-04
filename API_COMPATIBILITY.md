# elkjs 接口对齐要求

当前活动状态见[完整实现与统一校验](docs/FULL_NATIVE_IMPLEMENTATION.md)：正式源码已接入全部 12 算法、243 选项和 8 类别，持久 worker 与完整公共 API 已整合。下方 E03–E09 切片说明保留历史验收边界，不代表当前入口只实现这些能力；完整发行验收尚未结束。

状态：公开ELK/layout完整设计规范。E03实现[宿主基础](docs/HOST_FOUNDATIONS.md)，E04–E07实现[受限四方向/多组件切片](docs/E07_DIRECTIONS_COMPONENTS.md)，实际验收见状态页，不等于本文完整API验收。基线为 elkjs 0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`；未进入切片的签名/行为仍为设计。

E08当前实现入口、实例隔离的九选项元数据及真实spawn异步/关闭/取消，精确宿主差异和边界见[ADR0007](docs/decisions/0007-e08-api-lifecycle.md)与[E08手册](docs/E08_API_LIFECYCLE.md)。官方全注册目录、FakeWorker关闭异常与Python原生策略分别保留；logging/time=true及完整算法/正式发布不因该实现提前验收。最终结果只读状态页及机器记录。

配套工作分解见[完整实施方案](docs/IMPLEMENTATION_PLAN.md)和[任务清单](docs/TASKS.md)。默认官方元数据已真实采集为 12 算法/243 选项/8 类别，Python 全部仍待实现。py-mermaid 后续直接采用 py-elk；不建立旧 ELK 版本兼容 profile。

E09 以 [ADR0008](docs/decisions/0008-e09-diagnostics-coverage.md) 续接真实日志/计时，替代 E08 合同中 true 分支的拒绝；false/省略仍无新诊断树。参数只接受 bool，Python 的0/1不当作布尔值。根 logging 清理与嵌套业务字段保护、固定生成源的 wall-tick 标尺和专属比较规则分别验证，旧 profile 不放宽。当前元数据约束见 references/e09-metadata-schema.json，旧 E08 契约保留为历史；全部算法与正式发行仍待后续验收。
这里“待实现”指算法/公开布局语义；九项内部解析schema和243规范ID诊断分类已有真实代码，后者不作为可用注册表。

先交付并发布[独立基础正式包](docs/FIRST_RELEASE_SCOPE.md)，py-mermaid 集成后置单列。本文保留完整长期目标；基础 0.1.0 只声明已验证的单层 layered/核心选项，其他项留在分母并明确拒绝未支持输入。

## 1. 兼容等级

每项功能分别登记以下等级，不用“支持 ELK”概括全部能力：

| 等级 | 要求 |
| --- | --- |
| API | 入口、参数、异步返回方式、元数据字段及输入输出结构兼容 |
| 语义 | 方向、间距、层级、端口、边路由等约束按同一选项生效 |
| 坐标 | 在固定参考版本、输入顺序、随机种子下，节点及边几何数据通过差分比较 |

通过 API 测试不自动获得语义或坐标兼容标记。阶段性支持范围写入测试清单；没有测试证据的项目维持“未验证”。
实际可运行的官方采集/差分/几何/确定性脚本见[布局校验手册](docs/LAYOUT_VALIDATION.md)，当前Python执行域和安装验收见[E04手册](docs/E04_NATIVE_SLICE.md)。

## 2. 公开入口

| elkjs 入口 | Python 目标接口 | 要求 |
| --- | --- | --- |
| `new ELK(options?)` | `ELK(options=None)` | 接受可选映射，保留原参数名 |
| `layout(graph, args?)` | `async layout(graph, args=None)` | 返回布局后的图映射；失败抛 Python 异常 |
| `knownLayoutAlgorithms()` | `async knownLayoutAlgorithms()` | 返回实际已注册算法的描述列表 |
| `knownLayoutOptions()` | `async knownLayoutOptions()` | 返回实现已识别的选项描述列表 |
| `knownLayoutCategories()` | `async knownLayoutCategories()` | 返回已注册算法对应的类别描述 |
| `terminateWorker()` | `terminateWorker()` | 同步释放资源；E02设计为重复关闭无害、关闭后拒绝新任务，运行时测试留待实现 |

Python 的 coroutine 对应 JavaScript Promise，不提供 `.then()` 模拟层。`layout_sync()`、snake_case 别名和上下文管理器可以后续增加，但不是首轮兼容的必要条件；同步扩展不得在已有事件循环中直接调用 `asyncio.run()`。

### 构造参数

| 参数 | 对齐要求 |
| --- | --- |
| `defaultLayoutOptions` | 保存默认全局布局选项；避免保存可被外部意外修改的共享状态 |
| `algorithms` | 按短算法标识选择注册范围；查询结果与可调用范围保持一致 |
| `workerUrl`、`workerFactory` | 属于 JS 执行环境能力；Python 首版遇到显式传入时抛 `NotImplementedError`，说明不支持，不能悄悄忽略或执行 JavaScript |

兼容算法注册时，需要核验上游总是注册的基础算法，以及显式空列表、缺省列表、无效标识的区别。未实现算法不进入可用列表；元数据基线与已实现清单分开保存。

### layout 参数

| 参数 | 要求 |
| --- | --- |
| `graph` | 必填，ELK JSON 图映射；验证结果不能破坏原始输入 |
| `args.layoutOptions` | 全局布局选项，按节点或其他图元素上的局部值覆盖 |
| `args.logging` | 默认关闭；启用后在返回图中提供布局日志树 |
| `args.measureExecutionTime` | 默认关闭；保留固定生成源 wall 毫秒差×1000×1e-9 标尺，不能按通常秒解释 |

上游 API 对默认选项采用**调用级替换**：未传 `args.layoutOptions` 时使用构造默认值；显式传入映射时使用该映射，包括空映射，不把它与构造默认值逐键合并。局部图元素选项优先于对应的全局选项。父子图的继承、算法缺省值及各算法默认参数需通过参考样例冻结，不假设所有父级选项都会继承。

输入图和嵌套列表不原地修改是本项目目标。JS 实际数据保留行为、缺失字段与零值输出形态需在 M1 采样核对；有意不同之处单独记录，不能改写参考结果来适应 Python 实现。
E02已用56个官方进程探针冻结 [原生合同](docs/decisions/0001-native-contract.md) 和显式`native-basic-layered-v1`比较profile。
Python输入精确保留、参考新增形状`$H`的有限投影是两项明确适配；原始strict差异始终保留。业务字段、section ID、顺序及所有其他字段继续比较，用法见[手册](docs/LAYOUT_VALIDATION.md#显式原生合同profilee02)。这两项规则已用于E04真实安装对照，其他API行为仍按完整计划验收。

## 3. ELK JSON 数据契约

| 对象 | 输入重点 | 输出重点 |
| --- | --- | --- |
| Node | `id`、`children`、`ports`、`edges`、`labels`、`layoutOptions`、尺寸 | `x`、`y`、`width`、`height`，保留层级和关联 |
| Port | `id`、尺寸、位置及端口选项 | 相对所属节点的位置与尺寸 |
| Label | `text`、尺寸、可选 `id`、选项 | 所属元素坐标系内的位置与尺寸 |
| Extended edge | `id`、`sources`、`targets`、标签与选项 | `sections`、必要的 `container` / `junctionPoints` |
| Edge section | 可选的已有几何及拓扑关联 | `id`、`startPoint`、`endPoint`、可选 `bendPoints` 和形状/section 引用 |

要求：

1. 优先支持 extended edges。识别旧式 `source` / `target` 边并作为独立兼容项处理，不与 extended 格式混用。
2. 节点、端口和边的标识及端点引用必须可解析；重复 ID、缺失引用、无效尺寸应有包含元素路径的错误。
3. 上游 TypeScript 声明主要使用字符串 ID；通用 ELK JSON 还允许整数 ID。M1 必须覆盖两者，明确参考版本的实际行为，避免未经核验地字符串化而合并不同 ID。
4. 嵌套节点、端口、标签和边的坐标系按 ELK 规则处理。边几何依据布局容器解释，不能简单当作根图绝对坐标；跨层级边需要独立测试。
5. 多源或多目标边是 hyperedge，不把它静默展开成普通边。算法尚未支持时返回明确的未支持错误。
6. 空图、单节点、零尺寸、非连通分量、自环、环、平行边、长边、已有布局信息均进入样例集。
7. 自定义字段的保留与删除以参考行为为准。数据验证与内部模型转换不得导致无关业务数据丢失。
8. 标签尺寸由调用方提供；首版不引入字体排版引擎，也不以字符串长度猜测字形尺寸。

坐标系及 JSON 细节参见 [ELK JSON](https://eclipse.dev/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html) 与 [Coordinate System](https://eclipse.dev/elk/documentation/tooldevelopers/graphdatastructure/coordinatesystem.html)。通用网页可能持续更新，冲突时通过固定版本的实际行为裁定。

## 4. 选项兼容

优先支持完整 `org.eclipse.elk.*` 标识和对应 `elk.*` 别名。短后缀只在能够唯一解析时生效；歧义与未知选项的处理以参考样例确定。类型转换、枚举大小写、缺省值、padding 字符串格式都要测试，不仅匹配 key 名。

| 批次 | 选项或选项组 | 验收重点 |
| --- | --- | --- |
| M2 | `algorithm`、`direction`、`padding` | 算法选择、四个方向、容器边界 |
| M2 | `spacing.nodeNode`、`layered.spacing.nodeNodeBetweenLayers` | 同层及跨层间距、可变尺寸 |
| M2→M3 | `edgeRouting`、`randomSeed` | 首版正交几何和确定性；折线/样条在 M6 扩展 |
| M2→M3 | `separateConnectedComponents`、`spacing.componentComponent` | 基础版分量打包和空间隔离 |
| M6 | `portConstraints`、`port.side`、`port.index`、端口间距 | 侧面、顺序、固定位置和锚点 |
| M6 | `hierarchyHandling`、标签布局与节点尺寸约束 | 层级、跨层级边、边界与包围盒 |
| M6 | layered 的 cycleBreaking / layering / crossingMinimization / nodePlacement 选项 | 每个策略分别注册、分别差分，不用同一个简化实现冒充全部策略 |

这张表是开发优先级，不表示已实现。后续为每个选项维护规范 ID、别名、类型、默认值、适用算法/元素和测试用例编号。上游可识别但 Python 尚未实现且会改变结果的选项，要明确报告未支持；未知选项与未实现选项不能混为一谈。

## 5. 算法范围

| 阶段 | 算法 | 目标 |
| --- | --- | --- |
| M2 | `layered` | 平面图核心流程及基础边路由 |
| M3 | `layered` | 基础正式版范围的默认路径、API/选项/错误与坐标闭环 |
| M6 | `layered` | 高级端口、标签、层级、完整策略/选项及路由 |
| M7-A | `fixed`、`box`、`random` | 基础算法逐项验证，固定随机数行为 |
| M7-B | `mrtree`、`radial` | 树结构及相应约束 |
| M7-C | `force`、`stress` | 数值迭代、终止条件、随机与容差 |
| M7-D | `disco`、`sporeOverlap`、`sporeCompaction`、`rectpacking` | 依参考版本元数据建立独立移植任务 |

最终可用算法清单必须从固定版本运行时查询得到，再与 Python 注册表逐项比较。上游默认注册列表、用户筛选及算法元数据均是兼容测试内容。某算法未实现时不能回退为 layered 并仍保留原算法名。

## 6. 元数据、异常与生命周期

- 算法描述对齐 `id`、`name`、`description`、`category`、`knownOptions`、`supportedFeatures`；选项描述对齐 `id`、`name`、`description`、`group`、`type`、`targets`；类别描述对齐 `knownLayouters` 等字段。
- 参考实现完整元数据保存为基线快照。Python 查询只返回已实现/已注册范围；结果中不能把参考快照直接当作可用功能列表。
- 设计公共异常基类 `ELKError`；内部异常类型可区分错误类别，但当前差分profile严格比较公开name/message，不做泛化归一或消息裁剪，不比较工具错误stack。
- 日志树和时间单位需要兼容；当前比较器严格比较result内日志/计时，没有已批准的差异屏蔽。其他宿主适配须后续独立决策。
- E02冻结设计边界；Python `None`便利映射为省略，不宣称等同JS null。关闭/并发/取消设计见ADR；E03/E08实现后才能验收。

已观察到锁定 npm 发行物的 bundled/FakeWorker 模式 `terminateWorker()` 抛 `TypeError: this.worker.terminate is not a function`，采集清单保留该结果。不能把 Python 拟定的正常关闭语义写成 JS 已有行为；M1 分别核实 main、bundled、浏览器和真实 Worker，并记录 Python 的适配决策。

## 7. 差分验收

1. 参考工具固定 npm 依赖 `elkjs@0.12.1`，提交锁文件并在 CI 使用可重复安装；Node.js 仅用于开发和参考测试。
2. 每个样例包含输入、调用参数、构造参数、参考输出、版本/环境及比较等级。保留原始参考 JSON，不覆盖；规范化产物另存。
3. 对象键顺序不影响JSON语义，数组顺序严格保留。默认strict不适配副作用/私有字段；显式原生profile只采用E02两条冻结规则，并列出每次适配。日志耗时目前也严格比较。
4. API/schema：字段、关联、选项覆盖、元数据范围与异常类别验证；支持清单中的测试必须全部通过。
5. 语义：方向、节点不重叠、间距、端点归属、容器包围盒、正交边段与端口约束验证。允许重叠的选项/模型单独声明，不能套用错误的不变量。
6. 坐标：对确定性样例比较所有节点、端口、标签、section 点位及尺寸；默认 `abs_tol=1e-6`、`rel_tol=1e-9`，更宽容差必须按算法给出理由和独立状态。
7. 精确匹配、容差内匹配、语义通过但坐标不同、未支持、失败分别统计。跳过项不计作通过，不把坐标差异改名为兼容。
8. 每个里程碑提交机器可读报告和差异清单；示例可以渲染为 SVG 辅助人工检查，但不能以截图看起来相近代替几何验证。

## 8. 规范依据

- [固定版本 API 声明](https://github.com/kieler/elkjs/blob/624ae90aa37110033a8af59c5ccbb292708b4317/typings/elk-api.d.ts)
- [固定版本 API 实现](https://github.com/kieler/elkjs/blob/624ae90aa37110033a8af59c5ccbb292708b4317/src/js/elk-api.js)
- [固定版本 README](https://github.com/kieler/elkjs/blob/624ae90aa37110033a8af59c5ccbb292708b4317/README.md)
- [ELK 算法参考](https://eclipse.dev/elk/reference/algorithms.html)
- [ELK Layered 参考](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html)
