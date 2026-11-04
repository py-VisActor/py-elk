"""Offline regression for static source indexing; no .local checkout is required."""
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_assertions as audit


class LexicalIndexTests(unittest.TestCase):
    def scan(self, text):
        return audit.scan_source("test/mocha/testOptions.js", text.encode("utf-8"))

    def test_comments_strings_and_regex_are_not_assertions(self):
        result = self.scan(r'''
            // it('comment', () => { expect(1).to.equal(0) })
            const fake = "it('string', () => assert(false))";
            const regexp = /it\("fake",[{}]\)/;
            /* expect(fake).to.exist */
            it('real', function() { assert(true) })
        ''')
        self.assertEqual(result["staticTestCaseSites"], 1)
        self.assertEqual(result["staticAssertionRootSites"], 1)
        self.assertEqual(result["testCases"][0]["assertionSites"][0]["kind"], "assert")

    def test_should_initialization_and_chain_assertions_are_distinct(self):
        result = self.scan('''chai.should();
            it('mixed', function() {
              chai.should();
              return elk.layout(graph).should.eventually.be.fulfilled.then(function() {
                expect(graph).to.have.property('x').that.is.a('number');
                assert(graph.x === 1);
              });
            })''')
        sites = result["testCases"][0]["assertionSites"]
        self.assertEqual([site["kind"] for site in sites], ["should-chain", "expect", "assert"])
        self.assertIn("property", sites[1]["chainProperties"])
        self.assertIn("a", sites[1]["chainProperties"])
        self.assertEqual(len(sites), 3)  # roots, not every Chai predicate

    def test_suite_contexts_and_case_scopes_are_recorded(self):
        result = self.scan("describe('outer', function(){describe('inner',function(){it('one',function(){expect(1).to.equal(1)});it('two',function(){assert(true)})})})")
        self.assertEqual([c["suites"] for c in result["testCases"]], [["outer", "inner"], ["outer", "inner"]])
        self.assertEqual([len(c["assertionSites"]) for c in result["testCases"]], [1, 1])

    def test_nested_test_registration_does_not_duplicate_root_sites(self):
        result = self.scan("it('outer',function(){assert(true);it('inner',function(){expect(1).to.equal(1)})})")
        self.assertEqual(result["staticAssertionRootSites"], 2)
        self.assertEqual([len(c["assertionSites"]) for c in result["testCases"]], [1, 1])

    def test_control_flow_and_dynamic_templates_are_not_expanded(self):
        result = self.scan("for (const x of [1,2]) { it(`name ${x}`,function(){if(x){assert(x)}}) }")
        self.assertEqual(result["staticTestCaseSites"], 1)
        self.assertEqual(result["staticAssertionRootSites"], 1)
        self.assertTrue(result["testCases"][0]["dynamicTitle"])
        self.assertEqual(result["testCases"][0]["controlFlowSites"][0]["kind"], "if")
        self.assertEqual(len(result["opaqueSyntaxSites"]), 1)
        self.assertEqual(result["possibleDynamicRegistrationSites"][0]["kind"], "for")

    def test_skip_only_and_xit_do_not_become_execution_results(self):
        result = self.scan("it.skip('a',function(){assert(false)});it.only('b',function(){assert(true)});xit('c',function(){assert(false)})")
        self.assertEqual([c["mode"] for c in result["testCases"]], ["skip", "only", "skip"])
        self.assertTrue(all(c["executionStatus"] == "not_executed" for c in result["testCases"]))

    def test_utf8_offsets_match_canonical_bytes(self):
        text = "// \u4e2d\u6587\n it('ok',function(){expect(1).to.equal(1)})"
        site = self.scan(text)["testCases"][0]["assertionSites"][0]
        loc = site["location"]
        span = text.encode()[loc["startByte"]:loc["endByte"]]
        self.assertEqual(span, b"expect(1).to.equal(1)")
        self.assertEqual(hashlib.sha256(span).hexdigest(), site["expressionSha256"])
        self.assertEqual(loc["line"], 2)

    def test_quoted_object_keys_and_fake_member_it_are_not_registration(self):
        result = self.scan("var obj={'it': 'fake', 'expect(x)': '{}'};obj.it('no',function(){assert(false)});it('yes',function(){assert(true)})")
        self.assertEqual(result["staticTestCaseSites"], 1)
        self.assertEqual(result["testCases"][0]["title"], "yes")

    def test_unterminated_or_unbalanced_source_fails_closed(self):
        for source in ("/* bad", "it('bad", "it('a',function(){assert(true)", "var r = /bad"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.scan(source)


class CanonicalFixtureTests(unittest.TestCase):
    def make_root(self, root):
        source_path = "test/mocha/testParameters.js"
        data = b"// SPDX-License-Identifier: EPL-2.0 OR GPL-3.0-or-later\nit('required',function(){assert(true)})\n"
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        values = {
            "UPSTREAM.json": {"javascript": {"commit": "a" * 40, "version": "0.12.1", "repository": "https://github.com/kieler/elkjs"}},
            "references/source-inventory.json": {"files": [{"path": source_path, "gitBlob": blob, "category": "test_source"}]},
            "tests/fixtures/validation/cases.json": {"cases": [{"id": "error-missing-graph", "request": "requests/missing.json", "expectedOutcome": "threw"}]},
            "tests/fixtures/validation/requests/missing.json": {"graph": None}
        }
        for path, value in values.items():
            p = root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(value), encoding="utf-8")
        checkout = root / ".local/upstream-elkjs"
        worktree = checkout / source_path
        worktree.parent.mkdir(parents=True, exist_ok=True)
        worktree.write_bytes(b"it('WORKTREE IS NOT CANONICAL',function(){assert(false)})\r\n")

        def fake_git(path, *args):
            self.assertEqual(path, checkout)
            if args[0] == "ls-tree":
                self.assertIn("a" * 40, args)
                return f"100644 blob {blob}\t{source_path}\0".encode()
            self.assertEqual(args, ("show", "a" * 40 + ":" + source_path))
            return data
        return fake_git

    def test_build_reads_locked_git_objects_not_dirty_or_crlf_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_git = self.make_root(root)
            with patch.object(audit, "git", side_effect=fake_git):
                index = audit.build(root)
            self.assertEqual(index["sources"][0]["testCases"][0]["title"], "required")
            self.assertEqual(audit.validate_snapshot(index, root)["staticTestCaseSites"], 1)
            self.assertFalse(index["scanner"]["worktreeTextUsed"])
            self.assertTrue(index["projectCases"][0]["pythonTargets"])

    def test_source_inventory_missing_or_wrong_blob_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_root(root)
            with patch.object(audit, "git", return_value=b"100644 blob wrong\ttest/mocha/other.js\0"):
                with self.assertRaisesRegex(ValueError, "denominator"):
                    audit.build(root)

    def test_offline_snapshot_rejects_fabricated_pass_count_and_case_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(audit, "git", side_effect=self.make_root(root)):
                index = audit.build(root)
            changed = copy.deepcopy(index)
            changed["totals"]["upstreamTestsExecuted"] = 99
            with self.assertRaisesRegex(ValueError, "totals"):
                audit.validate_snapshot(changed, root)
            changed = copy.deepcopy(index)
            changed["sources"][0]["testCases"] = []
            with self.assertRaisesRegex(ValueError, "static counts"):
                audit.validate_snapshot(changed, root)
            changed = copy.deepcopy(index)
            changed["sources"][0]["testCases"][0]["executionStatus"] = "passed"
            with self.assertRaisesRegex(ValueError, "cannot claim"):
                audit.validate_snapshot(changed, root)

    def test_offline_snapshot_rejects_duplicate_ids_or_out_of_range_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(audit, "git", side_effect=self.make_root(root)):
                index = audit.build(root)
            changed = copy.deepcopy(index)
            case = changed["sources"][0]["testCases"][0]
            case["assertionSites"][0]["id"] = case["id"]
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                audit.validate_snapshot(changed, root)
            changed = copy.deepcopy(index)
            changed["sources"][0]["testCases"][0]["location"]["endByte"] = 2 ** 30
            with self.assertRaisesRegex(ValueError, "location"):
                audit.validate_snapshot(changed, root)

    def test_request_hash_and_provenance_drift_are_rejected_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(audit, "git", side_effect=self.make_root(root)):
                index = audit.build(root)
            changed = copy.deepcopy(index)
            changed["projectCases"][0]["origin"] = "upstream"
            with self.assertRaisesRegex(ValueError, "provenance"):
                audit.validate_snapshot(changed, root)
            request = root / index["projectCases"][0]["request"]
            request.write_text('{"graph":{}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                audit.validate_snapshot(index, root)

    def test_generate_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "existing.json"
            existing.write_text("ORIGINAL", encoding="utf-8")
            with patch.object(audit, "build", return_value={"totals": {}}), patch.object(audit, "validate_snapshot"), patch.object(sys, "argv", ["audit_assertions.py", "generate", "--out", str(existing)]), redirect_stdout(io.StringIO()):
                self.assertEqual(audit.main(), 2)
            self.assertEqual(existing.read_text(encoding="utf-8"), "ORIGINAL")

    def test_each_project_execution_or_coverage_promotion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(audit, "git", side_effect=self.make_root(root)):
                index = audit.build(root)
            mutations = [
                lambda p: p.update(pythonExecutionStatus="passed"),
                lambda p: p["pythonTargets"][0].update(status="coordinates_verified"),
                lambda p: p["pythonTargets"][0].update(existsClaimed=True),
                lambda p: p.update(relationship="verified upstream assertion coverage"),
                lambda p: p.update(pythonTargets=[]),
            ]
            for i, mutate in enumerate(mutations):
                with self.subTest(mutation=i):
                    changed = copy.deepcopy(index)
                    mutate(changed["projectCases"][0])
                    with self.assertRaisesRegex(ValueError, "cannot claim"):
                        audit.validate_snapshot(changed, root)

    def test_project_outcome_and_rehashed_request_remain_bound_to_master_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(audit, "git", side_effect=self.make_root(root)):
                index = audit.build(root)
            changed = copy.deepcopy(index)
            changed["projectCases"][0]["expectedOutcome"] = "returned"
            with self.assertRaisesRegex(ValueError, "provenance"):
                audit.validate_snapshot(changed, root)
            changed = copy.deepcopy(index)
            other = root / "tests/fixtures/validation/requests/other.json"
            other.write_text('{"graph":{"id":"other"}}', encoding="utf-8")
            changed["projectCases"][0].update(request=other.relative_to(root).as_posix(), requestSha256=audit.digest(other.read_bytes()))
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                audit.validate_snapshot(changed, root)

    def test_every_mapping_layer_rejects_empty_or_missing_symbol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(audit, "git", side_effect=self.make_root(root)):
                index = audit.build(root)
            selectors = {
                "upstream-case": lambda d: d["sources"][0]["testCases"][0],
                "upstream-assertion": lambda d: d["sources"][0]["testCases"][0]["assertionSites"][0],
                "project-case": lambda d: d["projectCases"][0],
            }
            for layer, select in selectors.items():
                for mutation in ("empty", "missing", "empty-targets", "missing-targets"):
                    with self.subTest(layer=layer, mutation=mutation):
                        changed = copy.deepcopy(index)
                        owner = select(changed)
                        if mutation == "empty":
                            owner["pythonTargets"][0]["symbol"] = ""
                        elif mutation == "missing":
                            owner["pythonTargets"][0].pop("symbol")
                        elif mutation == "empty-targets":
                            owner["pythonTargets"] = []
                        else:
                            owner.pop("pythonTargets")
                        with self.assertRaisesRegex(ValueError, "valid planned Python symbols"):
                            audit.validate_snapshot(changed, root)

    def test_mapping_symbols_are_python_dotted_identifiers(self):
        for symbol in ("pyelk.elk.ELK.layout", "pyelk", "_private._phase2"):
            self.assertTrue(audit.valid_planned_targets([{"symbol": symbol, "status": "planned", "existsClaimed": False}]))
        for symbol in ("pyelk..layout", ".pyelk", "pyelk.", "pyelk.bad name", "pyelk.123", "pyelk.class", " ", None, 42):
            with self.subTest(symbol=symbol):
                self.assertFalse(audit.valid_planned_targets([{"symbol": symbol, "status": "planned", "existsClaimed": False}]))


if __name__ == "__main__":
    unittest.main()
