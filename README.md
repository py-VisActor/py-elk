# py-elk

中文 | [English](https://github.com/py-VisActor/py-elk/blob/main/README.en.md)

原生 Python 图布局引擎：输入 ELK JSON 图，返回节点、端口和边的几何信息。
适合流程图、数据流图及其他需要自动布局的应用；绘制和字体测量由调用方负责。

- Python 3.11+，运行时无第三方依赖。
- 异步 `ELK` API，布局在隔离的 Python worker 中执行。
- Layered、树形、径向、力导向及打包等算法。
- 不需要 Node.js、Java、浏览器或 JavaScript 引擎。

## 安装

```shell
python -m pip install py-visactor-elk==0.1.1
```

PyPI 发行名是 **`py-visactor-elk`**，导入名是 **`pyelk`**。

## 快速开始

将以下代码保存为 `layout_example.py`，然后运行 `python layout_example.py`：

```python
import asyncio
from pyelk import ELK

async def main():
    graph = {
        "id": "root",
        "layoutOptions": {
            "elk.algorithm": "layered",
            "elk.direction": "RIGHT",
        },
        "children": [
            {"id": "a", "width": 40, "height": 30},
            {"id": "b", "width": 40, "height": 30},
        ],
        "edges": [{"id": "ab", "sources": ["a"], "targets": ["b"]}],
    }
    async with ELK(timeout=30) as elk:
        result = await elk.layout(graph)
        print(result["children"])
        print(result["edges"])

if __name__ == "__main__":
    asyncio.run(main())
```

worker 使用 `spawn`；请保留主入口保护，并在程序结束时关闭实例。
`async with` 会自动关闭，也可在 `finally` 中调用 `elk.close()`。
输入图不会被原地修改；结果包含节点坐标与边的 section/折点。

## 选择算法与选项

在图的 `layoutOptions` 中设置 `elk.algorithm`、`elk.direction` 等选项。
通过 `await elk.knownLayoutAlgorithms()`、`knownLayoutOptions()` 和
`knownLayoutCategories()` 查询当前实例的目录。
默认目录包含12个算法、243个选项、8个类别；注册数量不等于所有组合均已验证。
端口、标签和层级图的数据格式见[用户指南](https://github.com/py-VisActor/py-elk/blob/main/docs/USAGE.md)。

## 文档

- [用户文档目录](https://github.com/py-VisActor/py-elk/blob/main/docs/README.md)：安装、用法、API 与常见问题。
- [API 索引](https://github.com/py-VisActor/py-elk/blob/main/docs/API.md)：参数、生命周期、队列、超时与错误。
- [版本记录](https://github.com/py-VisActor/py-elk/blob/main/CHANGELOG.md)与[第三方许可](https://github.com/py-VisActor/py-elk/blob/main/THIRD_PARTY_NOTICES.md)。
- [维护者与 AI agent 入口](https://github.com/py-VisActor/py-elk/blob/main/docs/development/README.md)。

行为基线为固定 **elkjs 0.12.1**。已知宿主差异和有限验证边界见
[兼容说明](https://github.com/py-VisActor/py-elk/blob/main/API_COMPATIBILITY.md)；不承诺跨实现任意输入的像素或浮点坐标完全相同。

## 许可与反馈

原创代码使用 MIT；移植来源代码保留 EPL-2.0 / GPL-3.0-or-later 与 Apache-2.0
等适用条款，详见 [LICENSE](https://github.com/py-VisActor/py-elk/blob/main/LICENSE) 和 [THIRD_PARTY_NOTICES.md](https://github.com/py-VisActor/py-elk/blob/main/THIRD_PARTY_NOTICES.md)。
问题与建议请提交到 [GitHub Issues](https://github.com/py-VisActor/py-elk/issues)。
