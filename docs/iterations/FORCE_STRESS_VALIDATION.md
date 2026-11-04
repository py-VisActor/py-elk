# Force / Stress 定向验证

当前为私有真实provider实现，正式src、公开注册和安装包尚未切换。Force包含EADES/FRUCHTERMAN_REINGOLD、同一RNG跨组件、真实FGraph/label/bendpoint与组件拆合；Stress包含真实Force初值分支、Dijkstra队列与顺序majorization。来源与逐块独审见`references/e18-force-stress-sources.json`。

首次四个独立原官方请求覆盖Force两模型、加权/ports/labels/分量，以及Stress interactive X/fixed/显式边长和noninteractive Force-init Y。随后只新增一个interactive默认inline label请求。五例有限几何与业务字段严格一致，每例实际调用generic micro一次；20项生成`$H`差异原样保留，原Node terminate异常不作为生命周期通过。

Stress metadata的inline支持声明为true，但两条真实运行分支保持共享属性默认false。独立原观察明确区分两种公式，Root已移除错误的运行默认注入，并只核对应一个typed方法。不要将metadata支持描述等同于运行属性覆写。

恢复到新目录后，按当前变更选择单例：

```shell
python scripts/iteration/next_workspace.py restore --destination .local/next-provider-review
python tests/fixtures/suites/next-native/compare_force_stress.py .local/next-provider-review/src tests/fixtures/suites/next-native/force-stress-first/oracle.json .local/next-provider-review/force-eades.json force force-eades-weighted-labels
python tests/fixtures/suites/next-native/compare_force_stress.py .local/next-provider-review/src tests/fixtures/suites/next-native/stress-inline-default/oracle.json .local/next-provider-review/stress-inline.json stress stress-interactive-label-default
```

比较器验证原始请求与观察SHA、实际私有导入路径、源码执行前后、输入拥有权、micro调用和全部strict差异，另列wire一致性及finite几何。已保存观察只由开发比较器读取，产品运行不读取fixtures/references。修某一分支时只选该例；不重采Node、不重放无关四例或平台矩阵。

五个小正本不代表整个Force/Stress域、243选项、所有诊断/递归或独立Python包验收。未解析选项、公共调度和正式发行仍按机器计划推进，全部功能完成后再全量。GWT PriorityQueue窄支持归属已记录于私有`NOTICE-GWT-Ports.md`，不是完整Java运行时移植。
