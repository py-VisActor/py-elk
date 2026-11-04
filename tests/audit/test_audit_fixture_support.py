"""Read-set and mutation controls for sparse audit fixture construction."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_fixture_support import copy_files, e01_paths, record_reads, runtime_paths
import test_e05_runtime as e05
import test_e06_runtime as e06
import test_e07_runtime as e07
from validate_e01_audit import check as check_e01


class AuditFixtureDependencyTests(unittest.TestCase):
    def test_all_runtime_positive_copies_have_their_entire_actual_read_set(self):
        for iteration, module in (("E05", e05), ("E06", e06), ("E07", e07)):
            with self.subTest(iteration=iteration), module.offline_copy() as root:
                with record_reads(root) as reads:
                    result = module.check(root)
                self.assertEqual(result["errors"], [], result)
                present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
                self.assertTrue(reads)
                self.assertLessEqual(reads, present)
                self.assertFalse(any("oracle" in Path(name).parts for name in present))
                self.assertFalse((root / "test-runs").exists())

    def test_e01_positive_copy_has_all_plan_evidence_and_original_master_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copied = copy_files(ROOT, root, e01_paths(ROOT))
            with record_reads(root) as reads:
                result = check_e01(root)
            self.assertEqual(result["errors"], [], result)
            self.assertTrue(reads)
            self.assertLessEqual(reads, set(copied["paths"]))
            self.assertFalse((root / "tests/fixtures/suites").exists())

    def test_mutating_a_copied_file_never_changes_the_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source, target = directory / "source", directory / "copy"
            source.mkdir()
            original = source / "receipt.json"
            original.write_bytes(b'{"immutable":true}\n')
            copied = copy_files(source, target, {"receipt.json"})
            self.assertEqual(copied["copiedFiles"], 1)
            self.assertEqual(copied["copiedBytes"], original.stat().st_size)
            self.assertFalse(original.samefile(target / "receipt.json"))
            with self.assertRaises(FileExistsError):
                copy_files(source, target, {"receipt.json"})
            (target / "receipt.json").write_bytes(b"mutant\n")
            self.assertEqual(original.read_bytes(), b'{"immutable":true}\n')

    def test_missing_and_escaping_declared_dependencies_fail_immediately(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source, target = directory / "source", directory / "copy"
            source.mkdir()
            for name in ("../outside", "/outside", "a/../outside", "a\\outside"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    copy_files(source, target, {name})
            with self.assertRaises(FileNotFoundError):
                copy_files(source, target, {"missing.json"})
            with self.assertRaises(ValueError):
                copy_files(source, source, {"receipt.json"})

    def test_every_selected_request_and_current_package_file_is_retained(self):
        from layout_checks import load
        for iteration, count in (("E05", 36), ("E06", 52), ("E07", 72)):
            selected = runtime_paths(ROOT, iteration)
            suite = Path("tests/fixtures/suites") / iteration
            rows = load(ROOT / suite / "cases.json")["cases"]
            self.assertEqual(len(rows), count)
            self.assertTrue(all((suite / row["request"]).as_posix() in selected for row in rows))
        selected = runtime_paths(ROOT, "E07")
        package = {p.relative_to(ROOT).as_posix() for p in (ROOT / "src/pyelk").rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
        self.assertLessEqual(package, selected)

    def test_a_missing_indirect_seed_dependency_cannot_be_mistaken_for_a_semantic_rejection(self):
        with e07.offline_copy() as root:
            self.assertEqual(e07.check(root)["errors"], [])
            (root / "references/e03-option-sources.json").unlink()
            result = e07.check(root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("references/e03-option-sources.json", " ".join(result["errors"]))


if __name__ == "__main__":
    unittest.main()
