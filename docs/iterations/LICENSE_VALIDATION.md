# MIT 决定与变更校验

2026-11-04 用户选择项目原创代码 MIT；原始移植许可和版权保持不变。根 LICENSE、机器决定、pyproject 与当前说明必须一致。历史检查点及已执行包按原 SHA 保存，不重绑。

在仓库根目录执行：

```shell
python scripts/iteration/project_license.py --out test-runs/license-new/source.json
```

该入口仅核许可、打包声明和正式 src 的历史 AST 一致性，不要求将开发版本提前改成稳定版本。构建一个新的开发 wheel/sdist 后，可追加 `--wheel PATH --sdist PATH`，核验实际 METADATA、包源码及全部许可字节。构建仅为本地变更校验，不上传，不重跑布局矩阵。

正式候选仍使用 `scripts/iteration/e11_package.py`，保留稳定版本门禁。本次许可选择不解除剩余功能、安装与发行验收要求。全量只在全部迁移功能完成之后运行。
