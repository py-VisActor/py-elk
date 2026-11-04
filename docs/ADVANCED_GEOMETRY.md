# 高级几何独立校验

[advanced_geometry.py](../scripts/advanced_geometry.py) 直接检查输入要求与返回的公共 JSON；不导入布局实现，不用 Source 坐标作为期望位置。Source 和 Python 的实际结果分别接受同一组约束检查。坐标差分仍是另一项检查，几何成立不能替代坐标兼容。

从仓库根目录运行受影响检查：

```shell
python -m unittest discover -s tests/validation -p test_advanced_geometry.py -v
```

该命令只读取已保存的原始结果、验证约束及破坏样本，不启动 Source、Python 布局或平台矩阵。旧端口样本由 `references/full-native-closure/options.zip` 及 manifest 绑定；新样本在 [geometry-contracts](../tests/fixtures/suites/full-option-effects/geometry-contracts/manifest.json)，包含真实公共调用的缺尺寸标签、双 section，以及实际 LabelCell 状态。各自保留原始调用与执行身份。

也可对自己的已保存结果求值：

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from advanced_geometry import validate

request = json.loads(Path("request.json").read_text(encoding="utf-8"))
saved = json.loads(Path("result.json").read_text(encoding="utf-8"))
report = validate(request, saved.get("result", saved))
print(json.dumps(report, ensure_ascii=False, indent=2))
```

`status` 为 `PASS`、`PARTIAL` 或 `FAIL`。只要有未评估约束，`passed` 就不会为真；`assessedPredicatesPassed` 仅表示已适用谓词没有失败。必须同时查看 `checked`、`errors` 和 `not_assessed`。缺尺寸标签默认为零不代表进行了字体测量。

本次增量的适用边界：

| 约束 | 独立检查与范围 |
| --- | --- |
| FIXED_POS／FIXED_RATIO | 普通平面 RIGHT Layered 叶节点、显式 side 和给定切向坐标。比例使用端口矩形原点除以 owner 尺寸，锚点另行验证；实际样本包含 owner 从 120×90 调整到 180×140。 |
| FIXED_ORDER／index | 同侧至少两个端口、唯一整数 index、相同尺寸／锚点、足够空间与 BEGIN 对齐；NORTH／EAST 递增，SOUTH／WEST 递减。过满、重复 index 或复杂覆盖不推断。 |
| 最小尺寸 | 显式非负 MINIMUM_SIZE 的普通 Layered 叶节点；不推断继承或全局选项覆盖。 |
| 样条 | 新生成的平面 CONSERVATIVE 非自环边，非空控制网必须有 3k+1 个点，并检查两端实际附着。没有曲线避障承诺。 |
| 标签尺寸／间距 | 保留给定尺寸；无覆盖的 Layered／fixed 缺尺寸为零。`validate_label_stack(rectangles, axis, minimum_gap)` 只检查已明确堆叠模式的同坐标系矩形间距，不从任意 OUTSIDE 标签推导全局避让。 |
| section 连接 | 已保存的真实双 section：相邻连接点一致、引用存在且互为逆向引用。保留 fixed 的几何，不要求其任意输入都正交或贴节点边框。 |

负控制会在移动端口的同时移动附着端点，以确认切向／比例／顺序检查有独立检错能力；另覆盖缩小节点、删除样条控制点、移动曲线端点、改变缺省标签尺寸、断开连接与删除逆向引用。约束之外的组合继续明确保留为未评估。

本次[原始增量报告](changes/20261104-advanced-geometry-contracts.json)记录 24 个公共 JSON 结果观察及 4 个实际堆叠状态，154 项新增或新具检错能力的约束均无失败；14 个 JSON 观察仍是 PARTIAL。

这次增量不重写旧 142 个观察、6590 项已适用检查的执行记录；旧记录及 40 项 PARTIAL 保持原范围。新增样本和谓词另行记录，不将旧矩阵改称当前脚本的完整重跑结果。
