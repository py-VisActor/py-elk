"""Independent mutation and isolation guards for per-source-check reads."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_checks
from source_read_cache import readonly_source_check


def report():
    return {"status": "PASS", "errors": [], "wholeSourceApproved": True, "canonicalVerified": True}


class SourceReadScopeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "source.json"
        self.path.write_bytes(b'{"value": 1, "items": [1, 2]}\n')

    def test_plain_load_returns_fresh_mutable_objects(self):
        first = layout_checks.load(self.path)
        first["items"].append(99)
        self.assertEqual(layout_checks.load(self.path)["items"], [1, 2])

    def test_nested_checks_parse_once_and_outer_exit_rechecks_bytes(self):
        calls = []
        original = layout_checks._parse_json
        def parse(text):
            calls.append(text)
            return original(text)
        @readonly_source_check
        def inner():
            self.assertEqual(layout_checks.load(self.path)["value"], 1)
            self.assertEqual(layout_checks.sha256(self.path), hashlib.sha256(self.path.read_bytes()).hexdigest())
            return report()
        @readonly_source_check
        def outer():
            layout_checks.load(self.path)
            self.assertEqual(inner()["errors"], [])
            layout_checks.load(self.path)
            return report()
        with patch.object(layout_checks, "_parse_json", parse):
            self.assertEqual(outer()["errors"], [])
            self.assertEqual(len(calls), 1)
            self.assertEqual(outer()["errors"], [])
            self.assertEqual(len(calls), 2)

    def test_each_call_reads_same_size_same_mtime_mutation(self):
        @readonly_source_check
        def check():
            result = report()
            result["value"] = layout_checks.load(self.path)["value"]
            return result
        self.assertEqual(check()["value"], 1)
        stamp = self.path.stat().st_mtime_ns
        self.path.write_bytes(self.path.read_bytes().replace(b'"value": 1', b'"value": 9'))
        os.utime(self.path, ns=(stamp, stamp))
        self.assertEqual(check()["value"], 9)

    def test_exit_rejects_file_change_even_when_hash_was_previously_read(self):
        @readonly_source_check
        def check():
            layout_checks.load(self.path)
            layout_checks.sha256(self.path)
            self.path.write_bytes(self.path.read_bytes().replace(b'"value": 1', b'"value": 9'))
            return report()
        value = check()
        self.assertEqual(value["status"], "FAIL")
        self.assertIn("bytes/path changed", " ".join(value["errors"]))
        self.assertIs(value["wholeSourceApproved"], False)
        self.assertIs(value["canonicalVerified"], False)

    def test_exit_rejects_deleted_input(self):
        @readonly_source_check
        def check():
            layout_checks.load(self.path)
            self.path.unlink()
            return report()
        self.assertIn("disappeared", " ".join(check()["errors"]))

    def test_exit_rejects_atomic_file_replacement(self):
        @readonly_source_check
        def check():
            layout_checks.load(self.path)
            replacement = self.root / "replacement.json"
            replacement.write_bytes(b'{"value":9}')
            os.replace(replacement, self.path)
            return report()
        self.assertIn("bytes/path changed", " ".join(check()["errors"]))

    def test_symbolic_path_retarget_is_detected_even_for_equal_bytes(self):
        other = self.root / "other.json"
        other.write_bytes(self.path.read_bytes())
        alias = self.root / "alias.json"
        try:
            alias.symlink_to(self.path)
        except (OSError, NotImplementedError):
            self.skipTest("This host cannot create symbolic links")
        @readonly_source_check
        def check():
            layout_checks.load(alias)
            alias.unlink()
            alias.symlink_to(other)
            return report()
        self.assertIn("bytes/path changed", " ".join(check()["errors"]))

    def test_exit_rejects_in_memory_input_mutation_and_next_call_is_fresh(self):
        @readonly_source_check
        def bad():
            layout_checks.load(self.path)["items"].append(99)
            return report()
        value = bad()
        self.assertEqual(value["status"], "FAIL")
        self.assertIn("JSON data changed", " ".join(value["errors"]))
        self.assertEqual(layout_checks.load(self.path)["items"], [1, 2])

    def test_type_pollution_fails_closed(self):
        @readonly_source_check
        def bad():
            layout_checks.load(self.path)["items"].append(object())
            return report()
        self.assertIn("JSON data changed", " ".join(bad()["errors"]))

    def test_json_equivalent_tuple_and_integer_key_mutations_are_rejected(self):
        self.path.write_bytes(b'{"value":1,"items":[1,2],"1":1}\n')
        for mutate in (lambda d:d.update(items=tuple(d["items"])),
                       lambda d:d.__setitem__(1,d.pop("1"))):
            @readonly_source_check
            def bad():
                data=layout_checks.load(self.path)
                before=json.dumps(data)
                mutate(data)
                self.assertEqual(json.dumps(data),before)
                return report()
            value = bad()
            self.assertEqual(value["status"],"FAIL")
            self.assertIn("JSON data changed"," ".join(value["errors"]))

    def test_json_equivalent_container_subclass_is_rejected(self):
        class DerivedList(list):
            pass
        @readonly_source_check
        def bad():
            data=layout_checks.load(self.path)
            before=json.dumps(data)
            data["items"]=DerivedList(data["items"])
            self.assertEqual(json.dumps(data),before)
            return report()
        self.assertIn("JSON data changed"," ".join(bad()["errors"]))

    def test_cycle_introduced_in_memory_returns_normal_failure(self):
        @readonly_source_check
        def bad():
            data=layout_checks.load(self.path)
            data["items"].append(data)
            return report()
        self.assertIn("JSON data changed"," ".join(bad()["errors"]))

    def test_bad_json_duplicate_keys_nonfinite_and_missing_are_not_cached(self):
        @readonly_source_check
        def read():
            return layout_checks.load(self.path)
        self.assertEqual(read()["value"], 1)
        for raw in (b'{', b'{"value":1,"value":2}', b'{"value":NaN}'):
            self.path.write_bytes(raw)
            with self.assertRaises(ValueError):
                read()
        self.path.unlink()
        with self.assertRaises(OSError):
            read()
        self.path.write_bytes(b'{"value":7}')
        self.assertEqual(read()["value"], 7)

    def test_exception_clears_scope(self):
        @readonly_source_check
        def broken():
            layout_checks.load(self.path)["value"] = 99
            raise RuntimeError("independent failure")
        with self.assertRaisesRegex(RuntimeError, "independent failure"):
            broken()
        self.assertEqual(layout_checks.load(self.path)["value"], 1)

    def test_different_roots_do_not_share_by_relative_name(self):
        other = self.root / "other/source.json"
        other.parent.mkdir()
        other.write_bytes(b'{"value":8}')
        @readonly_source_check
        def check():
            self.assertEqual(layout_checks.load(self.path)["value"], 1)
            self.assertEqual(layout_checks.load(other)["value"], 8)
            return report()
        self.assertEqual(check()["errors"], [])

    def test_thread_with_copied_context_gets_independent_scope(self):
        @readonly_source_check
        def child():
            self.assertEqual(layout_checks.load(self.path)["items"], [1, 2])
            return report()
        @readonly_source_check
        def parent():
            parsed = layout_checks.load(self.path)
            parsed["items"].append(99)
            context = copy_context()
            with ThreadPoolExecutor(max_workers=1) as pool:
                value = pool.submit(context.run, child).result()
            self.assertEqual(value["errors"], [])
            parsed["items"].pop()
            return report()
        self.assertEqual(parent()["errors"], [])

    def test_async_task_does_not_reuse_inherited_completed_scope(self):
        async def execute():
            @readonly_source_check
            def parent():
                layout_checks.load(self.path)
                async def child():
                    return layout_checks.load(self.path)["value"]
                result = report()
                result["task"] = asyncio.create_task(child())
                return result
            value = parent()
            self.path.write_bytes(b'{"value":7}')
            return await value["task"]
        self.assertEqual(asyncio.run(execute()), 7)

    def test_literal_source_symbol_checks_do_not_reuse_decisions(self):
        from validate_e07_source_bindings import validate_symbol_bindings
        raw = b'function real() { return 1; }\n'
        source = {"sourceId":"test"}
        span = {"sourceId":"test", "symbol":"real", "startLine":1,"endLine":1,
                "spanSha256":hashlib.sha256(raw).hexdigest(),
                "functionStartOffset":0,"functionEndOffset":len(raw)-1}
        document = {"sources":[source], "entrySpans":[span]}
        @readonly_source_check
        def check():
            return validate_symbol_bindings(document, {"test":raw})
        result = check()
        self.assertEqual(result["newSemanticLabelExceptions"], 0)
        self.assertEqual(result["literalSymbolCount"], 1)
        span["symbol"] = "invented"
        with self.assertRaisesRegex(ValueError, "function symbol"):
            check()

    def test_prepared_canonical_text_preserves_utf16_and_token_guards(self):
        from validate_e04_source_bindings import validate_canonical
        from validate_e05_source_bindings import validate_function_line_alignment
        from validate_e06_source_bindings import validate_symbol_bindings as legacy_symbols
        from validate_e07_source_bindings import validate_symbol_bindings
        prefix = "// \U0001f600\n"
        body = "function real() { return 1; }"
        raw = (prefix + body + "\n").encode("utf-8")
        start = len(prefix.encode("utf-16-le")) // 2
        span = {"sourceId":"test", "symbol":"real", "startLine":2,"endLine":2,
                "spanSha256":hashlib.sha256((body+"\n").encode()).hexdigest(),
                "functionStartOffset":start,"functionEndOffset":start+len(body),
                "functionSha256":hashlib.sha256(body.encode()).hexdigest(), "offsetUnit":"UTF-16 code units"}
        document = {"lane":"R", "sources":[{"sourceId":"test", "sha256":hashlib.sha256(raw).hexdigest()}],
                    "entrySpans":[span]}
        blobs = {"test":raw}
        self.assertEqual(validate_canonical(document,blobs)["functionOffsetOccurrences"],1)
        validate_function_line_alignment(document,blobs)
        self.assertEqual(legacy_symbols(document,blobs)["literalSymbolCount"],1)
        self.assertEqual(validate_symbol_bindings(document,blobs)["literalSymbolCount"],1)
        span["symbol"]="imaginary"
        with self.assertRaisesRegex(ValueError,"function symbol"):
            legacy_symbols(document,blobs)
        with self.assertRaisesRegex(ValueError,"function symbol"):
            validate_symbol_bindings(document,blobs)
        span["symbol"]="real"
        span["functionStartOffset"]=4  # Split the supplementary code point.
        with self.assertRaises(UnicodeError):
            validate_function_line_alignment(document,blobs)
