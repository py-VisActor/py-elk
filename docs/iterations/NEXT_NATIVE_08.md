# 08批执行 brief

目标是把已审显式parser接入真实属性消费链，并继续闭合Layered与packing算法。沿用root+A/B/V，最多三个sub-agent；代码可并行写，源审/候选对照按小块移交，不等待整批文档。固定起点为07批90文件检查点，正式src仍为E11基础候选。

| owner | 单写范围 | 首个可审交付与校验 |
| --- | --- | --- |
| root | options、execution共享宿主、检查点和状态文档 | 已审scalar parser接真实global targets/单次解析与reader；只用新增属性/受影响默认控制；OBJECT chain和Integer盒身份先交source闭包 |
| A | layered算法内核 | 实际Fenwick、between/inlayer计数及side positions，随后NS/hyperedge与sweep消费者；不删guard冒充完成 |
| B | DisCo、RectPacking、Spore后续 | polygon相交、raster/Polyomino与真实packing阶段；不以bbox或Box替代 |
| V | 独立source/code审与新原控、比较器 | 优先已交小块；预备独立原对象；只复验新增/失败分支，不重复已接受组 |

接口原则：Core、provider Property_2、metadata-IProperty与adapter投影分别保留；显式值、global共享与默认presence不得混淆。跨provider沿同一Session，源Integer盒身份不由Python小整数缓存推断。真实clone深度先核源。公共API与完整算法声明等实际消费者闭合后再调整。

每个小块保留原source字节、请求、执行SHA、原始失败和独审收据；在新目录运行，与代码采集分开。root归档只核新字节绑定，不重演旧布局。全部迁移功能完成之前不执行全量、旧平台矩阵或重复通过组。批末复盘交付、队列等待、失败原因与下一批改进，不凭局部命令时间宣称整体提速。
