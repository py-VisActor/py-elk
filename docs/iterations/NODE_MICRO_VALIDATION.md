# 通用微布局与真实 provider 对照

当前私有代码使用同一 `JsonLayoutSession` 执行端口排序、完整节点/标签尺寸计算、margin 计算和各 provider。`session.node_micro_layout(node)` 调用实际 `node_size_process.process_node_size`；默认路径不设置 `omitNodeMicroLayout=true`。通用 adapter 按源中的 child/port/label 身份、compound 关系、边视图、Core 默认与可变属性缓存工作。

源闭包见 `references/next-node-micro-sources.json`、`node-micro-topdown-sources.json`，节点尺寸各组件见 E13 来源。私有 parser 现为63项 schema；它不等于243项完整 parser，正式发布包与公开 API 仍未切换。06批新增hook与属性修正见[共享运行层手册](HOST_DELTA_VALIDATION.md)。

本批首次对4个已保存官方 MrTree 请求执行真实默认 provider，覆盖 RIGHT/DFS、DOWN/BFS、LEFT/forest、UP/cycle，四次实际 micro 调用，严格非 `$H` 差异为0、最大坐标误差0。原 strict 共25项 GWT `$H` 差异保留。之后只为新 wrapper 改动执行首例一次，不重跑四例组。

新增两个真实 generic adapter 原控覆盖排序、node/port labels、edge head/tail 和 margin。入边同 owner 加 YO 的原条件与出边不对称，首稿失败后仅改该分支并重核该一例；另一成功例保留旧执行绑定。

径向新增三个官方请求：两个有效有限几何样例通过，一个上游非有限输出样例单列 wire 一致性。一个有限例最大误差约 `1.42e-14`，另一个严格非 `$H` 差异为0；比较器继续使用已有 `/result` 数值路径和容差。最后修复仅最终 wire 边界，只重核第三例；具体见 [输出决定](../decisions/0011-source-json-wire.md)。

在仓库根目录先恢复到新的目录，再按实际变更选检查。所有输出路径应是新路径：

```shell
python scripts/iteration/next_workspace.py restore --destination .local/micro-new-review
python -m unittest tests.next_native.test_micro_state.PrivateMicroStateTests.test_presence_distinguishes_parent_local_defaults_false_zero_and_property_removal -v
python tools/reference/compare_next_mrtree.py --source .local/micro-new-review/src --oracle tests/fixtures/suites/next-native/mrtree-first/oracle.json --case tree-right-dfs --out .local/micro-new-review/mrtree-first.json
```

原始 generic、节点尺寸和径向数据及比较脚本在 `tests/fixtures/suites/next-native`。各 `compare_*.py` 的 docstring 给出位置参数；需要修失败分支时使用其单 case 参数，复用原始观察，不重新采 Node 或重跑无关组。源码、raw JSON、命令/日志和执行 SHA 分别保存，不修改旧执行绑定。

`test_micro_state` 验证源类型对应的默认值身份、真实 fixed helper 消费 native DTO、全局映射拥有权/targets、signed32 原生 identity，以及最终 wire 不改变内部数学或输入校验。内部 hash 策略见 [ADR-0010](../decisions/0010-native-object-identity.md)。

共享 Session 提供 `has_option(element,name)`、`set_option(element,name,value)` 和 `remove_option(element,name)`。存在性不请求默认值，显式 `False`/`0` 仍存在；删除会遮蔽该 holder 的原始 local/global 属性，但不改写原 JSON。算法取值继续传入自身的 fallback，不能用“取值等于默认”推测显式覆盖。Vec/Insets等源type4对象默认值按元素克隆、缓存并产生presence；EnumSet不是type4，默认值共享且读取不物化，显式global值也共享。Fixed resize每次真实赋新空constraints set，后续读取须保留调用者对该set的修改，直到下一次真实赋值。

本批新增原版 property helper 对照覆盖父 local 与全局 targets；新的 Box 全局请求覆盖 call 覆盖 constructor、padding/spacing 和字符串 false。复用已保存原观测，不需再采 Node：

```shell
python tests/fixtures/suites/next-native/compare_property_presence.py .local/micro-new-review/src tests/fixtures/suites/next-native/property-presence-request.json tests/fixtures/suites/next-native/property-presence-oracle.json .local/micro-new-review/property-comparison.json
python tools/reference/compare_next_mrtree.py --source .local/micro-new-review/src --provider box --oracle tests/fixtures/suites/next-native/property-presence/oracle.json --case box-selected-global --out .local/micro-new-review/box-global.json
```

调用前核实际 fixture 路径及相应 comparator 的 docstring。Box 原观测保留 terminate 的 TypeError，几何返回一致不能用于声明生命周期通过。径向继续使用 `compare_radial.py`，其 wire 一致与有效有限几何分开统计。

几何数字转换只核相关新helper，命令如下。输入的负零用原生`-0.0`表示；其它大整数字面值在进入Session前保持Python整数，以免测试自己提前转换而掩盖实现问题。比较内部数值和随后一次加法，并单列ID/业务数据保持控制，不运行layout。

```shell
python tests/fixtures/suites/next-native/compare_numeric_import.py .local/micro-new-review/src tests/fixtures/suites/next-native/numeric-import-request.json tests/fixtures/suites/next-native/numeric-import-oracle.json .local/micro-new-review/numeric-import.json
```

后续仍需完整 typed/global/递归调度、advanced diagnostics、layered NS/crossing 消费链、剩余算法和公开注册/包交付。这些小对照不构成整个算法或安装包验收。最终全量只在全部功能完成后执行。
