# 递归协调器变更校验

11 批已归档至 `docs/changes/20261104-next-native-11.json`，固定 126 文件检查点 `e482a49e1453cc9c866947053c1ee539769df160badef1e280f6be6d388afd9a`。Topdown 修正后的实际执行、共享池新调用和 14 个本地导入 DTO 均已通过并完成独审；下方“首次失败”保留故障定位经过。下一步按 [12 批 brief](NEXT_NATIVE_12.md) 继续，不能把私有调用对照扩大为完整算法或公开包验收。

本页属于 11 批正在实施的私有迁移，正式 `src/pyelk` 尚未切换。目标仍覆盖剩余 E09–E21；py-mermaid 集成独立后置。开发只做变更校验，全部功能完成后再统一全量。

## 当前分工与交付边界

| owner | 单写范围 | 当前交付 |
| --- | --- | --- |
| Root | `execution/recursive.py`、pool、visitor、provider 桥与协调器比较脚本 | 完整普通递归/Topdown 控制流已实现，正在使用实际原版调用轨迹验证 |
| A | Layered 全流水线 | 已闭合 crossing 的新策略；继续真实 SortByInputModel、动态配置及 importer，旧节点数 guard 不能直接删掉冒充完整移植 |
| B | inside-loop helper；随后 JSON 本地属性导入边界 | helper 保留重复 incident 与可变向量引用；导入边界与现有严格选项 API 分开 |
| V | 独立来源/代码审与原版观察 | 已批准递归与 Topdown 来源；采集真实 provider/池行为，比较脚本必须委托实际实现 |

7 个递归 helper、12 项算法 feature 声明及 pool/deprecated 已完成独立代码审。遍历首次 native 对照严格差异为 0，V 的 `owned-traversal-code-review-01.json` 已接受固定 120 文件版本，并单列后续可选 root 参数的静态变更，不重绑旧执行。inside-loop 的 3 个新实际原版对象与首次 native 严格差异为 0，Root 的 `inside-loops-code-review-01/review.json` 已独审接受；原版与 Python 异常类/消息不同，完整原始差异保留，只比较明确的 index-family 投影。上述结论不能推广成全部算法验收。

## Topdown 原始样例与首次失败

固定原版样例及脚本：`tests/fixtures/suites/next-native/recursive-topdown-{request,probe,oracle}`。原版实际执行三层 Fixed 图，并记录递归进入/退出、算法调用、provider fetch/release 与最终队列。GWT 生成的 `$H` 分配标记只在原始数据保留，不作为可移植图输出字段。

首次候选使用 122 文件检查点 `d6c65fc13489c50989f7b961fc81dcda053d496928a579c05139f3b1b6262cda`，恢复到 `.local/recursive-topdown-review-01`。真实执行保存在 `test-runs/20261104-HOST-11/root/recursive-topdown-native-01`：0.179423 秒，导入阶段失败，尚未执行协调器。原因是本地 `elk.padding: "0"`：原版解析失败后忽略该属性，Python 导入器目前直接抛异常。必须修正真实导入语义，不能修改样例为合法 padding 掩盖差异。

## 运行方式

先创建新源码检查点，恢复到不存在的独立目录，再运行比较脚本；禁止覆盖原观察、旧目录或旧执行绑定。

```powershell
python scripts/iteration/next_workspace.py snapshot
python scripts/iteration/next_workspace.py restore --destination .local/recursive-topdown-review-NEW --manifest migration/next-native/checkpoints/NEW_SHA.json
python tests/fixtures/suites/next-native/compare_recursive_topdown.py .local/recursive-topdown-review-NEW/src tests/fixtures/suites/next-native/recursive-topdown-request.json tests/fixtures/suites/next-native/recursive-topdown-oracle.json test-runs/NEW/comparison.json
```

正式留证通过 `scripts/validate_layout.py` 的 `run(argv, new_directory, timeout=30)` 包装，记录真实命令、退出码、耗时及 stdout/stderr 摘要。比较脚本记录执行源码逐文件 SHA，采用严格比较，覆盖几何、调用顺序、真实 provider 数量与池最终状态。原版观察已存在时直接复用，不重新执行无关算法组。

仅修改比较逻辑时，使用下面的脚本重新核对保存数据，不运行布局。后面可以继续追加 `REQUEST ORIGINAL SAVED_NATIVE` 三个参数为一组。`recursive_observations.py` 只剥除输入原无 `$H` 的真实已导入图元素路径上的整数分配标记，保留用户原有和业务字典内的 `$H`；脚本带对应负控制。

```powershell
python tests/fixtures/suites/next-native/verify_recursive_saved.py test-runs/NEW/saved-review.json tests/fixtures/suites/next-native/recursive-ordinary-nested-request.json tests/fixtures/suites/next-native/recursive-ordinary-nested-oracle.json test-runs/20261104-HOST-11/root/recursive-ordinary-nested-native-01/comparison.json
```

普通递归已新增两份实际原版观察，使用同一个固定 122 文件候选首次严格对照通过：`recursive-ordinary-nested-native-01` 为 0.140571 秒，覆盖嵌套 Box 的 children-first 调度、noLayout、1.5 倍缩放和同 provider 复用；`recursive-ordinary-resolved-native-01` 为 0.120961 秒，覆盖 root 已有真实 typed descriptor 时整体跳过 resolver，即使原始 algorithm 文本不同也使用已有 descriptor。每个节点的 descriptor presence、算法 ID 与 hierarchy 值均参与比较，未删除这些可观察状态。两次执行的原版/候选源码及比较脚本 SHA 均独立保留。

下一步：B 修正本地导入边界后，使用新恢复副本验证 Topdown；V 独立审核协调器代码及上述两份保存结果。全局 registry 生命周期、公开 API 与完整 Layered 集成仍需后续实测，不由这些样例宣称完成。

V 的 `recursive-coordinator-code-review-01.json` 已接受主调度代码及上述两份普通递归保存结果，并静态核对 Topdown 数学；Topdown 实际运行仍须等本地导入修正后验证。协调器当前持有自己的 registry/pools，不能据此宣称原版全局 singleton 跨 job 生命周期已集成。

本地导入新来源审查位于 `test-runs/20261104-HOST-11/root/local-property-source-review-02/review.json`，只批准独立 local 通道；严格 public/global 解析器不变。原版的 JSON null、对象值会抛 importer 错误，和字符串 `"null"` 的跳过行为不同，实际 DTO 继续保留；未知/歧义名称、无效值及成功 alias 的覆盖顺序分别处理。Root 正在同步修正私有 Session 的容器准入：非对象 layoutOptions 可回退到对象 properties，空对象 layoutOptions 则优先。
