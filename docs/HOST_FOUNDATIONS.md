# E03 Python宿主基础模块使用

这里的代码已经实现并进入一键检查：有序JSON模型、九项核心选项解析、每次调用的数据隔离。
它们是E03内部开发接口，本身不计算布局。E04另提供真实`ELK.layout`受限切片与生成随机流，见[E04手册](E04_NATIVE_SLICE.md)；完整生命周期尚未验收。E03冻结设计见[ADR0002](decisions/0002-model-options-context.md)。

## 新会话运行

仓库根目录、CPython3.11+；离线入口不需安装依赖、Node或开发缓存：

```shell
python scripts/check.py --out test-runs/foundations-start-01
python examples/show_foundations.py
python scripts/validate_e03_foundations.py --out test-runs/foundations-report-01.json
```

一键检查发现foundation/model/options/execution测试组，保留每条命令的原始日志、退出码和代码SHA。
专用脚本核对来源收据、宿主声明，真实调用Graph/resolver/context，并分类25份既有请求；这里的accepted只表示输入数据可构建，不表示完成布局。
示例从src导入实际模块，演示整数2与字符串'2'区分、调用空映射替换及两次工作状态隔离，不生成坐标。

有固定Git/npm缓存时再校验实际canonical字节/行范围：

```shell
python scripts/upstream.py fetch
python scripts/validate_e03_foundations.py --with-upstream --out test-runs/foundations-source-01.json
```

Git源以固定commit的blob字节核验；Windows工作树CRLF与canonical LF身份分别记录。官方元数据是本仓库派生捕获，按lock SHA核验，不能当上游Git文件。
`scripts/check.py --with-reference`另外执行既有官方布局/56探针重采回放；它们不计作Python算法通过。

## 模型与身份

安装开发包后可从`pyelk.model`导入`Graph`；从源码运行的测试和示例显式加入本仓库src，不作为发行候选安装证据。

```python
from pyelk.model import Graph

data = {"id": "root", "children": [{"id": 1}, {"id": "1"}],
        "edges": [{"id": "e", "sources": [1], "targets": ["1"]}]}
graph = Graph.from_json(data)
assert graph.node(1) is not graph.node("1")
assert graph.to_json() == data
graph.node(1).set_property("custom", {"selected": True})
assert "custom" not in data["children"][0]
```

无损指字段、JSON值、对象和数组顺序，不承诺保留原始JSON文本字节；E02比较器仍使用独立的原请求bytes/Path指纹。
ID接受str（含空串）及Python int，拒绝bool/float；不字符串化，node/port/edge全局typed身份唯一。这是宿主设计，未声明完全复刻GWT整数转换。
nodes含root，按preorder；ports/edges按所属node及原列表次序。索引只读，`node/port/edge(id)`按原类型查找，有效类型的未知ID抛KeyError。
导入、导出和属性写入均深克隆；身份与结构不能经set_property重写，避免索引失效。显式尺寸须有限非负，缺失不补默认。
所有已识别元素的显式layoutOptions只做Mapping容器校验，内容在模型内原样保留。业务`$H`、`error.stack`、null/false/0不清理。
模型承载嵌套、ports、labels、hyperedge数据，不因此支持这些布局语义；primitive边明确拒绝。sections/points只做基础类型/有限值检查，不证明拓扑、坐标系或正交路由。

## 选项解析与调用上下文

`resolve_options(*,constructor=None,layout_arguments=None,local=None)`返回只读values/origins/selected_global，raw_values每次复制。
外层None是省略便利；显式option容器必须Mapping。所有出现的容器都校验类型，仅解析选中global内容，再由local覆盖。
call的layoutOptions字段存在即替换constructor默认，包括`{}`；未选中的构造内容不泄漏。同scope全ID/elk别名冲突拒绝，裸后缀暂拒绝。
九项解析规格与243规范诊断ID分开；已知未实现抛UnsupportedOptionError，未知抛UnknownOptionError。规范ID集合不注册任何算法，运行时不读references。
algorithm声明默认None与实际layout fallback来源分开；选中layered仅表示配置，不表示可以运行它。direction默认UNDEFINED，不提前推断RIGHT。
padding四边12、三间距20、分离组件true、正交routing、seed1。严格输入子集/字符串转换见ADR；seed0保留，但不承诺确定性或实现随机序列。

```python
from pyelk.execution import create_context

context = create_context(
    {"id": "root"},
    constructor={"defaultLayoutOptions": {"elk.direction": "LEFT"}},
    layout_arguments={"layoutOptions": {}},
)
assert context.resolved_options.values["org.eclipse.elk.direction"] == "UNDEFINED"
assert context.original_graph == {"id": "root"}
assert context.state == {}
```

working_graph、state、输入快照每次独立；original_graph/constructor/arguments以副本访问。worker参数只要出现就拒绝；algorithms筛选不得排除effective layered。
本模块不实现随机流、调度、async隔离、关闭或取消；E04在算法层新增真实随机流及最小本地关闭，完整执行生命周期仍待E08。不能用“上下文隔离通过”替代这些验收。
内部ValidationError携带code/path/message；path为RFC6901指针，根为`''`。模型和配置错误分别归ModelValidationError/OptionValidationError，尚不等于公开JS错误合同。

## 当前记录与下一步

来源见 [模型](../references/e03-model-sources.json)、[选项](../references/e03-option-sources.json)、[审计索引](../references/e03-audit.json)；[E03复盘](retrospectives/E03.md)记录跨审查修复。
下一轮按 [E04 brief](iterations/E04.md) 先完成逐组件生成源码/helper/许可对应，再机械移植真实默认处理链；保持既定坐标容差，不从测试快照复制坐标。
