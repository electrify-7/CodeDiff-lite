"""Tests for Metamorphic Testing (EMI) and Concurrency Coverage Fidelity."""

import unittest
from covdiff_lite.metamorphic import EMIMutator, verify_metamorphic_invariants
from covdiff_lite.concurrency import generate_concurrent_c_program, analyze_concurrency_fidelity


class MetamorphicCoverageTests(unittest.TestCase):
    def setUp(self):
        self.sample_c = (
            "#include <stdio.h>\n"
            "int main(void) {\n"
            "    int a = 10;\n"
            "    int b = 20;\n"
            "    int sum = a + b;\n"
            "    printf(\"%d\\n\", sum);\n"
            "    return 0;\n"
            "}\n"
        )

    def test_emi_mutator_inject_dead_code(self):
        variant = EMIMutator.inject_dead_code_at_line(self.sample_c, line_index=3, snippet_idx=0)
        self.assertIn("if (0)", variant.variant_source)
        self.assertTrue(len(variant.expected_dead_lines) > 0)
        # Verify line offsets
        lines = variant.variant_source.splitlines()
        for dl in variant.expected_dead_lines:
            self.assertTrue(1 <= dl <= len(lines))

    def test_emi_mutator_inject_opaque_predicate(self):
        variant = EMIMutator.inject_opaque_predicate(self.sample_c, line_index=4)
        self.assertIn("(_opq_v * _opq_v + 1) == 0", variant.variant_source)
        self.assertTrue(len(variant.expected_dead_lines) >= 2)

    def test_verify_metamorphic_invariants_pass(self):
        variant = EMIMutator.inject_dead_code_at_line(self.sample_c, line_index=3, snippet_idx=0)
        # Simulated baseline and variant with zero hits on dead lines
        baseline_cov = {3: 1, 4: 1, 5: 1, 6: 1}
        shift = len(variant.variant_source.splitlines()) - len(variant.baseline_source.splitlines())
        variant_cov = {3: 1, 4 + shift: 1, 5 + shift: 1, 6 + shift: 1}
        # Injected dead lines have count 0
        for dl in variant.expected_dead_lines:
            variant_cov[dl] = 0

        res = verify_metamorphic_invariants(
            case_id="emi_01",
            emi_variant=variant,
            baseline_gcc_cov=baseline_cov,
            variant_gcc_cov=variant_cov,
            baseline_llvm_cov=baseline_cov,
            variant_llvm_cov=variant_cov,
            baseline_output="30\n",
            variant_output="30\n",
        )
        self.assertTrue(res.passed)
        self.assertEqual(len(res.gcc_ghost_lines), 0)
        self.assertEqual(len(res.llvm_ghost_lines), 0)

    def test_verify_metamorphic_invariants_detect_ghost_line(self):
        variant = EMIMutator.inject_dead_code_at_line(self.sample_c, line_index=3, snippet_idx=0)
        baseline_cov = {3: 1, 4: 1, 5: 1}
        shift = len(variant.variant_source.splitlines()) - len(variant.baseline_source.splitlines())
        variant_cov = {3: 1, 4 + shift: 1, 5 + shift: 1}
        # Simulate compiler BUG: assigns count 1 to an unreached dead line
        bug_line = variant.expected_dead_lines[0]
        variant_cov[bug_line] = 1

        res = verify_metamorphic_invariants(
            case_id="emi_bug_01",
            emi_variant=variant,
            baseline_gcc_cov=baseline_cov,
            variant_gcc_cov=variant_cov,
            baseline_llvm_cov=baseline_cov,
            variant_llvm_cov=variant_cov,
            baseline_output="30\n",
            variant_output="30\n",
        )
        self.assertFalse(res.passed)
        self.assertIn(bug_line, res.gcc_ghost_lines)
        self.assertIn(bug_line, res.llvm_ghost_lines)


class ConcurrencyCoverageTests(unittest.TestCase):
    def test_concurrency_template_generation(self):
        code = generate_concurrent_c_program(num_threads=8, iterations=500)
        self.assertIn("#include <pthread.h>", code)
        self.assertIn("#define NUM_THREADS 8", code)
        self.assertIn("#define ITERATIONS_PER_THREAD 500", code)
        self.assertIn("SCORED_CRITICAL_SECTION", code)

    def test_concurrency_fidelity_analysis_exact(self):
        profile = analyze_concurrency_fidelity(
            num_threads=4,
            iterations=1000,
            gcc_hits=4000,
            llvm_hits=4000,
            overhead_ratio=1.05,
        )
        self.assertTrue(profile.passed)
        self.assertTrue(profile.gcc_counter_exact)
        self.assertTrue(profile.llvm_counter_exact)
        self.assertEqual(profile.expected_critical_hits, 4000)

    def test_concurrency_fidelity_analysis_tearing_loss(self):
        # 3998 hits instead of 4000 due to non-atomic tearing
        profile = analyze_concurrency_fidelity(
            num_threads=4,
            iterations=1000,
            gcc_hits=3998,
            llvm_hits=4000,
        )
        self.assertFalse(profile.gcc_counter_exact)
        self.assertTrue(profile.llvm_counter_exact)
        self.assertFalse(profile.passed)


if __name__ == "__main__":
    unittest.main()
