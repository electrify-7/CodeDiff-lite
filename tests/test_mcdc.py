import unittest
from covdiff_lite.mcdc import DecisionTree, MCDCAnalyzer, ConditionOutcome, IndependencePair
from covdiff_lite.branch_alignment import (
    resolve_gcc_decision_branches,
    resolve_llvm_decision_branches,
    classify_branch_finding,
    align_all_branches,
)


class MCDCTreeTests(unittest.TestCase):
    def test_single_condition_tree(self):
        ast = {
            "kind": "decision",
            "id": "single_cond",
            "value": {
                "kind": "binary", "op": ">",
                "left": {"kind": "variable", "name": "x"},
                "right": {"kind": "literal", "value": 0}
            }
        }
        tree = DecisionTree("single_cond", ast)
        res_t, eval_t = tree.evaluate({"single_cond": True})
        self.assertTrue(res_t)

    def test_compound_and_short_circuit_truth_table(self):
        ast = {
            "kind": "binary", "op": "&&",
            "left": {"kind": "decision", "id": "cond_a", "value": {"kind": "literal", "value": 1}},
            "right": {"kind": "decision", "id": "cond_b", "value": {"kind": "literal", "value": 1}},
        }
        tree = DecisionTree("decision_and", ast)
        self.assertEqual(tree.condition_ids, ["cond_a", "cond_b"])

        # When cond_a is False, cond_b should be unevaluated (None)
        res, ev = tree.evaluate({"cond_a": False, "cond_b": True})
        self.assertFalse(res)
        self.assertIsNone(ev["cond_b"])

        # When cond_a is True and cond_b is True -> True
        res_t, ev_t = tree.evaluate({"cond_a": True, "cond_b": True})
        self.assertTrue(res_t)
        self.assertTrue(ev_t["cond_a"])
        self.assertTrue(ev_t["cond_b"])

        table = tree.truth_table()
        self.assertEqual(len(table), 4)

    def test_compound_or_short_circuit(self):
        ast = {
            "kind": "binary", "op": "||",
            "left": {"kind": "decision", "id": "cond_a", "value": {"kind": "literal", "value": 1}},
            "right": {"kind": "decision", "id": "cond_b", "value": {"kind": "literal", "value": 1}},
        }
        tree = DecisionTree("decision_or", ast)
        res, ev = tree.evaluate({"cond_a": True, "cond_b": False})
        self.assertTrue(res)
        self.assertIsNone(ev["cond_b"])  # Short-circuited!


class MCDCAnalyzerTests(unittest.TestCase):
    def test_full_mcdc_satisfaction_for_and(self):
        analyzer = MCDCAnalyzer("test_and", ["a", "b"])

        # Vector 1: a=True, b=True -> True
        analyzer.record_evaluation(True, {"a": True, "b": True})
        # Vector 2: a=False, b=None -> False (proves 'a')
        analyzer.record_evaluation(False, {"a": False, "b": None})
        # Vector 3: a=True, b=False -> False (proves 'b')
        analyzer.record_evaluation(False, {"a": True, "b": False})

        pair_a = analyzer.find_independence_pair("a")
        self.assertIsNotNone(pair_a)
        self.assertEqual(pair_a.condition_id, "a")

        pair_b = analyzer.find_independence_pair("b")
        self.assertIsNotNone(pair_b)
        self.assertEqual(pair_b.condition_id, "b")

        summary = analyzer.compute_summary()
        self.assertTrue(summary["decision_coverage"]["covered"])
        self.assertEqual(summary["condition_coverage_pct"], 100.0)
        self.assertEqual(summary["mcdc_coverage_pct"], 100.0)
        self.assertTrue(summary["mcdc_fully_satisfied"])

    def test_partial_mcdc_when_condition_not_toggled(self):
        analyzer = MCDCAnalyzer("partial", ["a", "b"])
        # Only True, True executed
        analyzer.record_evaluation(True, {"a": True, "b": True})
        summary = analyzer.compute_summary()
        self.assertFalse(summary["decision_coverage"]["covered"])
        self.assertEqual(summary["mcdc_coverage_pct"], 0.0)
        self.assertFalse(summary["mcdc_fully_satisfied"])


class BranchAlignmentTests(unittest.TestCase):
    def test_gcc_branch_resolution_exact_counts(self):
        span = {"line": 10, "end_line": 10}
        expected = {"true": 3, "false": 2}
        gcov_lines = {
            "10": {
                "branches": [
                    {"count": 2, "fallthrough": True},
                    {"count": 3, "fallthrough": False},
                ]
            }
        }
        res = resolve_gcc_decision_branches("dec1", span, expected, gcov_lines, {})
        self.assertIsNotNone(res)
        self.assertEqual(res["true"], 3)
        self.assertEqual(res["false"], 2)

    def test_llvm_branch_resolution_region_overlap(self):
        span = {"line": 15, "end_line": 15}
        expected = {"true": 1, "false": 4}
        llvm_branches = [
            [15, 5, 15, 20, 1, 4, 0, 0, 4]  # lineStart, colStart, lineEnd, colEnd, trueCount, falseCount...
        ]
        res = resolve_llvm_decision_branches("dec2", span, expected, llvm_branches)
        self.assertIsNotNone(res)
        self.assertEqual(res["true"], 1)
        self.assertEqual(res["false"], 4)

    def test_branch_classification_agreement(self):
        expected = {"true": 5, "false": 0}
        gcc = {"true": 5, "false": 0}
        llvm = {"true": 5, "false": 0}
        finding = classify_branch_finding("dec_agree", expected, gcc, llvm)
        self.assertEqual(finding["assessment"], "complete_agreement")

    def test_branch_classification_contradiction(self):
        expected = {"true": 5, "false": 0}
        gcc = {"true": 5, "false": 0}
        llvm = {"true": 3, "false": 2}  # Contradiction!
        finding = classify_branch_finding("dec_contra", expected, gcc, llvm)
        self.assertEqual(finding["assessment"], "candidate_incorrect_report")
        self.assertIn("llvm-cov", finding["reason"])

    def test_align_all_branches_end_to_end(self):
        manifest = {
            "branches": [
                {
                    "decision_id": "outer_if",
                    "expected": {"true": 2, "false": 1},
                    "source_span": {"line": 12, "end_line": 12},
                }
            ]
        }
        gcov_rep = {
            "lines": {
                "12": {
                    "branches": [
                        {"count": 2, "fallthrough": False},
                        {"count": 1, "fallthrough": True},
                    ]
                }
            }
        }
        llvm_rep = {
            "branches": [
                [12, 5, 12, 18, 2, 1, 0, 0, 4]
            ]
        }
        aligned = align_all_branches(manifest, gcov_rep, llvm_rep)
        self.assertEqual(aligned["mapping_status"], "aligned")
        self.assertEqual(aligned["comparable_decisions"], 1)
        self.assertEqual(aligned["complete_agreements"], 1)
        self.assertEqual(len(aligned["findings"]), 0)


if __name__ == "__main__":
    unittest.main()
