# 13 批执行 brief

承接 [12 批](../changes/20261104-next-native-12.json)固定的 138 文件检查点 `9428b606012a93a163977ee57c23f8072d5860aa3a87dcf9be79976246e99c0f`。元数据选择注册、legacy lookup、两份选定注册集 Box 递归请求，以及通用 NS/BK/Orthogonal 的限定工作图控制已有来源与代码独审。完整算法验收仍为 0，正式 `src` 和公开包尚未切换。

| owner | 单写范围 | 交付与依赖 |
| --- | --- | --- |
| Root | execution/options/metadata、入口、归档；新 `components_general.py`/`resize_general.py` | 全局 optsToCfg 已独审；接真实组件拆并与尺寸收尾，A 不双写这两个新文件。LayeredProvider 实际可用后再注册有状态实例，审核短闭包减少 V 排队 |
| A | Layered importer/exporter、general long edges/pre/post、provider | 以已批 NS/BK/Orthogonal 接线；逐块交实际工作图和默认流水线，不能仅删除旧切片 guard；组件与 resize 已交 Root |
| B | `algorithms/layered/native_adapters.py` | Shape/Label/Edge 可先交新对象对照；Graph/Node 与 Port/Margin/Core 默认按独立来源闭包实施，接真实尺寸 caller |
| V | A/B 独立来源、代码和新原版对象 | 按短闭包先审；不重复 Root 已批准的 Graph/Node 来源或已成功 NS/BK/Orthogonal 对照 |

Layered provider 接口为 `LayeredProvider().__call__(state,node,monitor=None)`，实例持有 Configurator/Assembler，reset 保留 cache。属性只复制 present typed 值与 Integer token；复杂默认在实际 getter 需要时物化。组件保持 RANDOM 与 graph.random 同一引用，并传递实际 PROCESSORS、source session 和原始对象关系。路由接新 `orthogonal_general`，保留现有 VectorChain 身份。

优先闭合默认路径，先交最小真实控制，再补未走到的数学分支。已有成功组不重跑；比较器或归档工具修改使用保存数据重核。每次执行即时保存 checker/probe 字节，保留首次失败及原因。归档固定旧检查点，不阻塞 owner 后续实现。

全部迁移功能完成前不运行全量，不声明完整算法或发行通过。许可仍待用户选择，继续独立技术工作。批末记录交付、并行利用、阻塞和下一轮调整；没有同分母计时不宣称整体提速比例。
