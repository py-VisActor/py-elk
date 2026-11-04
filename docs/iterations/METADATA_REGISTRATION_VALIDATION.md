# 注册集与属性查找校验

本页说明 12 批私有迁移。正式 `src/pyelk` 的 E11 API 尚未切换，不能把私有 metadata 的 12/243/8 数量当成全部 Python 算法已验收。

`execution/metadata_service.py` 的 `NativeMetadataService` 管理实际注册顺序、descriptor 与 provider 池。Session 和协调器需要传入同一个 service；Source 的配置、属性查找和算法解析共享同一服务，不能各自补默认注册表。

```python
from pyelk.execution.metadata_service import NativeMetadataService
from pyelk.execution.json_transfer import JsonLayoutSession
from pyelk.execution.recursive import RecursiveLayoutEngine

metadata = NativeMetadataService(["layered"])
state = JsonLayoutSession({
    "id": "root",
    "layoutOptions": {"elk.algorithm": "box"},
    "children": [{"id": "a", "width": 20, "height": 10}],
}, metadata=metadata)
RecursiveLayoutEngine(metadata=metadata).layout(state)
result = state.export()
```

示例使用已接通的 Box body。Layered metadata 声明可注册，完整 Layered body 仍待其流水线交付；源码恢复目录需作为比较脚本的 `PRIVATE_SRC` 或 Python 导入路径，不能误用当前正式 E11 包。

## 原版已确认的规则

| 注册选择 | algorithms | options | categories |
| --- | ---: | ---: | ---: |
| Core（空列表） | 3 | 94 | 8 |
| `layered` | 4 | 183 | 8 |
| 默认九个 provider selector | 12 | 243 | 8 |

Core 总是注册 Fixed/Box/Random。注册选择只识别实际短名称；例如注册列表内 `org.eclipse.elk.layered` 与未知名称会被忽略。布局选项内选择算法的 suffix lookup 是另一条路径，不套用注册列表规则。任一 Spore selector 都会注册两个 Spore 算法。

查找先匹配当前 ID 的完整名称或带点边界的 suffix：多项匹配即歧义；没有当前匹配时才查 legacy ID。当前版本仅一项实际 legacy：`org.eclipse.elk.layered.northOrSouthPort` → `org.eclipse.elk.layered.allowNonFlowPortsToSwitchSides`。注册更新清空 option suffix cache，保留算法 suffix cache 的旧 descriptor 引用；不能统一清空所有 cache。

Core 中 `direction` 唯一，注册 Layered 后它与 `layered.priority.direction` 冲突而变成歧义；`elk.direction` 仍唯一。新服务按当前注册集处理 local JSON 属性，未注册的属性不进入 holder。12 批全局配置尚沿用严格策略；13 批已另行实现真实 `optsToCfg`，见[全局配置校验](GLOBAL_OPTIONS_VALIDATION.md)，各自执行仍绑定实际检查点。

metadata descriptions 是编译进包的固定声明，运行时不读取 `references`。类别的 `knownLayouters` 依当前算法注册顺序重建，返回值为独立 JSON 副本；不把 metadata defaults 写入几何图的实际 Property。

## 已执行与如何复现

来源与代码审查：`HOST-12/B/metadata-registration-{source,code}-review-01.json`。原版新目录观察覆盖 11 个注册组合与 3 次连续注册，首次 native 严格差异为 0；默认 metadata getter 与原先固定的 12/243/8 原始公开描述完全一致。该组不执行布局。

另有两份新的实际 Box 整体递归：`recursive-selected-core` 与 `recursive-selected-layered`。比较器验证导入前后真实 property presence、legacy false 值、完整 metadata 数组、布局几何、实际调用顺序与池状态，并断言 Session/Engine 共享 service/registry/pools。两个首候选均严格差异为 0，已由 V 独审；旧四个递归场景、旧 14 个 local DTO 未重跑。

在仓库根目录先恢复新源码目录，再复用归档中的原版数据。下面的输出文件所在目录需先创建，文件不可已存在。

```powershell
python scripts/iteration/next_workspace.py restore --destination .local/metadata-check-NEW --manifest migration/next-native/checkpoints/88af57765167f3850266c90deb5a105f4bae7648b07426acf1309081d6b6999c.json
python tests/fixtures/suites/next-native/compare_metadata_registration.py .local/metadata-check-NEW/src tests/fixtures/suites/next-native/metadata-registration-request.json references/next-native-evidence/12/test-runs/20261104-HOST-12/root/metadata-registration-original-01/observation.json test-runs/NEW/metadata.json
python tests/fixtures/suites/next-native/compare_recursive_topdown.py .local/metadata-check-NEW/src tests/fixtures/suites/next-native/recursive-selected-core-request.json references/next-native-evidence/12/test-runs/20261104-HOST-12/root/recursive-selected-core-original-01/observation.json test-runs/NEW/core.json
```

将最后一个命令的 `core` 改为 `layered` 可校验另一个场景。留证仍用 `validate_layout.run` 包装真实命令。比较器仅变更时，用 `verify_recursive_saved.py` 重核已保存结果，不重新执行布局。

静态表生成器为 `tools/reference/build_registration_metadata.py`，要求 accepted/空 blockers 的独立来源审和精确源包 SHA。重新生成前需恢复源包、审查收据里列明的同名原材料路径；通常新会话直接恢复检查点内已生成源码即可，无需重采 metadata。

八项原版无可用 raw 构造器、严格 API/全局配置的后续整合、完整 Layered 与公开注册/包交付继续单独推进。本页不声明全量功能或平台验收。
