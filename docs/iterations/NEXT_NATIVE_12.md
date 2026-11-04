# 12 批执行 brief

承接 11 批固定 126 文件检查点 `e482a49e1453cc9c866947053c1ee539769df160badef1e280f6be6d388afd9a`。普通递归、Topdown 和 DisCo→Fixed 共享池四个新增整调用场景已严格对照通过，14 个本地属性导入 DTO 已独审。正式 `src`、公开 API 和完整算法验收数不因私有迁移自动改变。

| owner | 单写范围 | 下一交付 |
| --- | --- | --- |
| Root | execution/options、入口与归档 | 收口本地导入与递归文档，继续调用者选择的 metadata/legacy 属性与公开入口依赖；为真实 Layered 有状态 provider 预留注册桥 |
| A | Layered 动态流水线、importer、真实阶段配置 | 先关闭 SortByInputModel/诊断文本独审，再接 Assembler/Configurator 与五主 phase 实际配置、默认路径完整入口 |
| B | 新 `algorithms/layered/network_simplex_general.py` | 完整 driver、显式 edge weight/delta/priority、迭代连通分量与大组件 subtree 处理；旧 `layering.py` 保持只读 |
| V | A/B 新来源及代码独审、新原版对象 | 按独立闭包审核动态配置和通用 Network Simplex；已有成功递归/算法组不重跑 |

Network Simplex 的 iteration limit 必须按实际 compiled `round_int`：正数 `sqrt(componentSize)` 截断，再乘 thoroughness×4；不能按函数名推断为四舍五入。n≥40 的 removeSubtrees→initialize→solve→reattach 是真实数学流程，不能仅删旧 guard。A 的默认 NETWORK_SIMPLEX 注册后应指向 B 的新完整 driver。

Layered provider 需要有状态实例：拟定 `pyelk.algorithms.layered.provider.LayeredProvider().__call__(state,node,monitor=None)`，持有 Configurator/Assembler。Assembler reset 不清 cache，主 phase 和 processor 对象会复用。类与完整入口实际交付后，Root 才接真实注册；不能先把 metadata 声明当作可执行实现。

属性导入只复制实际 present 的 typed 属性与 Integer token，默认值由真实 caller 的 owner 读取。不能把 metadata 默认表整张写入图，也不能混用 Core/Layered 的同名默认。当前 local importer 的 243 声明固定 catalogue、缺失 legacy 表与 caller-selected registry 仍是显式后续范围。

维持 Root+A/B/V 三个 sub-agent、产品文件单 owner。先接口与短来源闭包，再尽早交真实小场景；独立范围并行，依赖路径按实际调用顺序接通。失败保留，后验脚本强化只重核保存数据。开发继续只做变更校验，全部功能完成后才启动最终全量。
