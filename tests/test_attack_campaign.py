import unittest
from pathlib import Path
from scripts.attack_differential_campaign import generate_torture_suite

ROOT = Path(__file__).resolve().parents[1]


class AttackCampaignTests(unittest.TestCase):
    def test_torture_suite_generation(self):
        suite = generate_torture_suite()
        self.assertGreaterEqual(len(suite), 8)
        ids = [t["id"] for t in suite]
        self.assertIn("TORTURE-007", ids)
        self.assertIn("TORTURE-008", ids)

    def test_reproducers_exist_and_non_empty(self):
        repro_dir = ROOT / "docs" / "reproducers"
        stmt_expr_file = repro_dir / "test_stmt_expr_early_ret.c"
        indirect_goto_file = repro_dir / "test_indirect_goto_leak.c"

        self.assertTrue(stmt_expr_file.exists())
        self.assertTrue(indirect_goto_file.exists())

        self.assertIn("return 42", stmt_expr_file.read_text())
        self.assertIn("goto *targets", indirect_goto_file.read_text())


if __name__ == "__main__":
    unittest.main()
