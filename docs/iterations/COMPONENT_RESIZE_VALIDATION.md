# 组件与尺寸收尾变更校验

13 批的 `components_general.py` 不调用旧组件输入限制或旧分支猜测。实际 DFS 按端口顺序、incoming 再 outgoing；默认即使只有一个连通组件也创建新 LGraph，浅复制 present 属性、Integer token、RANDOM 和 PROCESSORS，另复制 padding 并删除组件 minimum。SimpleRow 使用实际 priority、model order、面积、spacing 和两次 offset/move。三个外部打包器及 connected compactor 尚未实现，选中时明确 pending。

`resize_general.py` 将层节点按实际顺序追加到 layerless 并清层；最小尺寸默认向量按原版物化与修改，fixedGraphSize 在此之后才阻止几何调整。内容对齐、外部 EAST/SOUTH 端口移动以及 padding 加减顺序均保留。取消/异常与 monitor 生命周期属于实际主流程，不由 cleanup helper 代替。

两组各六个新原版对象和首个 native 均严格 0 差异，来源与代码独审接受。固定源码见 146 文件检查点 `1c086f0651c288c3086144c24cca544adebbb35aa82cd707ba36bdc676b1c4d7`；各次实际执行仍绑定当时源码，不能将旧结果重绑最新工作区。

复核具体改动时，在仓库根恢复新目录并先创建输出目录。原版证据位于 13 批归档，不需重采：

```powershell
python scripts/iteration/next_workspace.py restore --destination .local/component-check-NEW --manifest migration/next-native/checkpoints/1c086f0651c288c3086144c24cca544adebbb35aa82cd707ba36bdc676b1c4d7.json
python tests/fixtures/suites/next-native/compare_components_general.py .local/component-check-NEW/src tests/fixtures/suites/next-native/components-general-request.json references/next-native-evidence/13/test-runs/20261104-HOST-13/root/components-general-original-01/oracle.json test-runs/NEW/components.json
python tests/fixtures/suites/next-native/compare_resize_general.py .local/component-check-NEW/src tests/fixtures/suites/next-native/resize-general-request.json references/next-native-evidence/13/test-runs/20261104-HOST-13/root/resize-general-original-01/oracle.json test-runs/NEW/resize.json
```

仅比较器或归档有变化时，直接对保存 report.actual 与 oracle.observation 使用 `layout_checks.diff(..., tolerant=False)`，不重新执行组件或 resize。实际命令通过 `validate_layout.run` 留存 stdout/stderr/command，并即时复制 checker。这里不代表完整 Layered 或全量功能验收。
