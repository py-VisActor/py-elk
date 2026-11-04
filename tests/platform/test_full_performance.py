"""Pure benchmark-plan and independent quality metric controls."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('full_performance',ROOT/'scripts/validate_full_performance.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class FullPerformanceTests(unittest.TestCase):
    def test_plan_covers_all_algorithms_scales_and_force_models(self):
        plan=module.plan();rows=plan['profiles']
        self.assertEqual(len(rows),39)
        self.assertEqual({row['algorithm']for row in rows},set(module.ALGORITHMS))
        for algorithm in module.ALGORITHMS:
            self.assertEqual({row['nodes']for row in rows if row['algorithm']==algorithm},set((8,32,96)))
        self.assertEqual((plan['warmups'],plan['samples']),(1,5))
        self.assertEqual(plan['layoutExecutions'],0)

    def test_datasets_exercise_disconnected_packing_and_overlap_removal(self):
        disco=module.graph_for('disco',32)
        self.assertLess(len(disco['edges']),31)
        overlap=module.graph_for('sporeOverlap',32)
        self.assertGreater(module.quality(overlap)['overlappingNodePairs'],0)

    def test_stress_metric_distinguishes_exact_lengths_from_a_collapsed_graph(self):
        graph={'children':[{'id':'a','x':0,'y':0,'width':0,'height':0},
                           {'id':'b','x':100,'y':0,'width':0,'height':0}],
               'edges':[{'sources':['a'],'targets':['b']}]}
        self.assertEqual(module.quality(graph)['normalizedGraphStress'],0)
        graph['children'][1]['x']=0
        self.assertEqual(module.quality(graph)['normalizedGraphStress'],1)


if __name__=='__main__':unittest.main()
