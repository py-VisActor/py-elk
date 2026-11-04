# 通用 JSON 与跨算法状态先行实现

该工作属于 E13/E16/E17 共享宿主准备，正式 `src/pyelk`、发行版本与公开能力暂未切换。实现位于可恢复的 private 检查点；整个算法完成数仍为 0。基础正式包继续按 E11 流程交付，py-mermaid 集成单独后置。

`references/next-json-transfer-sources.json` 保存固定 elkjs 0.12.1 worker 的 87 个原字节片段，覆盖原对象映射、两遍传回、坐标模式、section 关系、边容器选择与 primitive edge 导入。root 已独立核对片段字节、哈希和实际分支；源批准不代表实现通过。

`execution/json_transfer.py` 的 `JsonLayoutSession` 为一次作业保存同一个节点、端口、边对象集合和内部属性状态。多个 provider 调用各自的 `_layout(session, node, monitor=None)`，不能逐层调用会重新克隆图的 wrapper。计算后的边可以位于另一个内部容器，但导出仍更新原 JSON 所属节点中的 edge 对象，不移动用户的数组或丢失业务字段。

工作图与原 JSON 分开保存，因此内部清空 bends、sections 或 junctions 时，导出仍能遵守源中“非空才覆盖”的条件，而不误删原字段。已有 section 保留原 ID 与业务字段；新 section 使用 edge ID 加 `_s` 与序号。单 section 的 incoming/outgoing shape 仅在两者都未提供时自动补齐，section 关系还要维护反向链接。

先完成所有 node/port 的全局坐标和模式记录，再处理 edge/label。根的 x/y 原样传回；shape ROOT、edge CONTAINER/PARENT/ROOT 分别使用源定义的父节点、当前容器和原所属节点。`container` 使用 node identifier 字符串，原 endpoint ID 保留已接受的 Python str/int 类型。GWT `$H` 是进程对象标识副作用，不伪造每图编号；完整 strict 差异保留。

当前实现继续采用已有 native JSON 边界：独立拥有输入副本、有限几何值、尺寸非负、typed str/int ID、重复 ID 和无效引用明确报错。这与生成 JavaScript 的某些数字 ID 转换及输入修改副作用不同，不能声称逐运行时完全相同。

选项解析通过 `resolve_option(element, short_name, default)` 接口接入。没有该接口时仅使用 provider 既有的本地属性辅助入口；尚未实现所有选项的统一注册、全局 targets 和所有语法，不能将其当成完整选项层。默认值须分别核对 Core 声明和算法 metadata，不能把旧首版 schema 当成所有算法的通用默认表。完整递归调度、算法选择、node micro layout、top-down/层级处理和公开 API 集成仍待推进。

新会话先按 [检查点说明](../../migration/next-native/README.md) 恢复源码。只检查本批变更时执行：

```shell
python -m unittest tests.next_native.test_json_transfer -v
```

测试在临时目录恢复版本化源码，再用独立解释器执行 `tools/platform/next_json_probe.py`。六个方法检查原 owner/根坐标、坐标 enum ordinal 与非法值、条件字段/section 反向关系、primitive edge/跨 provider 状态、非法导入不修改输入，以及 source detached 根自环不参与传回。测试对应 JSON 宿主改动，不是已安装包、公开 API 或所有算法的验收。实际执行命令、stdout/stderr、源检查点与独立原 worker 对照记录随本批变更记录保存；不要重绑旧报告的 source SHA。

本次实际按变更拆为初稿四项、enum parser 修改后一项、detached 分支修复后一项；没有为了新增后两项再跑先前成功的四项。独立官方四个坐标请求的首轮几何/业务差异为 0，完整 strict 仍有 16 项 `$H`；新增 detached 原请求暴露过错误，修后该原请求几何/业务差异为 0，另保留 1 项 `$H`。先失败后修复的原材料保留，未修改旧执行的源码绑定。

并行边界：root 独占该宿主、中央选项和递归接口，A 独占 layered ports/NodeContext/size，B 独占树形和径向算法，V 独立审源、审实现和制作原始对照。已批准的文件范围内小块直接推进；跨边界需求通过接口交接。所有功能完成前不运行 full，也不因 CI 的未知路径自动回退全量。
