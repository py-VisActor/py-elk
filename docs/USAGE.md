# 用户指南 / Usage

## 安装与运行

```shell
python -m pip install py-visactor-elk==0.1.1
```

完整可复制示例见 [中文首页](../README.md) / [English](../README.en.md)。
保存为独立 `.py` 文件后运行；实际布局使用 Python `spawn` worker，保留
`if __name__ == "__main__":` 保护。已有事件循环中使用 `await`，不要嵌套 `asyncio.run()`。

## 输入与输出

输入是可序列化为 JSON 的字典、列表与标量。推荐为每个元素提供唯一的字符串 `id`。

| 元素 | 常用字段 |
| --- | --- |
| 根图/复合节点 | `id`、`children`、`edges`、`layoutOptions` |
| 普通节点 | `id`、`width`、`height`，可含 `ports` 和 `labels` |
| 边 | `id`、`sources`、`targets`，端点为节点/端口 ID |
| 标签 | `text`、调用方测量的 `width`、`height` |

`await elk.layout(graph)` 返回独立结果，原图不被原地修改。
节点通常增加 `x`/`y`，图获得整体尺寸；有路由的边返回 `sections`，包含
`startPoint`、`endPoint` 与可选 `bendPoints`。端口和标签也可能获得位置。
具体字段取决于算法与图结构，不要假定每个算法都会提供边路由。

复合图节点的位置相对于父容器；端口相对于所属节点。绘制时按容器层级累加位置，
边 section 使用其布局容器的坐标系。不要直接将所有局部坐标当成根图绝对坐标。
字体测量与 SVG/Canvas 等绘制由调用方完成，本包只计算几何。

## 布局选项

```python
graph["layoutOptions"] = {
    "elk.algorithm": "layered",
    "elk.direction": "DOWN",
    "elk.spacing.nodeNode": 30,
}
```

常用方向是 `RIGHT`、`DOWN`、`LEFT`、`UP`。算法决定适用的方向、端口与路由选项。
构造时可提供 `defaultLayoutOptions`；调用时可提供 `args["layoutOptions"]`。
显式调用级选项会替换构造默认，即使是空字典；根图和元素上的局部选项仍由解析器按层级处理。
为避免意外丢失默认值，调用时明确组织需要的选项映射。

通过 `knownLayoutAlgorithms()`、`knownLayoutOptions()`、`knownLayoutCategories()` 查询目录，
用法见 [API索引](API.md)。保留 elkjs 的 camelCase 方法与选项命名。
元数据声明、特定选项的实际效果、浮点坐标对照是不同验证层级，不能互相替代。

## 生命周期与错误

使用 `async with ELK(...) as elk:` 自动关闭，或 `try/finally` 调用 `elk.close()`。
单实例按 FIFO 使用一个 worker；`max_pending` 默认16，包含执行中与排队中的任务。
`timeout` 是包含排队与启动的总期限，单位秒；`None` 表示不设置该期限。
取消、关闭与资源限制的异常类别见 [API索引](API.md)。

布局耗时、失败和随机性取决于图与算法。不要将 `seed=0` 当作跨宿主确定性种子，
不要只根据某个输入能返回坐标就推断所有选项组合均兼容。

## 常见问题

- **为什么安装名和导入名不同？** 安装 `py-visactor-elk`，代码中 `from pyelk import ELK`。
- **需要 Node 或 Java 吗？** 生产布局不需要；它们只可能出现在本仓研发来源工具中。
- **在终端 stdin/Notebook 中 spawn 失败？** 将布局程序保存为可导入的独立脚本并保留主入口保护。
- **标签尺寸从哪里来？** 用应用自己的字体/绘制引擎测量，再把尺寸交给布局。
- **返回结果没有我期待的折线？** 先确认所选算法是否计算边路由，再检查具体选项与结果 sections。
- **需要报告问题？** 附上最小图JSON、布局选项、Python/包版本及完整异常，提交到
  [Issues](https://github.com/py-VisActor/py-elk/issues)；不要包含私密业务数据。
