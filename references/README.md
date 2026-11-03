# 锁定来源、元数据与范围

唯一行为基线为根目录 [UPSTREAM.json](../UPSTREAM.json) 的 elkjs 0.12.1。
已核实 Git tag/commit、11 个关键 canonical blob SHA、npm gitHead、tarball SHA512 integrity/
SHA256 和 12 个发行文件 SHA。日常命令只核查，不重新生成 lock 掩盖漂移：

```shell
python scripts/upstream.py fetch
python scripts/upstream.py check
```

源码位于 `.local/upstream-elkjs`，发行物位于 `.local/npm-elkjs/package`，均为研发资料。
[source-inventory.json](source-inventory.json)索引全部 64 个 elkjs Git 文件，包含 14 个 Mocha 文件；
这不是完整断言数，也不包含尚未锁定的 Java ELK 算法测试集。

[metadata](metadata)保存真实官方默认注册元数据：12 个算法、243 个选项、8 个类别。
这些是覆盖分母；Python 可用能力仍为零。生成入口和边界见 [reference 工具](../tools/reference/README.md)。
真实布局/错误/副作用保存于 [layout/index.json](layout/index.json)：25个自行编写请求，每例2次独立进程。
采集和完整差分用法见[布局校验手册](../docs/LAYOUT_VALIDATION.md)。原始字段/换行字节受指纹保护；不是完整上游断言覆盖或Python算法证据。
`algorithms: []`、逐算法筛选、main/browser/真实 Worker 等变体需在 M1 独立进程采样，不能从默认快照推断。

重要来源缺口：elkjs 的 build.gradle 从外部 `../elk` 读取 Java/Xtend/MELK，
其锁定 CI 使用外部仓库 `master`。elkjs tag 并没有固定该 Java checkout 的准确提交。
目前 npm 发行物是可重现的行为真值；可读 Java 算法来源映射仍为 unresolved，
M1 必须先确定、锁定并核对它与发行物的关系，不能把在线 Java 最新版当作同一源码。

许可证原文见 [licenses](licenses)。自有发行许可仍待决定，不发布本地占位候选。
