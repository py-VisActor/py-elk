# 可运行示例与当前边界

E09 开发包安装后运行 `python examples/diagnostics.py`，真实布局并输出日志/计时树。`executionTime` 延续固定生成源的特殊 wall-tick 标尺，解释见 [ADR0008](../docs/decisions/0008-e09-diagnostics-coverage.md)；它不是CPU秒。正式验收及同包结果只看状态页。

当前可运行的是范围查看工具：

```shell
python examples/show_scope.py
python examples/show_foundations.py
```

它报告12算法/243选项的完整分母、零个完整验收算法及当前可调用的E07实验切片，不执行布局。
第二条执行实际Python模型/配置/上下文，演示typed ID与输入/调用隔离，同样不计算布局。用法和边界见 [宿主基础模块](../docs/HOST_FOUNDATIONS.md)。
安装本地开发wheel后，可执行真实布局：

```shell
python -I examples/layout_path.py
```

该例直接导入已安装包，不添加仓库src路径、不读reference或fallback；缺包时明确失败。[E07手册](../docs/E07_DIRECTIONS_COMPONENTS.md)解释0–8原始节点/最多28边、四方向/多组件范围、调用限制及真实安装对照脚本；[E05手册](../docs/E05_NATIVE_DAG.md)保留diamond+长边例子。README中的双节点ELK例子也可执行。

E08正在实现公共API和执行生命周期。[api_lifecycle.py](api_lifecycle.py)演示三个async元数据查询、真实双节点布局、调用方输入保留，以及`try/finally`关闭：

```shell
python -I examples/api_lifecycle.py
```

它直接使用该解释器中安装的`pyelk`，主入口有适配spawn的`__main__`保护。当前源码的查询范围为1个受限算法、9项选项、1个类别；这不等于完整参考12/243/8，也不表示新wheel或正式发布已经通过。[E08指南](../docs/E08_API_LIFECYCLE.md)列出临时指定源码的验证方法、注册差异、队列/期限、取消/关闭和错误边界；当前候选安装验收命令以root最终交接为准。

本项目计算几何，不提供 Canvas、SVG 或字体 shaping 渲染器。
未来可用 py-mermaid 展示布局结果，图像仅作辅助检查，几何验收仍比较原始 JSON。
