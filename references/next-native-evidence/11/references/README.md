# 锁定来源、元数据与范围

当前E07来源入口为[33组件批准](e07-component-approvals.json)，A4/B3/R26分别绑定固定原文、完整E06证明继承、新方向/分量域、typed依赖、独立review与五份许可。使用方法见[E07手册](../docs/E07_DIRECTIONS_COMPONENTS.md)。`validate_e07_source_bindings.py --require-approved --with-upstream`核真实Git/npm字节；新span不增加semantic别名例外。来源通过不等于运行结果或完整算法验收。
E07的[当前安装收据](e07-installed-check.json)、[运行审计](e07-runtime-audit.json)、正式72例oracle及方向/分量/NS私有阶段分别验证。E04/E05/E06原wheel/声明位于`history/`，只作历史字节审计，不运行或回退；不能认证当前src。以下各旧轮证据保留原有含义。

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
`algorithms: []`和仅stress的bundled/FakeWorker额外诊断已在E02独立采样，layered调用失败；不据此推断元数据注册兼容。main/browser/真实Worker等变体仍需独立验证，不能从默认快照推断。

重要来源缺口：elkjs 的 build.gradle 从外部 `../elk` 读取 Java/Xtend/MELK，
其锁定 CI 使用外部仓库 `master`。elkjs tag 并没有固定该 Java checkout 的准确提交。
目前 npm 发行物是可重现的行为真值；可读 Java 算法来源映射仍为 unresolved，
M1 必须先确定、锁定并核对它与发行物的关系，不能把在线 Java 最新版当作同一源码。

E01已经交付 [来源链](e01-source-lineage.md)、[默认路径](e01-layered-path-notes.md)、[断言索引](assertion-inventory.json)、[port-map](port-map.json) 与 [汇总索引](e01-audit.json)。
12个npm文件均与固定Git中已跟踪的生成文件相同；解析的发布provenance没有给出先前Java/GWT构建提交，不能以release标签近似替代。
默认单边路径实测19次处理器调用；23个不同处理器类已定位生成实现范围。以上是E01历史结论；E04已按独立生成源审查移植受限真实路径，范围见下文。
离线与canonical校验命令见[布局验证手册](../docs/LAYOUT_VALIDATION.md)；本轮并行/反审与改进见[E01复盘](../docs/retrospectives/E01.md)。

E02的 [原生合同](native-contract.json)、[56组官方探针](e02-contract-probes.json) 和 [审计索引](e02-audit.json) 绑定原始请求字节/观察SHA；决策依据、有限适配与未验证边界见 [ADR 0001](../docs/decisions/0001-native-contract.md)。
它们冻结比较工具合同，没有实现Python算法；候选synthetic控制不进入官方探针和可用算法列表。

E03的 [模型来源](e03-model-sources.json)、[选项来源/九项收据](e03-option-sources.json) 与 [审计索引](e03-audit.json) 对应真实Python宿主数据实现，见 [手册](../docs/HOST_FOUNDATIONS.md)。
canonical Git path/blob、Windows工作副本CRLF和派生metadata捕获分别核对；来源facts与host design分列。9个解析schema、243诊断ID本身不代表布局语义；E03原始收据保留当轮source gate未核实状态。

E04的[A组件](e04-source-components-A.json)、[B组件](e04-source-components-B.json)和[逐组件审批](e04-component-approvals.json)绑定具体guard、传递helper、host语义、版本化独立review与原许可。`validate_e04_source_bindings.py`默认只核离线绑定；`--with-upstream`才重验真实blob/函数UTF16偏移/调用点。V8 coverage只作观察，缺少coverage记录不能证明函数未执行。
[安装收据](e04-installed-check.json)派生自真实已安装wheel同21例各3次的原始报告，保留原strict未通过事实；[runtime审计](e04-runtime-audit.json)限定实验能力，不提升完整12算法/243选项/8类别。用法见[E04手册](../docs/E04_NATIVE_SLICE.md)。旧E01–E03收据不回写，精确外部Java构建仍unresolved。

E05的[A](e05-source-components-A.json)、[B](e05-source-components-B.json)、[独立路由](e05-source-routing.json)与[22组件批准](e05-component-approvals.json)绑定当前ADR0004范围、共同source context、proof依赖、完整基审与原许可。`validate_e05_source_bindings.py --require-approved`严格核整个固定分母；加`--with-upstream`重验真正canonical源。
[E05当前安装收据](e05-installed-check.json)与[runtime审计](e05-runtime-audit.json)认证所记录的受限能力及当前包字节；原E04实际wheel/声明在`history/E04`，只读历史校验不运行、不认证E05。37路由阶段原状态、7数值和24真实helper观察分别保存，合成私有helper输入不算新公开布局案例。复跑/导出命令见[E05手册](../docs/E05_NATIVE_DAG.md)。

许可证原文见 [licenses](licenses)。自有发行许可仍待决定，不发布本地占位候选。
