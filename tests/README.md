# 测试范围

当前 [bootstrap](bootstrap/test_bootstrap.py) 为结构/覆盖分母/来源负控制，不是布局正确性测试。
新增 [validation](validation/test_layout_checks.py) 为真实快照上的比较器/几何/确定性回归。
其中 synthetic candidate 仅用于验证比较器，不是 Python 算法或兼容证据。

```shell
python scripts/check.py --out test-runs/start-01
python scripts/validate_bootstrap.py
python -m unittest discover -s tests/bootstrap -v
python -m unittest discover -s tests/validation -v
python scripts/upstream.py check
```

后续分组：contract、model、options、geometry、layered/phases、algorithms、conformance、property、
integration/py-mermaid、lifecycle、packaging、performance。尚未创建成功空测试来填充这些组。
[fixtures](fixtures/README.md)的原始输入、官方输出、规范化结果和差分报告分开保留。
完整验收见 [TEST_AND_RELEASE](../docs/TEST_AND_RELEASE.md)。
官方采集、Python接入、报告和负控制用法见 [布局校验手册](../docs/LAYOUT_VALIDATION.md)。
