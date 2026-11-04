# 外部组件与共享 enum 校验

14 批静态代码固定在 154 文件检查点 `3d6e0431fd40b03ba52b5dc28e420f222d6df9f47dc7fb122df16e6cfa8cf4ef`。普通布局 5 例中 4 例严格通过；首例保留 23 项内部 bucket/node 顺序差异。新进程的 native enum 分配策略与原 GWT metadata warmup 的分配顺序不同，不能填入原版 hash、改排序或放宽 raw gate。按对象身份的几何一致是独立见证，不是完整 conformance。

默认复核保存结果，不执行产品：

```shell
python tests/fixtures/suites/next-native/verify_external_components_saved.py test-runs/20261104-HOST-14/root/external-components-original-01/observation.json test-runs/20261104-HOST-14/root/external-components-native-01/report.json NEW_REPORT.json
```

以上原始文件位置以 [14 批归档](../changes/20261104-next-native-14.json)的 evidence 键及对应原 command.json 为准；删除本地 test-runs 后用 evidence.path 读取归档副本，不能猜文件名后重采旧例。新增实现或实际受影响 caller 才执行以下入口，输出路径必须全新：

```shell
python tests/fixtures/suites/next-native/compare_external_components.py PRIVATE_SRC REQUEST ORIGINAL NEW_REPORT
python tests/fixtures/suites/next-native/compare_enum_key_map.py PRIVATE_SRC ORIGINAL NEW_REPORT
python tests/fixtures/suites/next-native/compare_margin_no_port_order.py PRIVATE_SRC ORIGINAL NEW_REPORT
```

第一个入口是普通实际 ComponentsProcessor 的 strict gate；第二个明确为受控 hash 碰撞 primitive，不能作为 ordinary layout oracle；第三个仅检验适配器两处 IEEE 结合顺序。它们不读取旧输出作为运行时布局。对应 original probe、request、首次失败、修复后文件及 code review 全部随 14 批保存。

静态规则通过 `tools/reference/build_component_group_rules.py` 从已审源生成；必须提供 accepted/blockers/固定 packet SHA 和 EC01、EC05 的精确跨度批准。169 条规则仅保存在 Python 字面数据中，运行时不读 JS、reference 或 fixture。四个缺失批准负控已保存。

self-loop 新原版对象入口为 `compare_self_loop_foundation.py`、`compare_self_loop_post.py`、`compare_self_loop_port_side.py`，均在同一 fixtures 目录，参数见文件首行和本批原 command.json。已通过的 holder/pre/post/三策略不作为新会话启动回归；Restorer/Slot/Router 的新 caller 另采新证据。
