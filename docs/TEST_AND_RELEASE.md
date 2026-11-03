# 测试、证据与发行门禁

具体迭代与逐轮验收配方V0–V6见 [ITERATION_PLAN](ITERATION_PLAN.md)。现有工具用法仍以 [LAYOUT_VALIDATION](LAYOUT_VALIDATION.md) 为准；未来profile/阶段suite/算法矩阵/候选验收脚本按各轮交付后再登记为可执行。

## 当前可运行范围

```shell
python scripts/check.py --out test-runs/start-01
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python scripts/upstream.py fetch
python scripts/upstream.py check
python examples/show_scope.py
```

一键检查不加载 Node/JVM，覆盖结构/分母、布局比较器、官方快照和负控制；来源工具首次下载需要 Git/网络。
实际 graph capture/candidate/compare/replay、几何与确定性已落地，命令、协议、适用条件见 [布局校验手册](LAYOUT_VALIDATION.md)。
`check.py --with-reference` 可追加真实官方重采；元数据见 [tools/reference](../tools/reference/README.md)。
没有 Python 算法，工具通过不产生 Python 布局或全量契约兼容结论。
本地骨架 wheel 可用于检查打包/导入，不能上传占名或据此声称布局可用。

## 分层体系

| 层 | 对照与独立断言 |
| --- | --- |
| 来源/范围 | Git/npm identity、源码/发行 SHA、默认/筛选元数据、完整 case/assertion 来源，无被删除分母 |
| API/模型 | 参数/JS 值、ID、字段保留、默认/覆盖/继承、错误/副作用和 JSON 结构 |
| 阶段/几何 | phase/processor 顺序、拓扑、方向/约束、端口归属、容器、section/label box |
| 坐标/数值 | 所有节点/端口/标签/section 数值路径，exact 与既定 `1e-6/1e-9` profile 分开报告 |
| 算法/选项 | 全 12 算法、243 选项及策略/适用组合，不以抽样数量替代覆盖 |
| 稳定/资源 | seed、模型顺序、实例污染、并发/取消/关闭/恢复、规模/深度/时间/内存 |
| 集成 | py-mermaid 转换→新引擎布局→回填/绘制，旧 ELK 版本不作兼容门禁 |
| 部署/发行 | Python/Windows/Linux 矩阵、同一新候选、仓库外 `-I`、无 Node/JVM/浏览器/参考源码运行 |

原始输入、原始官方输出/错误、规范化结果、完整差分和人工辅助图分开存放。
数组模型顺序、ID、未知业务字段、端点/sections 不做静默归一化；数值差异不通过全局阈值扩大、坐标平移或删图隐藏。
必须有故意破坏字段、几何、默认值、seed 和错误的负控制；Python 同配置重复确定性与跨实现误差分别验。

每个 run 使用新目录，写实际 argv/cwd/退出码、版本/环境/输入/source/包 SHA、报告及限制；失败原样保存。
源码改变后重跑相关检查；旧报告只对其记录的源/环境有效。目录、占位类型和快照文件均不是实现证据。

## 发行

基础正式包先按 [FIRST_RELEASE_SCOPE](FIRST_RELEASE_SCOPE.md)完成M3功能、M4独立候选和M5上传/下载复验；
py-mermaid集成属于后置独立I阶段，不是基础包发行门禁。

当前没有发行许可决定，没有算法实现，故不发布占位包。计划首版为正式0.1.0，准确公开基础算法/选项/平台与剩余分母。
候选还需源码许可/NOTICE、名称可用性、wheel/sdist/METADATA/类型/文档、干净安装和真实布局验收。
commit/push、实际 CI、Release/PyPI 及重新下载核 SHA 各自记录，按当次授权执行。
