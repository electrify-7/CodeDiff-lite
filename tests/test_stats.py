import unittest
from covdiff_lite.stats import cliffs_delta, wilcoxon_signed_rank, compute_optimization_degradation_statistics


class StatsTests(unittest.TestCase):
    def test_cliffs_delta_scale(self):
        # Disjoint distributions -> delta = 1.0 (large)
        x = [10.0, 20.0, 30.0]
        y = [1.0, 2.0, 3.0]
        delta, effect = cliffs_delta(x, y)
        self.assertEqual(delta, 1.0)
        self.assertEqual(effect, "large")

        # Identical distributions -> delta = 0.0 (negligible)
        delta_same, effect_same = cliffs_delta(x, x)
        self.assertEqual(delta_same, 0.0)
        self.assertEqual(effect_same, "negligible")

    def test_wilcoxon_signed_rank_p_value(self):
        gcc_deg = [10.0, 15.0, 20.0, 25.0, 18.0, 12.0, 14.0, 22.0]
        clang_deg = [0.0, 1.0, 0.0, 0.0, 2.0, 0.0, 0.0, 1.0]
        w, p, msg = wilcoxon_signed_rank(gcc_deg, clang_deg)
        self.assertLess(p, 0.05)
        self.assertIn("p=", msg)

    def test_compute_optimization_degradation_statistics(self):
        gcc = [5.0, 8.0, 12.0, 10.0]
        clang = [0.0, 0.0, 1.0, 0.0]
        res = compute_optimization_degradation_statistics(gcc, clang)
        self.assertEqual(res["paired_sample_size"], 4)
        self.assertTrue(res["statistically_significant_p05"])
        self.assertIn("summary", res)


if __name__ == "__main__":
    unittest.main()
