# 独立算法几何检查

这些谓词只读取已保存的 JSON，使用矩形、树层和半径关系独立检查几何，不导入 pyelk 算法，也不以原版坐标作定义。原版与原生分别接受相同谓词检查。当前 14 组对照共 28 个观察，双方各 10 PASS、4 NOT_ASSESSED、0 FAIL；9 个测试捕获了 7 个数值破坏负控制。[原始报告](changes/20261104-independent-algorithm-geometry.json)绑定实际归档 SHA。

| 算法 | 已检查的有限条件 | 未包含的范围 |
| --- | --- | --- |
| MrTree | 唯一有根简单树、无压缩：方向正确，连续深度层带保持节点间距 | DAG、压缩、非树及端口/标签 |
| Radial | 唯一有根树、显式正半径、NONE compactor、无旋转：同层中心等半径，相邻层半径增量至少为指定值 | 其他 compactor、缺省半径、矩形无交叠或精确 depth×radius |
| Box / RectPacking | 无固定容器、无端口/标签的平面叶节点：矩形无交叠且在根容器内 | 最优面积、全部打包启发式及层级 |
| SporeOverlap | 同上且 scanline 启用：矩形无交叠且在根容器内 | 全部消重叠策略和抖动边界 |
| DisCo | 按输入无向边分组件：不同组件的节点矩形分离 | 同组件内部重叠；POLYOMINO 可合法互锁，不能要求整个组件 bbox 分离 |

容纳使用实际根容器范围；几何容差为 `1e-6`。部分检查有独立的未评估项，PASS 只覆盖表中适用谓词，不是该算法的全部几何保证。Force/Stress 的迭代与质量描述性指标见 [性能报告](FULL_PERFORMANCE.md)，不宣称通用收敛。

可在干净 checkout 直接运行，不需恢复忽略目录，也不会启动布局或原版：

```shell
python scripts/algorithm_geometry.py --out NEW_REPORT.json
python -m unittest discover -s tests/validation -p test_algorithm_geometry.py -v
```

默认读取 `references/full-native-closure/options.zip` 内的真实保存数据；完整归档身份与角色证据应另外按 [选项覆盖手册](iterations/FULL_OPTION_COVERAGE.md)严格核对。更换输入、参数或适用条件时，必须明确新增谓词的范围，不能把 NOT_ASSESSED 改称通过。
