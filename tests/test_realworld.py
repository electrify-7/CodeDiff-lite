import unittest
from covdiff_lite.realworld import compare_realworld_reports, RealWorldComparison


class RealWorldBenchmarkTests(unittest.TestCase):
    def test_macro_and_micro_discrepancy_calculation(self):
        gcc_report = {
            "lines": {
                "1": {"state": "reported", "count": 1},
                "2": {"state": "reported", "count": 1},
                "3": {"state": "reported", "count": 0},
                "4": {"state": "reported", "count": 1},  # GCC only!
            }
        }
        llvm_report = {
            "lines": {
                "1": {"state": "reported", "count": 1},
                "2": {"state": "reported", "count": 1},
                "3": {"state": "reported", "count": 1},  # LLVM only!
                "4": {"state": "reported", "count": 0},
            }
        }

        result = compare_realworld_reports("test_sqlite", 10, gcc_report, llvm_report, ci_thresholds=[70, 75, 80])
        self.assertEqual(result.gcc_covered_lines, 3)
        self.assertEqual(result.llvm_covered_lines, 3)
        self.assertEqual(result.gcc_only_covered, [4])
        self.assertEqual(result.llvm_only_covered, [3])
        self.assertEqual(result.both_covered, 2)

    def test_ci_threshold_divergence_flag(self):
        # GCC has 85% coverage, LLVM has 75% coverage
        gcc_report = {
            "lines": {str(i): {"state": "reported", "count": 1 if i <= 85 else 0} for i in range(1, 101)}
        }
        llvm_report = {
            "lines": {str(i): {"state": "reported", "count": 1 if i <= 75 else 0} for i in range(1, 101)}
        }

        result = compare_realworld_reports("ci_target", 100, gcc_report, llvm_report, ci_thresholds=[80])
        # At threshold 80%: GCC passes (85%), LLVM fails (75%) -> discrepancy is True!
        self.assertTrue(result.ci_threshold_divergence[80])
        self.assertEqual(result.macro_divergence_pct, 10.0)


if __name__ == "__main__":
    unittest.main()
