# 可运行示例与当前边界

当前可运行的是范围查看工具：

```shell
python examples/show_scope.py
```

它报告 12 个待移植算法、243 个选项和零个已实现算法，不执行布局。
[双节点输入](../tests/fixtures/graphs/layered-two-node.json)供下一轮参考采集使用，暂无坐标输出。
README 中的 `ELK`/`layout` 为明确标识的设计稿，不能当作已安装接口调用。

本项目计算几何，不提供 Canvas、SVG 或字体 shaping 渲染器。
未来可用 py-mermaid 展示布局结果，图像仅作辅助检查，几何验收仍比较原始 JSON。
