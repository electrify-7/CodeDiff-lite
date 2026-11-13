import unittest
from covdiff_lite.optimization import evaluate_statement_degradation, OPTIMIZATION_LEVELS


class OptimizationDegradationTests(unittest.TestCase):
    def test_fidelity_metric_perfect_match(self):
        manifest = {
            "lines": {
                "10": {"statement_id": "s1", "count": 2},
                "12": {"statement_id": "s2", "count": 0},
            }
        }
        report = {
            "lines": {
                "10": {"state": "reported", "count": 2},
                "12": {"state": "reported", "count": 0},
            }
        }
        result = evaluate_statement_degradation(manifest, report, "gcov", "-O0")
        self.assertEqual(result["fidelity_pct"], 100.0)
        self.assertEqual(result["ghost_count"], 0)
        self.assertEqual(result["dropped_count"], 0)

    def test_ghost_line_detection(self):
        # Line 12 was dead code (expected 0), but compiler optimized code into it (reported 1)
        manifest = {
            "lines": {
                "10": {"statement_id": "s1", "count": 1},
                "12": {"statement_id": "s2", "count": 0},
            }
        }
        report = {
            "lines": {
                "10": {"state": "reported", "count": 1},
                "12": {"state": "reported", "count": 1},  # Ghost!
            }
        }
        result = evaluate_statement_degradation(manifest, report, "llvm-cov", "-O2")
        self.assertEqual(result["ghost_count"], 1)
        self.assertEqual(result["ghost_lines"][0]["line"], 12)
        self.assertEqual(result["ghost_lines"][0]["reported"], 1)
        self.assertEqual(result["fidelity_pct"], 50.0)

    def test_dropped_line_detection_unmapped(self):
        # Line 10 was executed 3 times, but compiler inlined/elided it (missing from report)
        manifest = {
            "lines": {
                "10": {"statement_id": "s1", "count": 3},
                "12": {"statement_id": "s2", "count": 1},
            }
        }
        report = {
            "lines": {
                # Line 10 missing
                "12": {"state": "reported", "count": 1},
            }
        }
        result = evaluate_statement_degradation(manifest, report, "gcov", "-O3")
        self.assertEqual(result["dropped_count"], 1)
        self.assertEqual(result["dropped_lines"][0]["line"], 10)
        self.assertEqual(result["fidelity_pct"], 50.0)

    def test_count_mismatch_after_unrolling(self):
        manifest = {
            "lines": {
                "10": {"statement_id": "loop_body", "count": 10},
            }
        }
        report = {
            "lines": {
                "10": {"state": "reported", "count": 5},  # Count altered by unrolling
            }
        }
        result = evaluate_statement_degradation(manifest, report, "llvm-cov", "-O2")
        self.assertEqual(len(result["count_mismatches"]), 1)
        self.assertEqual(result["count_mismatches"][0]["reported"], 5)
        self.assertEqual(result["fidelity_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
