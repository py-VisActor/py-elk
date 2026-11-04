# 共享运行层定向校验

[06批记录](../changes/20261104-next-native-06.json)固定87文件源码、389份原始证据及各自执行SHA。它是私有迁移进度，公开API、安装包和完整算法尚未验收。开发中按改动选择单项；全部迁移功能完成后再全量。

先在仓库根恢复到新目录。需要精确复现本批源码时指定固定manifest，不使用持续变化的最新工作区：

```shell
python scripts/iteration/next_workspace.py restore --destination .local/host-review-new --manifest migration/next-native/checkpoints/bf228d35396eab22d9701533c84a651e401ec10f434ee33affc4ac5c5a58b2d7.json
```

`tests.next_native.test_micro_state`中的每个方法会自行恢复当前检查点到临时目录、在独立解释器中导入。只选本次受影响的方法，例如：

```shell
python -m unittest tests.next_native.test_micro_state.PrivateMicroStateTests.test_resize_constraint_set_mutation_survives_reads_until_next_actual_assignment -v
```

| 实际改动 | 对应单项方法后缀/原始比较器 |
| --- | --- |
| margin-only | `test_margin_only_computes_overhang_without_sort_resize_or_label_placement` / `compare_margin_only.py` |
| host entropy | `test_unseeded_host_entropy_is_separate_and_has_exact_half_open_boundaries` |
| Spore十项属性 | `test_spore_properties_preserve_enum_ordinals_targets_false_and_actual_defaults` |
| DOUBLE存储 | `test_double_defaults_and_computed_storage_use_binary64_without_weakening_finite_input` / `compare_double_properties.py` |
| identifier文本 | `test_source_identifier_text_does_not_change_native_typed_identity_or_raw_ids` |
| provider调用 | `test_underlying_provider_uses_same_session_and_only_resolved_calls_create_subtasks` |
| label minimum | `test_label_minimum_uses_parent_adapters_and_does_not_commit_shape_changes` |
| EnumSet共享 | `test_source_enumset_defaults_and_explicit_global_values_keep_distinct_sharing_rules` / `compare_enumset_identity.py` |
| Spore注册 | `test_new_spore_provider_registration_reuses_real_margin_only_and_shared_objects` |

比较器在`tests/fixtures/suites/next-native`；参数见各文件docstring。复用已保存原始oracle，输出到新路径，修单分支时传单case参数。`compare_spore_providers.py`对应`spore-providers`中的两个新请求。不要为改一个共享属性而重采所有Node样例或重跑旧算法组。

margin-only只计算真实child margin，不排序、不调整尺寸、不放置标签，也不调用完整NodeMicro。minimum查询只在有真实parent时使用parent adapter，执行`process(false,true)`，其中true表示忽略inside port labels；不能解释为只计算minimum或把暂存布局提交回节点。共享provider invoker保留同一Session/节点与计算属性，仅找到可调用body后创建子monitor；未知可选provider跳过，已知但尚未集成的body明确报错。

原Math.random与原生系统熵的映射见[ADR0012](../decisions/0012-native-host-entropy.md)，不承诺V8随机轨迹。标识符文本见[ADR0013](../decisions/0013-source-identifier-view.md)，不能据文本相同合并int与str身份。DOUBLE区分原数值负零经source字符串化后的正零，以及原字符串`"-0"`的负零；finite输入限制保留，旧公开九选项边界不变。

EnumSet默认共享、global解析一次共享、local分别解析；Vec/Insets按源type4规则复制。Fixed每次resize赋新的空constraints set；赋值后修改集合，再读取必须保留内容和身份。首版错误的truthiness重清空分支及其失败执行已保留，只对该新失败leaf复验。

243项元数据采集位于`references/next-property-schemas-sources.json`，225项标量/enum/enumset与18项OBJECT的声明已观测；10个OBJECT factory可构造，另8个原版本身抛错。当前运行schema仍63项，不能把采集数量作为支持数量。该完整registry后续独审与接入。

07批先行采集补充了`references/next-property-runtime-defaults-sources.json`：22个真实静态owner、229个唯一属性ID及原对象身份。metadata声明、Core默认、provider覆写分别记录；例如Core路由为UNDEFINED，Layered覆写ORTHOGONAL。14项未找到静态assigned Property的字段不能臆造owner；LayoutOptionData本身也是IProperty，其metadata默认视图仍可单独读取。该新source包尚待分块独审，不计入06执行验收。

需要因声明采集器本身变更而重新采集时，以下只运行原版元数据和属性初始化，不执行布局。正常开发应复用已保存观察，而不是例行重采：

```shell
node tools/reference/capture_option_schemas.cjs .local/npm-elkjs/package references/metadata/options.json test-runs/metadata-new.json
node tools/reference/capture_property_defaults.cjs .local/npm-elkjs/package test-runs/property-defaults-new.json
```

两个输出路径都必须不存在；父目录应先创建。采集器核固定worker字节，保留原PID、参数、执行日志与SHA；不同运行的identity编号仅在本次观察内比较，不能跨进程当作业务ID。

归档绑定校验仅检查本批文件字节、固定checkpoint和声明边界，不执行产品布局；不能把归档通过当作新代码已运行。失败日志、生成hash差异与原terminate异常均保留，旧通过证据不改绑新SHA。
