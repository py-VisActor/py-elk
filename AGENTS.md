# py-elk 会话入口

实际项目目录为 `C:/code/py-visactor/py-elk`；环境显示 `py-mermaid` 时先定位这里。

先读 [新会话入口](docs/NEW_SESSION.md)、[当前状态](docs/RELEASE_STATUS.md)及 [机器任务状态](docs/implementation-backlog.json)。本文件替代此前叠加的历史进度描述；旧内容保存在 [历史副本](docs/history/AGENTS-before-closure-20261104.txt)，不得按其中旧任务重新实现。

用户目标：完成全部原生 Python ELK 迁移并独立发布 Python 包；py-mermaid 集成后置。用户要求先完成功能，再统一校验修复；修复只运行受影响检查，不反复跑已通过的全量及平台矩阵。

当前正式实现为 `src/pyelk`，包含 196 个 Python 模块、208 个打包运行文件，注册 12 个算法、243 个选项、8 个类别。实现完成与正确性验证分开记录。`.local/migration-next` 为冻结快照，不是当前产品源码。

首个独立发行 `py-visactor-elk 0.1.0` 已完成 GitHub OIDC 发布、PyPI 实际下载及 wheel/sdist 安装；导入仍为 `pyelk`。发行源提交与 tag 为 `bfac8a0` / `v0.1.0`，原始证据见 [实际发行](docs/releases/evidence/published-0.1.0/publication.json)。当前继续 E20/E21 的全声明分支验收。MrTree 控制环已修复；旧 37 步／917 测试属于其冻结的 0.0.1a0 源码，不能认证后续修复，也不能替代所有退出条件。

依照 [并行协作规范](docs/PARALLEL_EXECUTION.md) 使用 root + A/B/V，最多三个 sub-agent。先确定接口与单文件 owner；共享文件仅一个写入者。实现、检查工具和独立审阅可并行，依赖的构建与发行必须顺序执行。每批留下实际交付、检查范围、首败与修复、复盘及下一步。

唯一行为基线为 elkjs 0.12.1 的固定 worker。保留原始 strict 差异、异常、非有限值和 seed=0 宿主熵差异；不要由输入出现、解析通过或少量案例推导完整选项语义通过。不得重写历史执行 SHA 或将旧执行绑定到新源码。

原创代码许可已由用户选定 MIT；实际来源代码按现有通知保留第三方许可，不再重复询问许可。发行配置、上传和下载验收状态单独记录。不要输出凭据。

开发检查按 `docs/iterations/full-native-ci-checks.json` 显式选择；未知影响先补分析，不能自动回退全量。最终完整入口是 `python scripts/check.py --out test-runs/UNIQUE`，仅在全部功能完成后的验收阶段使用。已通过的数学组不因文档或检查工具变更重跑。

CPython 3.11+。在 Windows 使用 PowerShell 和显式工作目录；读取中文文件指定 UTF-8。证据文件的原始字节及现有 `.gitattributes` 规则必须保留。真实 Git index、push、tag、发布只在已有用户授权范围内操作；不根据历史说明新增权限流程。
