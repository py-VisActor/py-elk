"""Historical E11 AST boundary; full-native packages use their own verifier."""
import ast
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import e11_package
from e11_history import material


class ReleaseSourceBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Authenticate the sealed original product instead of rebinding its
        # release-only AST gate to the later full-native implementation.
        files=material(ROOT)
        cls.directory=tempfile.TemporaryDirectory(prefix='pyelk-e11-original-source-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.historical=Path(cls.directory.name)
        for name,raw in files.items():
            if name.startswith('src/pyelk/'):
                target=cls.historical/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        baseline=cls.historical/e11_package.BASE;baseline.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/e11_package.BASE,baseline)

    def test_actual_license_only_phase_change_preserves_all_runtime_ast(self):
        old,signatures=e11_package.runtime_unchanged(self.historical)
        self.assertEqual(len(signatures),35)
        self.assertEqual(len(old),43)

    def test_changed_mathematics_and_new_module_require_a_new_check_plan(self):
        with tempfile.TemporaryDirectory(prefix='py-elk-e11-source-') as folder:
            root=Path(folder);baseline=root/e11_package.BASE;baseline.parent.mkdir(parents=True)
            shutil.copy2(self.historical/e11_package.BASE,baseline)
            shutil.copytree(self.historical/'src/pyelk',root/'src/pyelk',ignore=shutil.ignore_patterns('__pycache__'))
            e11_package.runtime_unchanged(root)
            phases=root/'src/pyelk/algorithms/layered/phases.py';original=phases.read_bytes()
            tree=ast.parse(original);binary=next(n for n in ast.walk(tree) if isinstance(n,ast.BinOp))
            binary.op=ast.Mult() if isinstance(binary.op,ast.Add) else ast.Add()
            phases.write_text(ast.unparse(tree),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'Runtime AST changed'):e11_package.runtime_unchanged(root)
            phases.write_bytes(original)
            (root/'src/pyelk/unknown_algorithm.py').write_text('pass\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'module additions/removals'):e11_package.runtime_unchanged(root)


if __name__=='__main__':unittest.main()
