# 默认与自环完整链校验

15 批固定 162 文件 `8ef85d93156d168fc065414e7cbebc0070609bc76b5deb9671f5325cf8f92aa6`。默认 19 阶段与自环 23 阶段真实整调用已验；全算法/选项及完整 public 包仍待完成。每次运行保自己的源码 SHA，不回绑新文件。

新会话先纯核绑定，不跑布局：

```shell
python references/next-native-evidence/15/progress-bindings/check_progress.py
```

机器计划推进后用最新批入口；历史结果仍保存，不将计划退回。恢复本批：

```shell
python scripts/iteration/next_workspace.py restore --destination .local/review-15-new --manifest migration/next-native/checkpoints/8ef85d93156d168fc065414e7cbebc0070609bc76b5deb9671f5325cf8f92aa6.json
```

重算保存 JSON，无产品执行：

```shell
python scripts/iteration/check_layered_saved.py --request REQUEST.json --original SOURCE_OBSERVATION.json --candidate NATIVE_RESULT.json --out NEW_REPORT.json
```

默认不投影。审查 [ADR0001](../decisions/0001-native-contract.md) 与 [ADR0010](../decisions/0010-native-object-identity.md) 后才追加 `--project-reference-shape-hashes`。仅限原输入无同名字段、身份/数组路径匹配、Source 新增有限整数且 native 不补造的 shape `$H`；业务及嵌套字段严格比较。始终读 rawStrict、adaptations、violations。此脚本不证明执行版本或输入保留，需另核原 collector、manifest、命令/日志及独审。

| 范围 | request / original 目录 | native 目录 |
| --- | --- | --- |
| 默认 19 阶段 | `test-runs/20261104-HOST-14/A/layered-default-full-original-01` | `test-runs/20261104-HOST-15/A/default-full-native-02` |
| 注册/RGE 新 caller | 复用上一行唯一原请求 | `test-runs/20261104-HOST-15/root/layered-registry-native-02` |
| 自环 23 阶段 | `test-runs/20261104-HOST-15/A/layered-self-loop-full-original-01` | `test-runs/20261104-HOST-15/A/self-loop-full-native-01` |

文件分别为 `request.json`、`observation.json`、`result.json`。本地 test-runs 缺失时，从 [15 归档](../changes/20261104-next-native-15.json) evidence 键读取不可变副本；不要重采旧 Source。原 collector 有固定已存在输出目录，仅供审阅，不能直接重运行。

产品或真实 caller 有变化才执行新输出：`check_layered_registry.py PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT`，或新增 collector 并固定 source manifest。运行时仅 Python，不读取 JS/reference/fixture。

其它新增入口均在 fixtures/next-native：`compare_cgraph.py PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT [CASE_INDEX ...]`、`compare_cgraph_locking.py PRIVATE_SRC ORIGINAL NEW_REPORT`、`compare_spline_math.py PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT`。原始 Source、首败/修复、执行过的 checker/probe 在 evidence 保存。准备态 router 的 geometryStrict 与原错误 monitor 导致的 rawStrict 不同，不能升级为 raw 全字段通过。

不启动 full、旧平台矩阵或已过 NS/BK/三模式/primitive 回归；全部迁移功能完成后再全量。
