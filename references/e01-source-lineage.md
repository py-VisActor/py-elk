# E01-A：来源、构建生成关系与许可头审计

状态：调查批次已交付，`algorithm-source`门禁仍为 **unverified**。
机器记录见 [e01-source-lineage.json](e01-source-lineage.json)。本轮没有移植算法源码，没有改变上游基线，也没有形成发行许可结论。

## 已确证的发行链

1. elkjs固定提交为`624ae90aa37110033a8af59c5ccbb292708b4317`。Git树已跟踪`lib/elk-worker.js`、bundled入口等文件，尽管`.gitignore`也列有`lib/`；不能从忽略规则推断这些文件未进入提交。
2. npm tarball中的**12个文件**逐一与上述提交的canonical Git blob核对，SHA256全部相同。worker为`275e6caf4af71c06f5afd673939bdb4c9a0edf6ad97b32476cb7bc6cfdc09d86`，bundled为`b1032b7cfd2a57c54c6f0e8369d7665e19a579954f7cd20a6dae28f1912ea0d7`。
3. npm公开的SLSA payload以elkjs0.12.1为subject，SHA512与已锁tarball相同；resolvedDependencies记录上述elkjs提交，workflow为`.github/workflows/publish.yml`，invocation为run`40687425972`。本轮解析元数据并核对摘要，**没有执行签名证书/透明日志的密码学验证**。[npm provenance原始入口](https://registry.npmjs.org/-/npm/v1/attestations/elkjs@0.12.1)
4. 该发布run为release事件、成功、head为固定提交。job步骤为checkout、setup-node、npm publish及清理，未包含外部Java checkout或Java/GWT构建。[实际发布运行](https://github.com/kieler/elkjs/actions/runs/40687425972)
5. 固定提交祖先中，worker最近一次引入提交是`73ae7182e8ecfd7c53bfbdad2f63ad1ca77dbd98`，消息为“add lib files for 0.12.1 release”。因此发布工作流从已经进入Git的生成文件打包，而不是在该run中生成worker。[生成文件引入提交](https://github.com/kieler/elkjs/commit/73ae7182e8ecfd7c53bfbdad2f63ad1ca77dbd98)

结论限于“发行物等于固定Git生成文件，发布元数据与其身份一致”。它不证明更早的Java/GWT编译使用了哪一个外部Java提交。

## 构建定义与Java候选

固定[build.gradle](https://github.com/kieler/elkjs/blob/624ae90aa37110033a8af59c5ccbb292708b4317/build.gradle)的64–82行从外部`../elk`取core/graph/JSON/common和算法源码；208–255行实施排除、预处理与GWT适配器替换；275–288行定义PRETTY/minified GWT输出；314–322行定义生成顺序。
其版本表包含GWT2.13.0、Guava31.1-jre、MELK0.13.0-SNAPSHOT，属于声明，不是当时解析到的全部依赖字节清单。
固定[CI配置](https://github.com/kieler/elkjs/blob/624ae90aa37110033a8af59c5ccbb292708b4317/.github/workflows/ci.yml)选择外部`eclipse/elk`的`master`；这一单独的CI定义不能自动解释已提交的release worker。

elkjs[0.12.1发布说明](https://github.com/kieler/elkjs/releases/tag/0.12.1)明确声称基于ELK0.12.1。
官方Java仓库现为`eclipse-elk/elk`，原`eclipse/elk`地址重定向；[v0.12.1标签](https://github.com/eclipse-elk/elk/releases/tag/v0.12.1)锁定到：

```text
3aa3b9fb98d8f9a41285b3061cff5efe79ed2ba4
```

本轮将该tag作为**已锁定的可读候选**下载到新的`.local/e01-java-v0.12.1`，没有改动原elkjs或npm资料。
索引记录了ElkLayered、GraphConfigurator、Layered.melk、LayeredLayoutProvider、GreedyCycleBreaker、NetworkSimplexLayerer、LayerSweepCrossingMinimizer、BKNodePlacer、OrthogonalEdgeRouter、Core.melk、RecursiveGraphLayoutEngine，以及LICENSE/NOTICE/DEPENDENCIES共14份canonical文件的blob/SHA256。
发布版本声明、tag身份及源码可读性均已核实；候选Java提交与发行worker的准确构建对应关系仍未核实。

## 已锁定组件与可用范围

| 组件 | 已核实身份 | 仍需单独核实 |
| --- | --- | --- |
| JS API/Node入口 | 固定elkjs提交中的实际源文件及SPDX | Python宿主适配和公开合同，交E02 |
| Java桥接/GWT JSON adapter | 固定elkjs提交、canonical SHA和版权/SPDX | 完整构建未重现；导入/布局/回填语义仍需逐断言移植 |
| 生成worker/bundled | 固定Git生成文件与npm字节一致 | 生成前外部Java和实际解析依赖 |
| 可读layered/core | 官方v0.12.1候选提交及选定文件SHA/许可头 | 不能整体冒充worker的确切Java构建提交 |

JSON adapter实际使用elkjs的`src/java-additional/.../JsonAdapter.xtend`替换；不能把被构建排除的Gson版本当成这一执行路径的直接来源。
后续可用固定生成worker作为可追溯的行为/实现证据，并用Java候选解释组件；每个机械移植单元还须记录其实际使用的源文件、符号、语义对照、版权和依赖边界。

## 许可头事实

固定elkjs API/Java桥接/JSON adapter的源头，以及所选Java候选算法文件的SPDX均为`EPL-2.0 OR GPL-3.0-or-later`；具体版权行按文件保存在机器索引中。
候选根LICENSE、NOTICE、DEPENDENCIES都已锁SHA；NOTICE也声明上述SPDX。[候选NOTICE](https://github.com/eclipse-elk/elk/blob/3aa3b9fb98d8f9a41285b3061cff5efe79ed2ba4/NOTICE.md)
生成worker不保留每个编译类的原文件许可头，因此不能仅用npm顶层声明完成所有被移植组件的许可处理。
本轮只记录来源声明，没有把Java/GWT实现复制进Python，也未将py-mermaid许可套用到本项目。
发行前仍按实际复用组件处理版权、NOTICE、源码提供安排及本项目发行许可；这些是待办，不是本页给出的法律兼容性判断。

## open项与具体下一步

- **A-O01：Java构建提交。** 调查worker引入提交`73ae718...`对应的预生成构建日志/来源说明；若不能恢复，按组件比对固定Java候选与固定生成符号，保留局部证据，整体exactJavaCommit维持unresolved。
- **A-O02：生成依赖。** 寻找当时Gradle解析清单或构建记录，尤其MELK SNAPSHOT；另做复现时固定依赖SHA，并把复现身份与原发行物构建身份分开。不同编译产物字节本身不能直接证明Java来源不同。
- **A-O03：实际移植与发行许可。** 每个组件移植前记录代码/行为复用方式与版权；正式发行前审查真实包内容并落实LICENSE/NOTICE等安排。

E01调查交付可以完成；E02合同和E03模型可继续。算法机械移植和最终发行的来源/许可门禁不能因此自动通过。

## 原始证据与协作改进输入

命令、HTTP响应、connector响应、候选源码和校验结果保存在`test-runs/20261103-E01-01/A`；持久化JSON内含5份精简主来源receipt及源身份。
初次公共GitHub REST受共享IP限流返回403，npm因错误Accept头返回406，均已保留；改用认证GitHub connector和正确npm Accept后成功。
建议后续轮次优先使用认证connector、分别管理GitHub/npm请求头，并在来源审计中检查实际发布workflow及已跟踪生成文件，避免只读CI和.gitignore形成不完整推断。
