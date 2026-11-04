# ADR 0015：MrTree 第二次 Walker 调用环

状态：接受；只适用于检测已确认不可能返回的调用依赖，不改变正常布局算法。

固定 elkjs 0.12.1 的 MrTree BFS 在共享子节点非树输入上可能重复访问节点。邻居构造会生成 `RIGHTSIBLING` 自引用。源第二次 Walker 递归依次调用首子节点和右兄弟，最终抛出 `RangeError: Maximum call stack size exceeded`。原生对应的显式帧栈没有语言递归上限，会无限运行。由调用方超时停止不能视为算法异常行为已对齐。

原生第二次 Walker 现在使用进入／离开帧，并按对象身份维护仍未返回的活动调用集合。节点在该集合中重入时抛出 `RecursionError: Cyclic sibling/child dependency in MrTree second walk`。离开帧才删除活动标记，因此正常返回后对共享节点的重复访问仍保留。不使用全局去重，不按节点数、迭代次数或 JavaScript 栈大小设置限制；第一遍、BFS 和邻居生成不变。

这是明确的宿主异常映射：JavaScript `RangeError` 对应 Python `RecursionError`。异常类型、文案、栈和触发时刻不宣称相同。原版原始观察保留，不能计为正常几何通过。

当前修复源码 SHA 为 `4cb5f83db016783e12a5c79dc25676a1ecd9d489c9f82dd74a961a7dc8915813`。受影响校验包括原挂起输入的真实公共 API 返回、正常 MrTree 与已有原版保存数据比较、共享子节点返回后两次访问、1500 层合法链，以及新 wheel/sdist 实际安装。原生前后基线比较仅用于防止修复改变合法行为，不代替原版数学证据。

可重核 [源码差异与审阅](../releases/evidence/runtime-repair/review.json)、[异常路径](../releases/evidence/runtime-repair/cycle-termination.json)、[合法公共输入](../releases/evidence/runtime-repair/valid-tree-regression.json)和 [候选差异](../releases/evidence/runtime-repair/candidate-delta.json)。

受影响的合法重访／深树检查可独立运行：

```shell
python tests/fixtures/suites/full-option-effects-nonlayered/check_mrtree_repair.py --before docs/releases/evidence/runtime-repair/mrtree-before.py --source src --out NEW_DIRECTORY
```

发行门禁会重新读取真实观察、请求、命令和源码指纹，不只接受汇总的 `passed` 值：

```shell
python scripts/iteration/release_readiness.py --source-only
```

如果发行尚未最终就绪，该入口应拒绝放行，而不是略过候选状态。
