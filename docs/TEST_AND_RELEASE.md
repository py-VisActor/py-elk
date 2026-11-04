# 测试、证据与发行门禁

当前执行[完整实现后的统一校验与集中修复](FULL_NATIVE_IMPLEMENTATION.md)。E04–E09 运行收据均只认证其冻结历史包；当前完整源码使用新的 API／算法／属性／平台和安装验证。最终全量入口已加入当前完整 API 和 196 模块检查，不以历史收据认证新包。

用户最新规则：持续goal完成剩余E09–E21迁移；[变更校验政策](VALIDATION_POLICY.md) 优先。开发只运行变更相关校验，全部功能完成后再统一全量；下文旧逐轮full要求不再作为当前收口前置。

E09 增加真实诊断来源、首版声明分支及当前同一wheel的 geometry/API/newcoverage 强连接。完整离线入口为35步，含官方重采为54步；旧31/48步仅对应E08历史。来源、静态声明和实际收据分别验证，计时仅使用明确的源生成叶策略，业务同名字段 exact，旧profile不放宽。E04–E08旧包只认证历史；完整平台/性能矩阵仍在E10，正式发行门不提前通过。当前命令见 [LAYOUT_VALIDATION](LAYOUT_VALIDATION.md)、来源与声明见 [E09手册](E09_BRANCH_COVERAGE.md)。

具体迭代与逐轮验收配方V0–V6见 [ITERATION_PLAN](ITERATION_PLAN.md)。现有工具用法仍以 [LAYOUT_VALIDATION](LAYOUT_VALIDATION.md) 为准；未来profile/阶段suite/算法矩阵/候选验收脚本按各轮交付后再登记为可执行。

当前E07的实际72输入/新wheel验证、阶段定位与收据导出见 [E07手册](E07_DIRECTIONS_COMPONENTS.md)。离线入口检查当前包字节/METADATA并运行真实源码对照；E04/E05/E06原wheel/声明分别用相应`validate_e0N_runtime.py --historical`单独验证，不能作为当前安装证明。可用`python scripts/check_fresh_copy.py --out test-runs/fresh-01`检查Git过滤后的无缓存副本。

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
离线入口包含真实Python受限切片对保存的官方观察，不等于全量算法/API兼容。[E04手册](E04_NATIVE_SLICE.md)提供真实已安装wheel同suite对照入口、源码/许可/安装身份核对及默认seed policy。
当前本地0.0.1a0开发wheel已执行真实布局，正式候选仍须完整基础范围、平台/性能/资源与发布许可验收。

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

当前没有发行许可决定，算法只完成实验路径切片，尚未正式发布。计划首版为正式0.1.0，准确公开基础算法/选项/平台与剩余分母。
候选还需源码许可/NOTICE、名称可用性、wheel/sdist/METADATA/类型/文档、干净安装和真实布局验收。
commit/push、实际 CI、Release/PyPI 及重新下载核 SHA 各自记录，按当次授权执行。
