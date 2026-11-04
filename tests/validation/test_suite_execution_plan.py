"""Request-sharing controls. Synthetic contexts never count as engine evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import plan_suite_execution as sharing
from layout_checks import load


def synthetic_context(role="candidate"):
    return {"schema": "py-elk-execution-context/v1", "role": role, "nonce": "one-run",
            "identity": {"wheelSha256": "1" * 64, "name": "pyelk" if role == "candidate" else "elkjs"},
            "argvTemplate": ["actual-engine", "<REQUEST>", "<OBSERVATION>"],
            "environmentSha256": "2" * 64, "environmentPolicy": "synthetic-test-only",
            "environmentEvidence": {"synthetic-test-only": True},
            "workingDirectory": str(ROOT), "actualExecutionRoot": "synthetic-test-only",
            "projectFilesSha256": {"pyproject.toml": "4"*64, "README.md": "5"*64},
            "sourceSha256": {"adapter.py": "3" * 64}}


class SuiteExecutionPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = sharing.build_plan()

    def test_full_denominators_and_exact_duplicate_grouping(self):
        self.assertEqual(self.plan["caseCount"], 181)
        self.assertEqual(self.plan["uniqueRequests"], 149)
        self.assertEqual(self.plan["duplicateRequestsPerEngineRepeat"], 32)
        self.assertEqual({k:len(v["cases"]) for k,v in self.plan["suites"].items()}, sharing.COUNTS)
        self.assertEqual(sum(len(v["members"]) for v in self.plan["requests"].values()), 181)
        for fingerprint, group in self.plan["requests"].items():
            raw = (ROOT / group["request"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), fingerprint)
            for member in group["members"]:
                case = next(c for c in self.plan["suites"][member["suite"]]["cases"] if c["caseId"] == member["caseId"])
                self.assertEqual((ROOT / case["request"]).read_bytes(), raw)

    def test_equal_json_with_different_original_bytes_is_not_same_execution_key(self):
        a, b = b'{"graph":{}}', b'{ "graph": {} }\n'
        self.assertEqual(json.loads(a), json.loads(b))
        self.assertNotEqual(sharing.execution_key(hashlib.sha256(a).hexdigest(), synthetic_context(), 0),
                            sharing.execution_key(hashlib.sha256(b).hexdigest(), synthetic_context(), 0))

    def test_each_repeat_and_role_has_its_own_process_slot(self):
        fingerprint = next(iter(self.plan["requests"]))
        keys = {sharing.execution_key(fingerprint, synthetic_context(role), i) for role in ("reference","candidate") for i in range(3)}
        self.assertEqual(len(keys), 6)

    def test_no_reuse_mode_really_keeps_every_case_process_slot(self):
        contexts={role:synthetic_context(role) for role in ("reference","candidate")}
        independent=sharing._jobs(self.plan,contexts,3,False)
        shared=sharing._jobs(self.plan,contexts,3,True)
        independent_keys={sharing.execution_key(h,contexts[role],i,scope) for h,_,scope,role,i in independent}
        shared_keys={sharing.execution_key(h,contexts[role],i,scope) for h,_,scope,role,i in shared}
        self.assertEqual(len(independent),1086)
        self.assertEqual(len(independent_keys),1086)
        self.assertEqual(len(shared),894)
        self.assertEqual(len(shared_keys),894)
        self.assertTrue(independent_keys.isdisjoint(shared_keys))

    def test_unknown_or_mixed_case_scope_is_rejected(self):
        fingerprint=next(iter(self.plan["requests"]))
        for scope in ({"kind":"case","suite":"E99","caseId":"x"},{"kind":"case","suite":"E07"},
                      {"kind":"request","caseId":"ignored"},[],"request"):
            with self.assertRaisesRegex(ValueError,"scope"):
                sharing.execution_key(fingerprint,synthetic_context(),0,scope)

    def test_every_relevant_engine_identity_change_invalidates_the_slot(self):
        fingerprint = next(iter(self.plan["requests"]))
        context = synthetic_context()
        initial = sharing.execution_key(fingerprint, context, 0)
        for mutate in (lambda c:c.update(nonce="another-run"),
                       lambda c:c.update(environmentSha256="9"*64),
                       lambda c:c.update(environmentEvidence={"changed":"actual-environment-policy"}),
                       lambda c:c["identity"].update(wheelSha256="8"*64),
                       lambda c:c["sourceSha256"].update(**{"adapter.py":"7"*64}),
                       lambda c:c.update(argvTemplate=["another-engine","<REQUEST>","<OBSERVATION>"]),
                       lambda c:c.update(actualExecutionRoot="another-path")):
            value=copy.deepcopy(context);mutate(value)
            self.assertNotEqual(sharing.execution_key(fingerprint,value,0),initial)

    def test_unknown_missing_context_and_bad_repetition_fail_closed(self):
        fingerprint = next(iter(self.plan["requests"]))
        for key in ("nonce","identity","argvTemplate","environmentSha256","environmentPolicy","environmentEvidence","workingDirectory","sourceSha256","actualExecutionRoot","projectFilesSha256"):
            context=synthetic_context();context.pop(key)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"Incomplete"):
                sharing.execution_key(fingerprint,context,0)
        for role in ("unknown","python","reference-old"):
            context=synthetic_context();context["role"]=role
            with self.assertRaisesRegex(ValueError,"Unknown"):
                sharing.execution_key(fingerprint,context,0)
        for repetition in (-1,True,1.0,None):
            with self.assertRaisesRegex(ValueError,"repetition"):
                sharing.execution_key(fingerprint,synthetic_context(),repetition)

    def test_plan_keeps_each_independent_geometry_policy(self):
        masters = [c for s in self.plan["suites"].values() for c in s["cases"] if c["caseId"]=="layered-chain"]
        self.assertGreater(len(masters),1)
        self.assertEqual(len({c["requestSha256"] for c in masters}),1)
        self.assertTrue(any(c["definition"]["geometry"].get("rankSeparation")=="default-layered-components-v2" for c in masters))
        self.assertTrue(any("rankSeparation" not in c["definition"]["geometry"] for c in masters))

    def test_no_engine_launch_is_needed_to_build_the_plan(self):
        from unittest.mock import patch
        with patch("subprocess.Popen",side_effect=AssertionError("Plan must not run an engine")):
            self.assertEqual(sharing.build_plan()["uniqueRequests"],149)

    def test_actual_cross_run_contexts_cannot_be_mixed(self):
        contexts={role:synthetic_context(role) for role in ("reference","candidate")}
        contexts["candidate"]["nonce"]="other-run"
        with self.assertRaisesRegex(ValueError,"across actual runs"):
            sharing.verify_objects(ROOT, self.plan, contexts, {}, 3)

    def test_empty_or_missing_process_objects_never_pass_via_all(self):
        contexts={role:synthetic_context(role) for role in ("reference","candidate")}
        with self.assertRaisesRegex(ValueError,"denominator"):
            sharing.verify_objects(ROOT,self.plan,contexts,{},3)


class SharedCaseEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=ROOT/"tests/fixtures/suites/E07"
        cls.ref_index=load(cls.base/"oracle/index.json")
        cls.ref_case=next(c for c in cls.ref_index["cases"] if c["id"]=="layered-chain")
        cls.definition=cls.ref_case["definition"]
        cls.request=cls.base/"oracle"/cls.ref_case["request"]
        cls.reference=[load(cls.base/"oracle"/p) for p in cls.ref_case["observations"]]
        sys.path.insert(0,str(ROOT/"tests/conformance"))
        import test_e06_native as native
        # Actual in-process kernel results test only the evaluator here. Fresh
        # process/repetition provenance is separately required by the runner.
        cls.candidate=[native.native_observation(cls.request)[0] for _ in range(3)]

    def test_real_saved_positive_case_retains_all_independent_policies(self):
        result=sharing.evaluate_case(self.definition,self.request,self.reference,self.candidate,3)
        self.assertTrue(result["passed"],result)
        self.assertEqual(len(result["comparisons"]),3)
        self.assertEqual(len(result["candidateGeometry"]),3)
        self.assertEqual(len(result["referenceGeometry"]),3)

    def test_empty_partial_repetitions_are_never_success(self):
        for reference,candidate in (([],[]),(self.reference[:2],self.candidate),(self.reference,self.candidate[:1])):
            with self.assertRaisesRegex(ValueError,"repetitions"):
                sharing.evaluate_case(self.definition,self.request,reference,candidate,3)

    def test_equal_but_invalid_geometry_still_fails(self):
        reference,candidate=copy.deepcopy(self.reference),copy.deepcopy(self.candidate)
        for row in reference+candidate:row["result"]["width"]=1
        for row in reference:row["inputAfter"]["width"]=1
        result=sharing.evaluate_case(self.definition,self.request,reference,candidate,3)
        self.assertTrue(all(r["publicContract"]["exact"]["passed"] for r in result["comparisons"]))
        self.assertFalse(result["passed"])
        self.assertTrue(any(r["passed"] is False for r in result["candidateGeometry"]))

    def test_original_endpoints_and_input_preservation_remain_required(self):
        candidate=copy.deepcopy(self.candidate)
        candidate[0]["result"]["edges"][0]["targets"]=["missing"]
        self.assertFalse(sharing.evaluate_case(self.definition,self.request,self.reference,candidate,3)["passed"])
        candidate=copy.deepcopy(self.candidate)
        candidate[0]["inputAfter"]["id"]="changed"
        self.assertFalse(sharing.evaluate_case(self.definition,self.request,self.reference,candidate,3)["passed"])

    def test_error_outcomes_do_not_count_as_positive_suite_coverage(self):
        candidate=copy.deepcopy(self.candidate);candidate[0]["outcome"]="threw"
        with self.assertRaisesRegex(ValueError,"Positive suite"):
            sharing.evaluate_case(self.definition,self.request,self.reference,candidate,3)


class CurrentProjectBindingTests(unittest.TestCase):
    def test_config_fingerprint_and_semantic_rebinding_both_reject_stale_metadata(self):
        import base64
        import shutil
        import tomllib
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ("pyproject.toml","README.md"):
                shutil.copyfile(ROOT/name,root/name)
            project=tomllib.loads((root/"pyproject.toml").read_text(encoding="utf-8"))["project"]
            headers=["Metadata-Version: 2.4","Name: "+project["name"],"Version: "+project["version"],
                     "Summary: "+project["description"],"Requires-Python: "+project["requires-python"],
                     "Description-Content-Type: text/markdown"]
            headers += ["Classifier: "+v for v in project.get("classifiers",[])]
            for extra,values in project.get("optional-dependencies",{}).items():
                headers += ["Provides-Extra: "+extra]
                headers += ['Requires-Dist: '+v+'; extra == "'+extra+'"' for v in values]
            headers += ["Requires-Dist: "+v for v in project.get("dependencies",[])]
            raw=("\n".join(headers)+"\n\n").encode()+(root/"README.md").read_bytes()
            installed={"version":project["version"],"distributionMetadata":{
                "archivePath":"py_elk-"+project["version"]+".dist-info/METADATA",
                "sha256":hashlib.sha256(raw).hexdigest(),"bytesBase64":base64.b64encode(raw).decode()}}
            self.assertEqual(sharing.current_metadata(installed,root)["status"],"E07_DISTRIBUTION_METADATA_VALIDATED")
            before=sharing.project_identity(root)
            readme=(root/"README.md").read_bytes()
            (root/"README.md").write_bytes(readme+b"changed\n")
            self.assertNotEqual(sharing.project_identity(root),before)
            with self.assertRaisesRegex(ValueError,"README bytes"):
                sharing.current_metadata(installed,root)
            (root/"README.md").write_bytes(readme)
            (root/"pyproject.toml").write_bytes((root/"pyproject.toml").read_bytes().replace(b'requires-python = ">=3.11"',b'requires-python = ">=3.12"'))
            self.assertNotEqual(sharing.project_identity(root),before)
            with self.assertRaisesRegex(ValueError,"Requires-Python"):
                sharing.current_metadata(installed,root)


class ExecutionTimingTests(unittest.TestCase):
    def test_realistic_concurrency_bounds_accept_positive_and_reject_forged_times(self):
        report={"jobs":2,"captureSeconds":4.5,"elapsedSeconds":5.5}
        objects={str(i):{"command":{"elapsedSeconds":2}} for i in range(4)}
        identities=[{"elapsedSeconds":0.2} for _ in range(3)]
        sharing.validate_timing(report,objects,identities)
        for patch in ({"captureSeconds":0.01},{"captureSeconds":-1},{"elapsedSeconds":0.01},
                      {"captureSeconds":float('nan')},{"captureSeconds":True},{"jobs":0},{"jobs":True}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                sharing.validate_timing({**report,**patch},objects,identities)
        with self.assertRaisesRegex(ValueError,"durations"):
            sharing.validate_timing(report,{},identities)


class RecordedEnvironmentTests(unittest.TestCase):
    @staticmethod
    def context(role="candidate"):
        env={"PATH":"" if role == "candidate" else "original-reference-path", "TRANSIENT_CALLER_VALUE":"original"}
        return {"role":role, "environmentSha256":sharing.canonical_sha(env),
                "environmentEvidence":sharing.environment_evidence(role,env),
                "environmentPolicy":"EMPTY_PATH_NO_PYTHON_OVERRIDES" if role == "candidate" else "NO_NODE_PYTHON_OVERRIDES"},env

    def test_recorded_environment_verifies_in_new_process_with_different_caller(self):
        import os
        import subprocess
        context,original=self.context()
        sharing.validate_environment(context,original)
        code="import json,sys;sys.path.insert(0,sys.argv[1]);import plan_suite_execution as r;c=json.loads(sys.argv[2]);r.validate_environment(c);assert r.canonical_sha(r.environments()['candidate'])!=c['environmentSha256'];print('RECORDED_POLICY_VALIDATED')"
        actual={**os.environ,"TRANSIENT_CALLER_VALUE":"different-child-caller", "PYTHONPATH":"unrelated-verifier-value"}
        result=subprocess.run([sys.executable,"-I","-c",code,str(ROOT/"scripts"),json.dumps(context)],
                              env=actual,capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("RECORDED_POLICY_VALIDATED",result.stdout)

    def test_policy_and_digest_tampering_are_rejected(self):
        for role in ("candidate","reference"):
            context,env=self.context(role)
            sharing.validate_environment(context)
            for mutate in (lambda c:c.update(environmentSha256="9"*64),
                           lambda c:c.update(environmentPolicy="inherited-unchecked"),
                           lambda c:c["environmentEvidence"].update(overridesAbsent=False),
                           lambda c:c["environmentEvidence"].update(overridesAbsent=1),
                           lambda c:c["environmentEvidence"].update(role="unknown"),
                           lambda c:c["environmentEvidence"].update(candidatePathEmpty=False)):
                changed=copy.deepcopy(context);mutate(changed)
                with self.subTest(role=role,changed=changed),self.assertRaisesRegex(ValueError,"environment policy/digest|environment policy"):
                    sharing.validate_environment(changed)
            with self.assertRaisesRegex(ValueError,"Actual execution environment"):
                sharing.validate_environment(context,{**env,"TRANSIENT_CALLER_VALUE":"another-actual-execution"})

    def test_actual_environment_overrides_or_candidate_nonempty_path_fail(self):
        for name in sharing.OVERRIDE_VARIABLES:
            for variant in (name,name.lower()):
                with self.subTest(name=variant),self.assertRaisesRegex(ValueError,"overrides"):
                    sharing.environment_evidence("candidate",{"PATH":"",variant:"injected"})
        with self.assertRaisesRegex(ValueError,"PATH"):
            sharing.environment_evidence("candidate",{"PATH":"unexpected-compiler-or-runtime"})

    def test_rebound_environment_digest_changes_every_object_context_key(self):
        context,env=self.context()
        full={**synthetic_context(),**context}
        fingerprint="a"*64
        original=sharing.execution_key(fingerprint,full,0)
        rebound=copy.deepcopy(full)
        rebound["environmentSha256"]="9"*64
        rebound["environmentEvidence"]["environmentSha256"]="9"*64
        sharing.validate_environment(rebound)
        self.assertNotEqual(sharing.execution_key(fingerprint,rebound,0),original)


if __name__=="__main__":
    unittest.main()
