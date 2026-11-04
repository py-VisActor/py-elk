# 15 批执行 brief

承接 [14 批](../changes/20261104-next-native-14.json)，固定 154 文件 `3d6e0431fd40b03ba52b5dc28e420f222d6df9f47dc7fb122df16e6cfa8cf4ef`。14 批保存 366 份新增材料、10 份范围限定代码审查。开发仅变更校验，全部功能完成后再全量。

| owner | 单写范围 | 下一交付 |
| --- | --- | --- |
| A | native_import_full/native_transfer/provider/factories | outer 与 transfer、flat driver 已源审；Long/End 已代码独审。接真实默认 19 槽及 Session exporter，复用已保存的唯一完整原版请求，交首次完整 native 调用 |
| B | self_loops_general | 已验 holder/pre/post/side assignment；接共享 enum identity，复用真正 Ortho cycle callee，完成 Restorer/Slot/Router。RoutingDirector 完整源已由 Root 分担 |
| Root | execution/metadata/components、许可与归档 | 配合 A 入口接线、独审 B 新 caller，推进真实 connected Compactor。保留外部 placer 原始 23 项顺序差异，核实际调用影响；不以重新排序的见证替代 raw gate |
| V | 独立源/代码/新增原版对象 | 优先 A 新 outer/transfer 与完整首调用、B Restorer/Slot。复用现有源审，避免将无变化模块重新执行 |

A/B 在自己文件内推进，不等待归档。新完整入口只能依赖真实实现；尚未批准的高级策略明确报 pending，不能静默代用旧受限阶段。源码批准、代码审查、实际对照、整个算法验收四者分别记录。

项目原创 MIT 决定已落实，实际开发 wheel/sdist 许可字节已核；不升级版本或上传。用户进一步认为移植部分属于完全重写，当前来源记录与部分代码却标为机械/逐函数移植，需按实际证据核对。不能仅靠替换文件头认定全部实现纯 MIT，也不能把所有读取过上游的原创文件一概归为衍生作品。原许可声明在事实厘清前保留。
