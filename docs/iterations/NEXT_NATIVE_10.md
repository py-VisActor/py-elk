# 10批执行 brief

承接09固定99文件与原始执行收据，保持root+A/B/V并行、单文件owner；工作区可领先固定快照，不能用最新SHA覆盖历史执行。

先行切片固定100文件`38a8700b46dfa191e82acd9c08741ef8c4250ca197dbc584e382c7a9afebddc7`：`model_order_import.py`已实现源批准的needs/flat producer与native token绑定。16个谓词、实际flat importer的过滤次序/计数和非空CB分组新原控均与候选严格0差异；完整geometry/endpoint callbacks仍待，不扩大到完整import验收。只在相关逻辑变更时选择下列对应对照，不重跑两个无关切片：

```shell
python -I tests/fixtures/suites/next-native/compare_model_order_producer.py PRIVATE_SRC tests/fixtures/suites/next-native/model-order-producer-oracle.json test-runs/model-producer-new.json
python -I tests/fixtures/suites/next-native/compare_model_order_groups.py PRIVATE_SRC tests/fixtures/suites/next-native/model-order-groups-request.json tests/fixtures/suites/next-native/model-order-groups-oracle.json test-runs/model-groups-new.json
```

| owner | 单写范围 | 下一个可验收交付 |
| --- | --- | --- |
| root | execution/options与新的import宿主薄桥 | 基于真实owner的needsModelOrder、节点/端口/边MODEL_ORDER producer与Integer token绑定，随后真实递归resolver/coordinator |
| A | layered counters/sweep/factory与router | 关闭local-swap/Type独审，获批flow/optimizer后接真实GraphInfo与controller；不以删除guard代替实现 |
| B | DisCo/Polyomino/RectPacking数学与内部holder | 用一个新完整DisCo请求先对照；将实际RP owner默认接宽度loader与preMicro首读，再接完整provider |
| V | 独立source/code与新增原对象对照 | 优先关闭一个可运行消费者；root分担B最短独立源叶，避免审核全串行 |

Integer的唯一cache由`integer_box_tokens.value_of_integer_box`提供。局部parse每次发生、全局parse一次；普通内部数字没有来源token时不猜身份。MODEL_ORDER和MAX没有缺省0，crossingMinimizationId的实际默认0才共享cache0。producer须在源规定的guard/过滤次序上赋值，节点NO_LAYOUT先过滤，端口/边MODEL_ORDER则先赋值再做各自过滤。

每次只执行该变更需要的新场景或必要代表性回归。已有成功对照与原观察保持旧依赖绑定；guard修复只加目标控制，不重新运行无关矩阵。归档与独审不执行产品；完整迁移功能完成前不跑最终全量，不改变完整算法验收分母与公开范围。

本批进一步减少串行审核：V集中审producer及大型flow/packing；A在等flow源批期间独立审root的Layered实际owner声明和生成器；B在等packing源批期间独立审root的resolver小闭包。产品仍保持单owner；审核者不得批准自己写的实现或改动对方产品文件。获批的数学继续优先实现，短审不阻塞真实controller/provider。每项审核保精确范围、原字节及执行身份，不以互审代替新增真实原控。

Owner默认表先行固定102文件`f1328759aa64e49d0f16250883150f75c1417db0d10da7ab7ef226502e3c7abb`。A源批只批准两个Layered owner的232声明，排除8个复杂值；静态表仍保留owner/symbol/实际Property与default的观察标签。标签不是Python身份，不能拿它们直接构造Integer/共享对象。`read_owner_scalar_property`必须明确owner与symbol，只处理标量/enum并保持既有typed值优先；结构化缺省须走另外的native factory规则。它不会自动选择算法owner或把metadata override注入实际Property。新scalar策略控制通过，代码交A独审；producer100的既有执行不重绑102。
