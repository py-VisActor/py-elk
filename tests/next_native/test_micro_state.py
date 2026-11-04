"""New generic adapter state only; no full layout/provider sweep."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/iteration'))
import next_workspace


class PrivateMicroStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory(prefix='py-elk-micro-state-')
        cls.workspace=Path(cls.folder.name)/'restored';next_workspace.restore(cls.workspace)
    @classmethod
    def tearDownClass(cls): cls.folder.cleanup()
    def run_case(self,name):
        result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/platform/next_micro_state_probe.py'),
                               '--workspace',str(self.workspace),'--case',name],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        record=json.loads(result.stdout);self.assertTrue(record['passed'])
        self.assertTrue(Path(record['modulePath']).is_relative_to(self.workspace))
        self.assertFalse(record['publicAPIIntegrated']);self.assertFalse(record['fullValidation'])
    def test_mutable_defaults_cache_per_element_and_reach_real_provider_helpers(self): self.run_case('mutable-properties')
    def test_native_identity_is_stable_signed32_and_independent_of_json_business_hash(self): self.run_case('native-identity')
    def test_shared_factory_owns_and_targets_the_selected_global_mapping(self): self.run_case('global-factory')
    def test_generated_nonfinite_output_uses_null_without_changing_input_or_internal_math(self): self.run_case('wire-boundary')
    def test_presence_distinguishes_parent_local_defaults_false_zero_and_property_removal(self): self.run_case('property-presence')
    def test_reviewed_force_stress_and_ns_schemas_share_target_and_core_default_semantics(self): self.run_case('source-option-additions')
    def test_new_property_assignment_and_removal_supersede_legacy_cleared_marker(self): self.run_case('cleared-property-replacement')
    def test_margin_only_computes_overhang_without_sort_resize_or_label_placement(self): self.run_case('margin-only')
    def test_unseeded_host_entropy_is_separate_and_has_exact_half_open_boundaries(self): self.run_case('host-entropy')
    def test_spore_properties_preserve_enum_ordinals_targets_false_and_actual_defaults(self): self.run_case('spore-options')
    def test_double_defaults_and_computed_storage_use_binary64_without_weakening_finite_input(self): self.run_case('double-storage')
    def test_source_identifier_text_does_not_change_native_typed_identity_or_raw_ids(self): self.run_case('identifier-view')
    def test_underlying_provider_uses_same_session_and_only_resolved_calls_create_subtasks(self): self.run_case('provider-invocation')
    def test_label_minimum_uses_parent_adapters_and_does_not_commit_shape_changes(self): self.run_case('label-minimum')
    def test_source_enumset_defaults_and_explicit_global_values_keep_distinct_sharing_rules(self): self.run_case('enumset-identity')
    def test_new_spore_provider_registration_reuses_real_margin_only_and_shared_objects(self): self.run_case('spore-invocation')
    def test_resize_constraint_set_mutation_survives_reads_until_next_actual_assignment(self): self.run_case('cleared-set-mutation')
    def test_core_defaults_do_not_inherit_bounded_layered_or_other_provider_overrides(self): self.run_case('core-property-defaults')
    def test_imported_generic_properties_keep_targets_aliases_presence_cache_and_caller_defaults(self): self.run_case('runtime-properties')
    def test_generic_property_value_and_presence_resolve_the_same_unique_suffix(self): self.run_case('runtime-property-alias')
    def test_native_property_getter_materializes_and_retains_mutable_chain_without_provider_view(self): self.run_case('native-property-getter')
    def test_owner_default_materializes_before_micro_and_is_shared_across_later_owner_reads(self): self.run_case('owner-default-property')
    def test_actual_provider_padding_read_caches_owner_default_before_later_micro(self): self.run_case('provider-padding-materialization')


if __name__=='__main__': unittest.main()
