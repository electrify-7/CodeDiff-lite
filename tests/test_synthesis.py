import unittest
from covdiff_lite.synthesis import (
    synthesize_complex_macro,
    synthesize_statement_expression,
    synthesize_non_local_control,
    synthesize_vla_and_duff,
    generate_large_scale_corpus,
    EXPANDED_FAMILIES,
)


class SynthesisTests(unittest.TestCase):
    def test_complex_macros_variadic_and_token_paste(self):
        src_var, man_var = synthesize_complex_macro("variadic", 5, 1)
        self.assertIn("VAR_ADD(result, 5", src_var)
        self.assertEqual(man_var["expected_output"]["stdout"], "5\n")

        src_paste, man_paste = synthesize_complex_macro("token_paste", 7, 0)
        self.assertIn("GLUE_ADD(result, 7)", src_paste)
        self.assertEqual(man_paste["expected_output"]["stdout"], "7\n")

    def test_statement_expressions_and_attributes(self):
        src_stmt, man_stmt = synthesize_statement_expression("stmt_expr", 2, 3)
        self.assertIn("({", src_stmt)
        # (2 + 3) * 2 = 10
        self.assertEqual(man_stmt["expected_output"]["stdout"], "10\n")

        src_inline, man_inline = synthesize_statement_expression("always_inline", 1, 4)
        self.assertIn("__attribute__((always_inline))", src_inline)
        self.assertEqual(man_inline["expected_output"]["stdout"], "5\n")

    def test_non_local_control_setjmp_longjmp(self):
        # Trigger != 0 -> longjmp taken -> recovered path (amount * 3) = 6
        src_jmp, man_jmp = synthesize_non_local_control("setjmp_longjmp", 1, 2)
        self.assertIn("setjmp(env)", src_jmp)
        self.assertIn("longjmp(env, 1)", src_jmp)
        self.assertEqual(man_jmp["expected_output"]["stdout"], "6\n")

        # Computed goto
        src_goto, man_goto = synthesize_non_local_control("computed_goto", 0, 3)
        self.assertIn("goto *labels[idx]", src_goto)
        self.assertEqual(man_goto["expected_output"]["stdout"], "3\n")

    def test_vla_and_duff_device(self):
        src_vla, man_vla = synthesize_vla_and_duff("vla_dynamic", 4, 3)
        self.assertIn("int vla[n];", src_vla)
        # 4 * 3 = 12
        self.assertEqual(man_vla["expected_output"]["stdout"], "12\n")

        src_duff, man_duff = synthesize_vla_and_duff("duff_device", 5, 2)
        self.assertIn("switch (count % 4)", src_duff)
        self.assertEqual(man_duff["expected_output"]["stdout"], "10\n")

    def test_scaled_corpus_uniqueness_and_scale(self):
        cases = generate_large_scale_corpus(target_count=500)
        self.assertEqual(len(cases), 500)
        hashes = [m["source_sha256"] for _, m in cases]
        self.assertEqual(len(hashes), len(set(hashes)), "All generated programs must have unique SHA-256 hashes")


if __name__ == "__main__":
    unittest.main()
