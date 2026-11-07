# Examples / 示例

当前安装使用从 [用户指南](../docs/USAGE.md) 与 [API索引](../docs/API.md) 开始。
README 的完整示例包含 spawn 主入口保护与自动关闭，可直接复制为独立脚本。

- [layout_path.py](layout_path.py)：从已安装包执行双节点布局，输出JSON；不渲染图片。
- [diagnostics.py](diagnostics.py)：布局日志/计时示例。计时值沿用固定源标尺，不应当作CPU秒。

其他脚本保留其研发/历史用途：`api_lifecycle.py` 的元数据计数断言来自E08旧切片，
`show_scope.py`/`show_foundations.py` 是历史范围与基础模型观察，不作为当前安装验证入口。
不要从这些旧数字推断当前算法注册范围；当前查询方法见API索引。

开发采集、验收与原版依赖说明见 [维护者目录](../docs/development/README.md)。
整理前的示例目录说明保存在 [原文快照](../docs/history/audience-before-20261107/examples-README.txt)。
