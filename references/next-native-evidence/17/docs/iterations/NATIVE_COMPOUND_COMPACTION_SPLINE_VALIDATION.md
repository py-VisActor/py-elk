# 17 批变更校验入口

先读机器计划的 `parallelPreparation.progressRecord`，再读取其中 checkpoint、`reviewScopes` 和证据映射。当前仍在私有迁移目录，正式 `src/pyelk`、完整算法分母和发布状态未因此改变。

本批覆盖真实 connected compactor、四个层级端口处理器、完整 compound、通用方向和 Spline P5/Final。prepared working graph 的几何由测试提供；完整 JSON caller 的几何由真实导入、阶段执行和导出产生，两类证据分开记录。每次执行绑定自己的冻结源码，后续 getter 修复不重新认证先前的运行。

新会话优先运行记录旁的纯绑定脚本，不默认启动产品：

```powershell
python references/next-native-evidence/17/progress-bindings/check_progress.py
```

需要重新观察时先确认实际代码发生了影响对应对象的变化，再创建新的输出目录。`scripts.validate_layout.run` 会写入 command、stdout 和 stderr，调用者负责先创建唯一目录。保留首次失败及实际执行脚本；观察器问题可以从保存结果重新判定，不能把旧运行的源码 SHA 换成当前版本。

完整 compound 新样本的原始比较保留七处 Source 新增形状 `$H` 差异。既有浅层投影仍保留四处嵌套差异；新增的显式树投影只沿实际 `children` 关系处理已验证的 Source 新增整数形状字段，不遍历业务字典。复核保存结果：

```powershell
python scripts/iteration/check_layered_saved.py --help
```

按帮助提供保存的 request、stock original 和 native result，并显式选择 `--project-reference-hierarchy-shape-hashes`。默认不投影；旧 `--project-reference-shape-hashes` 保持浅层行为。报告同时保留原始差异、适配记录、前置条件违规和最终差异。业务 `$H`、原输入已有字段、坐标或数组顺序不允许随之归一化。规则见 [ADR 0014](../decisions/0014-saved-hierarchy-shape-hashes.md)。

connected compactor 的新增控制含真实上游 `returnVal` 未定义故障：ReferenceError 发生在第一段内部边几何计算之后、加入凸包角点之前。故障对象证明失败路径，不能计作成功布局；另有不含该内段的真实成功对象。四 side 默认值、Pair 字段组合 hash、共享 connections 默认集合及三种 placer 调用均有独立新对象。旧 external 组件的 23 项身份相关顺序差异仍待处理。

Spline 的 foundation、排序、P5、Final 和完整 JSON caller 分别验收。Final 的新 prepared caller 不代表公开 SPLINES 全面通过；真实原版抛错的 JSON 请求保留失败状态，候选在原版正本门禁前停止时必须报告产品调用数为零。Polyline driver 若只有草稿和源批准，仍标为不可执行，不由 snapshot 文件数推定完成。

开发仅运行变更校验。所有迁移功能完成后统一全量验收；本批不自行提交、推送或发布。
