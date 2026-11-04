# E11 发行许可决定

2026-11-04 用户明确选择 **MIT**，取代下方尚未生效的 EPL-2.0 拟案。项目自行编写的代码采用根目录 [LICENSE](../LICENSE)；第三方移植文件继续保留原有许可、版权、来源和通知。整个发行包的 SPDX 表达式为 `MIT AND (EPL-2.0 OR GPL-3.0-or-later) AND Apache-2.0`，根目录 MIT 不对第三方文件重新许可。机器决定见 [0009](decisions/0009-project-license.json)，校验方法见[许可变更校验](iterations/LICENSE_VALIDATION.md)。

本次决定不更改历史包与通知，不提升版本、不代表已发布。正式发行仍须核源码与实际包内容；精确外部 Java 构建身份仍 unresolved。以下保留原拟案供追溯，已经被本段决定替代，不再作为执行方案。

用户进一步明确：完全独立重写的实现采用 MIT。这里按文件的实际实现来源区分：独立设计和实现的 Python 文件可以归入项目 MIT；目前仍有按上游函数结构、分支和运算顺序移植的文件，不能仅因换成 Python 或重写了语法就将其标为独立实现。逐文件确认替换后，再同步调整声明、第三方清单和发行表达式；当前保留这些文件的通知，不把整个迁移目录一概视为上游代码或一概改为 MIT。

## 已被替代的历史拟案

状态：供发行阶段决定与复核，尚未写入项目 LICENSE 或发布包，不代表已选择项目许可。当前来源事实见 THIRD_PARTY_NOTICES 和逐组件批准；[E11 brief](iterations/E11.md)规定先核许可再冻结候选。

拟采用的具体配置：项目新编写的 Python 宿主与工具使用 EPL-2.0；移植文件继续保留原有 SPDX、来源身份及版权通知。顶层 LICENSE 使用已保存的 EPL-2.0 正文，pyproject 使用 `license = "EPL-2.0"` 并明确打包 LICENSE 和既有通知；不将上游原始 SPDX 改写成项目自行创设的许可。最终 sdist 提供对应 Python 源码，wheel 保留所有适用许可与 NOTICE，metadata 声明源仓库及已验证支持范围。

这一方案使项目发行明确选择上游提供的 EPL 路径；不假定附带 Exhibit A 本身即可把其他代码自动转成 GPL 次级许可。官方正文和说明见 [EPL-2.0](https://www.eclipse.org/legal/epl-2.0/)；本仓库保存的原始上游文本位于 [elkjs-LICENSE.md](../references/licenses/elkjs-LICENSE.md)。逐单元的第三方义务仍须核对，不能仅靠顶层 SPDX 代替完整来源与版权盘点。

正式候选前需要落实：项目自身代码许可的发行决定；第三方来源与通知完整性复核；顶层 LICENSE、pyproject、实际 wheel/sdist 包内容及源码提供信息一致。精确外部 Java 构建身份仍标 unresolved，发布说明不得将候选 Java tag 描述为已证明的原 worker 构建输入。

该拟案不改变当前 E10 包及原收据；决定落实后由 root 一次修改版本/许可/README，并按包变更做必要安装验收，不重新运行无关算法矩阵。
