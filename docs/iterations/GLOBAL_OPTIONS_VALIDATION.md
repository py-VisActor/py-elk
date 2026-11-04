# 全局配置变更校验

13 批新增 `execution/global_properties.py`，接入私有 Session 的准备阶段。先按所选 metadata 注册集查找属性，再按原版 JSON 文本规则解析；未知、歧义和无效值被忽略，最后一次有效 alias 赋值生效。适用 targets 和 NO_OVERWRITE 由现有 reader 应用，False/0/空 EnumSet 仍是存在值。NODES 或 PARENTS 任一 target 都配置所有节点，不能自行加“必须已有 children”的限制。

结构化输入的文本规则在独立 Apache-2.0 `execution/json_text.py`：数组逗号无空格，object 逗号后有空格，数字键按 JS array-index 顺序，数字负零写 `0`，特殊字符按原 GWT escaping。它与最终 JSON wire 输出分工不同。正式公开 strict API 尚未切换。

八个新原版场景的首个 native 进程退出 1，唯一差异是原版观察器遗漏 Insets 的 `top_0` 投影。只重采该一个场景，再用保存 native 数据严格比较为 0 差异；未重跑八个 native 场景。另一个新 Box 整体递归的首次候选也因观察器未展开 Integer `value_0` 报差异，修正该唯一新原控后保存比较一致。两次实际退出 1 的记录保留，不能写成首次进程成功。

初始产品固定 142 文件检查点 `78198dcec93371af732dc609b05a6e82edf730a9c2e401e9547e59c25cb948fc`。独审又发现 5000 位数字字符串键不应交给 Python int 转换；143 文件 `40bdd44ada5212a6b574cf92756515420472db9194055bb5c9a07d0b4a74a710` 只加长度筛选，独立新原版与首次 Session 候选控制严格一致，旧八例不回绑新 SHA。V 代码独审为 `test-runs/20261104-HOST-13/V/global-options-code-review-01.json`，63 份文件绑定，接受范围包括两处观察器修正后的保存比较及真实消费者接线。批末归档保留原字节。

需要复核新变更时，从仓库根恢复新的目录；输出目录先建、输出文件不能已存在。开发阶段只选受影响检查。

```powershell
python scripts/iteration/next_workspace.py restore --destination .local/global-check-NEW --manifest migration/next-native/checkpoints/40bdd44ada5212a6b574cf92756515420472db9194055bb5c9a07d0b4a74a710.json
python tests/fixtures/suites/next-native/compare_global_options.py .local/global-check-NEW/src tests/fixtures/suites/next-native/global-options-request.json test-runs/20261104-HOST-13/root/global-options-original-01/oracle.json test-runs/NEW/global.json test-runs/20261104-HOST-13/root/global-options-original-02/oracle.json
```

独审还确认超大 Python 整数需要按原版 binary64 数字呈现为 `Infinity`/`-Infinity`。保留一个新候选真实 OverflowError，再只修数字分支，用一个新增原版/修后候选控制严格通过；旧八例和 Box 未重跑。此后源码固定为 13 批的 `1c086f0651c288c3086144c24cca544adebbb35aa82cd707ba36bdc676b1c4d7`，补充审查为 `global-large-integer-code-review-01.json`。本页上方 142/143 的执行和命令均保各自来源，不回绑新版本。

13 批原始文件现已可从 `references/next-native-evidence/13/test-runs/20261104-HOST-13/` 恢复，上方命令中的 `test-runs/20261104-HOST-13/` 可换为该归档前缀，无需重新执行原版。

比较脚本改变时复核保存数据即可，无需再次执行 Session 或布局：

```powershell
python tests/fixtures/suites/next-native/verify_global_options_saved.py test-runs/20261104-HOST-13/root/global-options-original-01/oracle.json test-runs/20261104-HOST-13/root/global-options-original-02/oracle.json test-runs/20261104-HOST-13/root/global-options-native-01/report.json test-runs/NEW/saved.json
```

原版重采使用 `global-options-probe.cjs`，第四个路径参数后可指定一个 case 名，只执行受影响场景。真实命令用 `validate_layout.run` 留存 command/stdout/stderr，并即时复制实际执行 checker/probe。这里不是完整 LayoutConfigurator 扩展接口或全量验收。
