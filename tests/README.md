# 测试范围

当前E07新增72个官方输入对照、方向与真实NS分量驱动/component阶段回放、九项选项交互及原图几何lemma负控。`check.py`执行全部组，并检查33组件来源/依赖/独立review和当前wheel的全部Python/五许可/METADATA；E04/E05/E06仅做各自历史包审计。完整算法/API/生命周期仍未验收，见[E07手册](../docs/E07_DIRECTIONS_COMPONENTS.md)。下面保留各轮测试的原始职责。

当前 [bootstrap](bootstrap/test_bootstrap.py) 为结构/覆盖分母/来源负控制，不是布局正确性测试。
新增 [validation](validation/test_layout_checks.py) 为真实快照上的比较器/几何/确定性回归。
新增 [audit](audit/test_e01_audit.py) 为来源/断言索引与并行/完成/复盘守卫；局部测试用`-p`限定owner文件，完整discover在root稳定屏障执行。
E02新增 [contract](contract/test_contract_probes.py) 为56组官方合同探针事实/字节身份检查；[profile控制](validation/test_profile_cases.py) 和 [profile实现回归](validation/test_profiles.py) 使用明确标记的合成候选，独立验证适配与拒绝边界。
`audit/test_e02_contract.py`检查冻结规则/探针分母/收据与伪运行时声明；这些都不属于Python算法测试。
其中 synthetic candidate 仅用于验证比较器，不是 Python 算法或兼容证据。
E03新增foundation/model/options/execution，测试实际Python数据模块而非合成candidate；包括typed身份、round-trip、容器/尺寸/端点、替换/别名/默认、跨调用隔离。
E04新增layered/API/conformance，实际执行真实受限算法对21个官方观察及12个数值正例；source绑定/runtime历史收据审计独立验证范围/来源/声明。全部组接入check.py，真实安装对照另用check_e04_slice.py。完整算法/API/生命周期仍未验收。

E05新增36输入真实API/geometry/exact重复与19阶段trace/dummy链恢复，22组件source绑定/依赖/修订基审负控，当前安装收据语义和完整包字节审计。原E04 admission显式调用历史策略，其布局正例仍执行当前Python；E04 runtime audit用归档真实包/声明历史模式，不能借旧wheel认证新src。见[E05手册](../docs/E05_NATIVE_DAG.md)。

```shell
python scripts/check.py --out test-runs/start-01
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python -m unittest discover -s tests/validation -v
python scripts/upstream.py check
```

后续分组：geometry、layered/phases、algorithms、conformance、property、
integration/py-mermaid、lifecycle、packaging、performance。尚未创建成功空测试来填充这些组。
[fixtures](fixtures/README.md)的原始输入、官方输出、规范化结果和差分报告分开保留。
完整验收见 [TEST_AND_RELEASE](../docs/TEST_AND_RELEASE.md)。
官方采集、Python接入、报告和负控制用法见 [布局校验手册](../docs/LAYOUT_VALIDATION.md)。
