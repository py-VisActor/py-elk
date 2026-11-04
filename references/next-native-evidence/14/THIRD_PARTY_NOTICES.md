# 第三方来源与许可状态

2026-11-04 用户决定：项目自行编写的代码采用根目录 [MIT LICENSE](LICENSE)。ELK 移植代码继续适用原始 `EPL-2.0 OR GPL-3.0-or-later` 声明，Apache 辅助代码继续适用 Apache-2.0；各自版权、来源及通知均保留。整个包的 SPDX 表达式为 `MIT AND (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0`。正式源码通过 [项目仓库](https://github.com/py-VisActor/py-elk)及对应发行 sdist 提供。本次只落实许可决定，未发布。下方逐轮记录中的“项目自身许可待定”为决定之前的历史状态。

E11已补实际GWT Random辅助部分的Apache-2.0正文与归属，见 [NOTICE-GWT-Random.md](src/pyelk/_licenses/NOTICE-GWT-Random.md) 和 [许可盘点](docs/iterations/E11-license-inventory.json)。phases.py只改版权/SPDX注释，35模块的运行AST保持一致；GWT2.13.0仍只是对应源码材料，不宣称解决精确worker构建来源。原E09/E10候选已封历史闭包，不用其旧SHA认证后续包。项目自身许可选择和正式候选仍待落实，尚未发布。

E09 的真实 monitor 树、日志收集、Network simplex 子任务、BK 动态诊断与根日志清理续审固定生成源，见 [ADR0008](docs/decisions/0008-e09-diagnostics-coverage.md) 及 [来源清单](references/e09-diagnostics-sources.json)。新包包含 NOTICE-E09.md，保持此前通知；不扩展既有算法域，也不提前解决项目发行许可和精确外部 Java 构建身份。

E08 facade/九选项元数据引用固定elkjs API/worker来源，逐范围身份和版权见[API/metadata来源](references/e08-api-metadata-sources.json)及[执行来源](references/e08-execution-sources.json)。新wheel保留`_licenses/NOTICE-E08.md`和此前所有许可。Python线程/spawn、有界队列、取消、超时及资源清理属于[ADR0007](docs/decisions/0007-e08-api-lifecycle.md)明确的新宿主设计，不声称上游FakeWorker具有这些语义；没有扩大算法来源批准或解决精确外部Java构建身份。

行为参考为固定 elkjs 0.12.1 / `624ae90aa37110033a8af59c5ccbb292708b4317`。
上游 package.json 和源码头的 SPDX 标识是 `EPL-2.0 OR GPL-3.0-or-later`；
原始许可证保存于 [elkjs-LICENSE.md](references/licenses/elkjs-LICENSE.md)。

当前仓库包含自行编写的宿主模型/检查工具、官方元数据快照及E04–E07受限生成源算法移植。
E01新增来源/路径/断言审计与只读内存插桩工具，事实及版权头见 [来源审计](references/e01-source-lineage.md)。官方Java0.12.1标签仅为已锁定候选，未证明其为worker精确构建来源；生成文件每类原始许可头与项目发行许可仍需逐单元处理。
原始 Git/npm 资料存于被忽略的 `.local/`，不进入 Python 产品包。
不得把 py-mermaid 的 MIT 声明直接套到 ELK 源码移植上；逐文件移植前记录来源、版权和适用许可。

本项目自身代码现已选择 MIT，pyproject 按上述混合来源声明 SPDX。
首次对外发行前必须审查选定源码、生成代码、ELK/Guava/GWT 等来源及最终包内容，
完成所需的 LICENSE/NOTICE/源码提供安排；当前开发wheel只在本地验证，未上传。

E04按[ADR0003](docs/decisions/0003-e04-generated-source-slice.md)直接移植固定生成worker的已审支路，[逐组件审批](references/e04-component-approvals.json)绑定原源/独立审查/guard/helper和许可SHA。移植文件保留SPDX、worker身份与原始来源说明；原字节LICENSE及NOTICE位于[src/pyelk/_licenses](src/pyelk/_licenses/NOTICE.md)，实际已安装wheel已核字节。该受限来源闭合不解决精确外部Java build或项目自身发行许可问题。

本页记录来源与发布待办，不构成对许可兼容性的法律结论。

E06环/自环及扩展工作域按[ADR0005](docs/decisions/0005-e06-multigraph.md)逐组件续审，[27组件批准](references/e06-component-approvals.json)保留完整基审、typed依赖和license SHA。新增[NOTICE-E06.md](src/pyelk/_licenses/NOTICE-E06.md)随开发包打包；原LICENSE/NOTICE与E05 notice字节不变。METADATA和全部许可文件均纳入当前包验证，项目自身发行许可与精确外部Java构建仍未解决。

E07方向/组件与新工作域按[ADR0006](docs/decisions/0006-e07-directions-components.md)续审全部33组件，固定原源、完整旧证明与新域依赖见[批准清单](references/e07-component-approvals.json)。新增[NOTICE-E07.md](src/pyelk/_licenses/NOTICE-E07.md)随开发wheel保留，旧四份许可通知字节不变；真实当前包校验全部五份及METADATA。历史包只作字节归档审计，不代表当前包或正式发行许可。
