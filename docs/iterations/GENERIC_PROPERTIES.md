# 通用属性迁移接手

10显式owner入口：`read_owner_scalar_property(element,'LayeredOptions','EDGE_ROUTING')`读实际具名Property的缺省；缺省ORTHOGONAL不产生presence，随后Core读仍为UNDEFINED，显式用户值则优先。`options/_owner_data.py`目前仅有独审范围内的232声明，结构化EnumSet等不能通过scalar入口自动构造；观察identity标签也不能当Python身份。生成命令必须绑定独立accepted源审、approvedRows与每份依赖hash：

```shell
python tools/reference/build_owner_defaults.py --review test-runs/20261104-HOST-10/A/layered-default-owners-source-review-02.json --out NEW_OWNER_DATA.py
python -I tests/fixtures/suites/next-native/check_owner_scalar_policy.py PRIVATE_SRC test-runs/owner-scalar-new.json
```

只在对应生成器/缺省读取策略变更时运行；此表与薄入口不等于所有owner已消费，更不等于全部243项已完成算法接线。

09新增Integer桥：`integer_box_identity(element,name,declared_default_token)`返回实际parse/赋值token；`set_option(...,integer_box=token)`保存显式来源，普通数字赋值不猜身份。局部parse各自调用唯一valueOf cache，全局parse一次并按targets及局部优先应用；Snapshot浅复制保token，remove/无token覆盖清旧token。MODEL_ORDER没有默认0，crossingMinimizationId的实际owner默认才是cache0。新增矩阵复用下列原观察，只在桥的行为变更时执行：

```shell
python -I tests/fixtures/suites/next-native/compare_integer_provenance.py PRIVATE_SRC tests/fixtures/suites/next-native/integer-provenance-request.json tests/fixtures/suites/next-native/integer-provenance-oracle.json test-runs/integer-new.json
```

09共享增量已落：`set_generated_junction_points`使Fixed生成点进入typed存储；Box读取同一mutable链，export先has且非空才覆写。六个新原对象场景严格对照通过；真实Fixed请求亦通过，缺section首稿原报错保留。`PropertySnapshot.read_native`在新holder自身克隆/缓存实际默认，Core68 raw默认优先，保port.borderOffset=None与generic adapter0的区别。`session.read_native_property`将同一规则用于实际holder，padding15先物化后Micro及后续owner读8仍见同15。它们的后续caller接线与整数盒provenance仍在推进。

新脚本只在相关分支变化时执行，复用原观察；单case参数可避免重跑全部六例：

```shell
python -I tests/fixtures/suites/next-native/compare_junction_bridge.py PRIVATE_SRC tests/fixtures/suites/next-native/junction-bridge-request.json tests/fixtures/suites/next-native/junction-bridge-oracle.json test-runs/junction-new.json rematerialized
python -I tests/fixtures/suites/next-native/compare_snapshot_default.py PRIVATE_SRC tests/fixtures/suites/next-native/snapshot-default-oracle.json test-runs/snapshot-default-new.json
```

未知owner的结构化默认不能由`_native`猜测深复制：传实际factory并明确`materialize`规则；已知Core EnumSet共享、不制造presence，Vec/Insets/Chain等type4克隆并缓存到当前holder。读取实际对象用`get_native_property`或明确owner-default入口，provider-view列表用于算术表示，不作为可变链存储。Snapshot以当前presence判断重新物化的默认值，不能按历史remove标记排除。

08已将声明接入Session：243个登记类型，235个raw可构造；8个原factory缺失的OBJECT用`UNAVAILABLE_OBJECT_FACTORY`明确诊断，仍允许内部typed set/get。`parse_generic_mapping`仍是225标量独立入口；`element.parse_mapping`负责完整登记类型的显式输入。源68个真实Core标量默认在`_core_defaults.py`，不以metadata填未知owner。公开包仍9选项，完整owner默认和Integer盒身份尚待，不能据登记数量宣称全部属性消费完成。

新增position、bendPoints与junctionPoints向量链保留原分隔符、负零及合法奇数尾坐标忽略规则。链clone只复制容器、共享点对象；Core junction默认空链是type4，会在读取时缓存并产生presence。Node/Port几何与typed属性的最终桥接仍按09任务独立完成，不把顶层同名JSON字段当typed来源。

可重用单项脚本如下，仅在相应实现变更时选case/新输出路径：

```shell
python scripts/iteration/next_workspace.py restore --destination .local/property-review-new --manifest migration/next-native/checkpoints/fd785f4b0e86fc6eea6d1dfa53740f234756d9b0431b3fb735169e760fe9e302.json
python -I tests/fixtures/suites/next-native/compare_object_properties.py .local/property-review-new/src tests/fixtures/suites/next-native/object-properties-request.json tests/fixtures/suites/next-native/object-properties-oracle.json test-runs/property-chain-new.json chain-odd-tail
python -I tests/fixtures/suites/next-native/compare_property_snapshot.py .local/property-review-new/src tests/fixtures/suites/next-native/property-snapshot-request.json tests/fixtures/suites/next-native/property-snapshot-oracle.json test-runs/property-snapshot-new.json
```

`session.property_snapshot(element)`只复制实际present/适用global/已物化/内部computed字段，key map独立、值引用浅共享，不注册geometry、parent、ID或端点。`get`给provider标量视图，`get_native`保实际对象；`has/set/remove/copy`保持同一别名规则，`.values`保private key。Integer sidecar不猜Python int身份。09的`get_native_property`为真实mutable链薄入口，后续Snapshot缺省读取和junction单一存储桥另收据，不改绑08。

下文07的63项Session限制、parser未接入等描述均为历史固定阶段。

07批代码在私有检查点中增加`options/_generic_data.py`与`options/generic.py`。225项非OBJECT声明与显式解析器已独立源/代码审查，10个新原版`$parseValue`小样例严格对照通过。它尚未替换Session reader/配置器，现有Session schema计数仍63，正式公开仍9。不要据此宣称243项属性执行或整个算法完成。固定源码与82份原始证据见[07记录](../changes/20261104-next-native-07.json)。

`parse_generic_mapping(raw,path)`解析显式提供的STRING、BOOLEAN、INT、DOUBLE、ENUM、ENUMSET，返回typed值与拥有的原值；不选择运行默认值、不做算法调度、不读取references。算法名称在此按STRING处理，是否可执行由后续注册/协调器判断。现有有限数值及严格无效输入政策保留。OBJECT18单独接入，其中10个原factory可构造、8个原factory抛错，不能编造可用实现。

静态`METADATA_SCALAR_SPECS`的默认值只描述LayoutOptionData。Core或provider的真实Property/Property_2默认必须按调用者选择；Core路由UNDEFINED/components缺省，Layered覆写ORTHOGONAL/true，不能从旧受限解析器拷入Core。已审通用port adapter的borderOffset缺省投影0仍是独立adapter规则。

开发只选择受影响case，不重跑已通过的10例组。复用已存原观察，输出使用新路径：

```shell
python scripts/iteration/next_workspace.py restore --destination .local/generic-review-new --manifest migration/next-native/checkpoints/ab674459c82b0acbb082b4d1536afac46adecb62c6a7c5448a20bb724748fd15.json
python -I tests/fixtures/suites/next-native/compare_generic_scalars.py .local/generic-review-new/src tests/fixtures/suites/next-native/generic-scalar-request.json tests/fixtures/suites/next-native/generic-scalar-oracle.json test-runs/generic-single-new.json enum-ordinal
```

比较器以既有strict diff区分bool与number，集合按原enum声明顺序输出其成员视图。首版比较器用了Python相等运算，V对已保存raw做离线严格复核；保留原报告及旧SHA，修比较器不重启产品。最初请求中的错误选项ID及Node首败也保留，后续只修fixture拼写。

静态表由`tools/reference/build_scalar_catalogue.py`生成，输入是完整原始声明source包与明确批准225项的独审收据。生成器核同一source SHA、拒绝覆盖已有输出；生成操作不等于运行接入。需要修改生成器才重做生成；正常开发无需重新采Node元数据。

下一步接配置器的global targets/单次解析与真实Property reader。OBJECT vector-chain解析/clone、源Integer盒身份、Core/provider完整默认表分别源审，不用metadata默认兜底未知owner。最后接统一递归与公开注册/安装包；最终全量留全部迁移功能完成后。
