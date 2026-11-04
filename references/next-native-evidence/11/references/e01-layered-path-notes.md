# E01：固定layered执行路径审计

状态为固定发行物的来源/路径调查，Python布局实现仍为零。机器证据见 [layered-default-path.json](layered-default-path.json)，其中每条源锚点包含source ID、符号、行范围和span SHA。
Java/Xtend精确提交与生成worker的对应关系仍由来源lane调查；本页确认生成发行物内的实现身份，不据此声称Java版本已经闭合。

## 实际查到的入口与默认路径

锁定elkjs0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`。
`src/js/elk-api.js`接受构造默认及调用级参数；调用级layoutOptions是替换关系，空对象同样替换。
Java入口的optsToCfg使用NO_OVERWRITE；局部图属性和全局参数的作用方式需要保留，不能笼统地逐键合并所有配置。
Node默认包装选择minified FakeWorker；本次原始bundled参考未修改。开发探针另通过官方elk-api的workerFactory运行同发行物PRETTY worker。

JSON导入/配置 → RecursiveGraphLayoutEngine → LayeredLayoutProvider → ElkGraphImporter → GraphConfigurator/AlgorithmAssembler → components拆分 → 每组件处理器链 → components合并/root resize → ElkGraphLayoutTransferrer → JsonImporter回填原始JSON。
每一步的实际生成符号和固定源码位置见JSON的entryPath；原始Java facade和生成worker身份分开记录。

五个默认阶段为：

| 阶段 | 默认选项值 | 实际生成类 |
| --- | --- | --- |
| P1破环 | GREEDY | GreedyCycleBreaker |
| P2分层 | NETWORK_SIMPLEX | NetworkSimplexLayerer |
| P3层内排序 | LAYER_SWEEP | LayerSweepCrossingMinimizer，主实例monitor为BARYCENTER |
| P4节点定位 | BRANDES_KOEPF | BKNodePlacer |
| P5边路由 | ORTHOGONAL | OrthogonalEdgeRouter |

## 首条真实单边路径需要19个调用槽位

缺省方向解析为RIGHT的两节点单边、链、菱形与环，实际观测到以下19次调用：

1. EdgeAndLayerConstraintEdgeReverser
2. GreedyCycleBreaker
3. LayerConstraintPreprocessor
4. NetworkSimplexLayerer
5. LayerConstraintPostprocessor
6. LongEdgeSplitter
7. PortSideProcessor
8. PortListSorter
9. LayerSweepCrossingMinimizer（BARYCENTER主实例）
10. LayerSweepCrossingMinimizer（TWO_SIDED_GREEDY_SWITCH额外实例）
11. InLayerConstraintProcessor
12. LabelAndNodeSizeProcessor
13. InnermostNodeMarginCalculator
14. BKNodePlacer
15. LayerSizeAndGraphHeightCalculator
16. OrthogonalEdgeRouter
17. LongEdgeJoiner
18. EndLabelSorter
19. ReversedEdgeRestorer

“被调用”不等于处理器对该输入做了非空工作。Node-only JSON也会经过port、label/尺寸和margin相关处理器；首版不支持显式ports/独立labels，不代表可以忽略真实默认链的内部处理。
同一个LayerSweepCrossingMinimizer类出现两次，须用构造配置和monitor区分，不按类名去重。默认greedy switch为TWO_SIDED，flat情况下需非interactive、非OFF，且threshold为0或大于配置时节点数；默认threshold为40。
JSON的processorCatalog为本轮实际见到的23个不同类记录constructor、process派发和process实现的完整生成代码span。它仍不是这些方法全部传递helper依赖的Java来源闭合证明。

## 默认值和样例显式配置分开记录

自编的两节点默认探针仅显式选择layered，节点给定40×30；其他九项中的参数不显式设置。

| 选项 | 固定代码默认/本次默认探针 |
| --- | --- |
| algorithm | core属性无固定值；未配置的非空节点在layered已注册时回落到org.eclipse.elk.layered |
| direction | 属性为UNDEFINED；依据aspectRatio选择RIGHT/DOWN，本次实际解析RIGHT |
| padding | 四侧12 |
| spacing.nodeNode | 20 |
| layered.spacing.nodeNodeBetweenLayers | 20 |
| separateConnectedComponents | layered缺省true |
| spacing.componentComponent | 20 |
| edgeRouting | layered覆盖core的UNDEFINED为ORTHOGONAL |
| randomSeed | layered缺省1；0走非固定种子构造路径，非零走显式种子构造路径 |

现有25例套件中的很多请求显式指定seed=7、层间距30、组件间距40；这些值是测试输入，不是ELK默认值。
JSON options记录默认来源、metadata type/targets和解释；构造/调用替换与局部覆盖记录各自源锚点。全部配置分支与宿主适配仍需E02冻结。

## 23例真实探针与不可混用的证据

对现有套件22个成功布局请求，以及自编单边默认请求，分别启动三个干净进程：原bundled、原PRETTY、内存插桩PRETTY，共69次布局。
三种执行都显式覆盖`logging=true`、`measureExecutionTime=false`，实际layoutArguments保存在每个报告；request SHA指原请求字节，不包含这项额外覆盖。
这些是派生研发调用，不能写成原golden参数完全相同。原参数下的25例V1重采/确定性仍由独立capture/replay验收。

所有23例均满足：PRETTY与bundled的完整result exact相等；插桩与原PRETTY的完整result exact相等；实际调用前后名称配对；调用顺序与公开logging的配置槽位一致。
完整result比较保留logging和私有字段，未删坐标、未平移/缩放、未排序模型数组。共记录451次processor-before和451次processor-after。
这不是同一引擎重复三次的确定性测试，也不是Python实现验证。

| 输入类别 | 本轮实际调用次数 |
| --- | --- |
| 空图 | 0，未进入组件processor循环 |
| 普通相连图/单点子节点/单边/链/菱形/环 | 每组件19 |
| 非RIGHT方向 | 通常21，增加方向前后GraphTransformer |
| 自环 | 23，增加四个self-loop处理器 |
| 两个分离组件 | 38，每组件19 |

上述数值只描述本轮列出的具体请求。metadata/策略/图属性可添加其他处理器，不能泛化为所有ELK输入的固定数量。

## 复现方式

该开发工具校验全部锁定npm文件SHA，原发行文件不写入；只在内存编译PRETTY副本时添加配置和processor循环前后hook。
每次hook要求唯一原文锚点，否则失败；输出保存原worker SHA、精确match/replacement规则、原始结果、调用事件、日志和全部子进程argv/退出码。
当前domain限定为平面root/children、无显式ports/labels、单源单目标extended edges，不覆盖hierarchy-aware执行。

```shell
python scripts/upstream.py fetch
node tools/reference/trace_layered_path.cjs .local/npm-elkjs/package tests/fixtures/validation/requests/layered-diamond-right.json test-runs/new-path-diamond
```

输出目录必须不存在。完整原始本轮产物位于`test-runs/20261103-E01-01/B/trace-*-final`；公开JSON保留逐例观察、原始report SHA和重建输入的信息。
22个原请求已在tests/fixtures/validation/requests版本化；自编默认请求原始UTF-8字节嵌在JSON的defaultProbeRequest中，读取后写到新文件即可使用相同工具重采。

后续重点：E02明确宿主/输入副作用和私有字段profile；E03内部模型应服务于真实默认链；E04先按已核实组件移植，不把19槽位缩写成五个空阶段。
