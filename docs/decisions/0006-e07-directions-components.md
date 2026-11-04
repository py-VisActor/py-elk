# ADR-0006：四方向、组件和基础选项

状态：source-review-in-progress，revision1，scope id `E07-ADR0006-revision1`。当前公开域仍E06；本文件冻结E07协议，未批准组件不得进入机械移植。
run=`test-runs/20261103-E07-01`；1845份起点已备份，597项基线通过。固定elkjs0.12.1 commit `624ae90aa37110033a8af59c5ccbb292708b4317`、worker SHA `275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`。

## 输入与规模

拟支持flat、0–8原始节点、最多28原始边的有向多重图，允许任意弱连通分量、孤立点、环/自环/平行边。RIGHT/LEFT/DOWN/UP及缺省UNDEFINED，ORTHOGONAL，给定有限非负尺寸和各spacing/padding上界1000000，非零signed32 seed或来源default1。保持E04–E06全部raw输入与oracle、25master及12/243/8完整分母。
九项基础选项按已有schema，构造默认由调用layoutOptions整体替换，再由root local覆盖；每scope别名重复仍拒绝。显式padding需官方importer接受的字符串。child-local padding在独立source def-use和探针确认后限定开放；不泛化其他child选项。高级策略、公开ports/labels、嵌套、初始几何、seed0、其他routing不因本轮自动支持。
NS在每个原始弱component上执行，最大规范化rank仍需来源证明不超过7。全图总规模的粗界继续为176 work nodes、196段边、392端口，普通路由私有segment每层边界56；分量拆分不复制原node/edge身份，只改owner。不得把观察到的最大值当理论上界。

## 方向协议

默认congruency为READING_DIRECTION。真实factory的命名须原样记录：PRE创建TO_INPUT_DIRECTION，POST创建TO_INTERNAL_LTR；LEFT pre/post为mirror-X，DOWN为transpose，UP pre为mirror-Y→transpose、post为transpose→mirror-Y。RIGHT不新增这两次调用，空root不执行processor。
导入按原方向创建实际隐式ports：输出E/W/S/N，再由pre归成内部E/W。DIRECTION始终保留原值，不临时写RIGHT来绕过guard。transpose/mirror按真实源处理node/port pos/size/anchor、graph size/offset/padding、minimum/label padding/junctions和相关标记；不能用最终画布旋转替代。是否改变margin/layer size与属性presence由独立源审确认。
A唯一提供`direction_preprocessor`/`direction_postprocessor`、`resolve_direction`/`from_direction`和`get_node_labels_padding`/`get_node_size_minimum`。其他模块只能调用已批准getter，不能克隆第二套可变默认。

## 分量协议

全图prepare一次，生成global PROCESSORS/GRAPH_PROPERTIES和一个JavaRandom，再split。true按原node顺序与有序port邻接DFS；component浅共享RNG/flags/processor对象，padding独立拷贝。全局有selfloop时所有component都跑loop4；方向pre/post也来自同一全局配置。
false直接返回原图本人，不DFS、不packing。NS仍需按真实connectedComponents规则处理多个private NS及previous-layer filling，不能仅删除connected guard。
B唯一提供`split_components`、`finish_component`、`combine_components`、`resize_graph`。combine按真实stable面积排序及row placer，ASPECT_RATIO默认实际double为`1.600000023841858`；component spacing是独立值/default20，额外spacing.baseValue不在本域。resize只按实际defaults/flags执行；EnumSet注册clone回调不代表getDefault会进入Cloneable分支，须绑定type表和hasProperty前后事实。
公共路径为raw import→split→每component processors→finish→combine→resize→geometry export。原始模型顺序由origin回填，不排序public数组。只有root padding最终加一次，内部moveGraph的offset与junction顺序按源执行。

## 审查、验证与边界

来源固定33组件：A4、B3、R26。每项绑定完整E06独立基审、真实entry/helper、guard/默认值、typed依赖、source context、版本化review及许可；旧RIGHT/单component假设不能直接继承为新事实。原source artifact和review不可回写。
正式suite先拟72=22/25 master正例+50项目变体，原3error明确排除而不计成功；新压力场景可加不可删。两端同输入各至少3次，原E04/05/06同新wheel回归，-I/空PATH/全部Python与许可/METADATA一致。E06包与声明先封历史，历史不能认证新代码。
几何拟新增显式`layerFrame=independent-components-v1`和`rankSeparation=default-layered-components-v2`，只从原请求及其有效选项推断，不能从候选坐标/改端点制造豁免。true的不同组件不猜为同层，false不能用此豁免；仅DAG可达pair或严格simple ring引用rank来源lemma。所有overlap/root bounds/section/端点/路由及既定1e-6/1e-9容差继续保留。E06旧marker规则不改。
同源码Windows/WSL/Git过滤副本完整检查，稳定屏障后建同一新wheel，完成四部分复盘并将改进写E08 brief。完整算法数仍0，完整API/生命周期、发行许可、精确外部Java build及正式0.1.0发行另行验收，不含py-mermaid集成。
