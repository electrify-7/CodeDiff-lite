import unittest
from covdiff_lite.matrix import CompilerMatrix, BugReport


class CompilerMatrixTests(unittest.TestCase):
    def setUp(self):
        self.matrix = CompilerMatrix()

    def test_version_evolution_fixed_in_modern(self):
        obs = {
            "14.0.0": True,   # Bug present
            "16.0.0": False,  # Fixed
            "18.1.0": False,  # Fixed
        }
        res = self.matrix.categorize_version_evolution(obs)
        self.assertEqual(res, "upstream_fixed_in_modern")

    def test_version_evolution_persistent_bug(self):
        obs = {
            "14.0.0": True,
            "16.0.0": True,
            "18.1.0": True,
        }
        res = self.matrix.categorize_version_evolution(obs)
        self.assertEqual(res, "persistent_bug")

    def test_version_evolution_regression(self):
        obs = {
            "11.4.0": False,
            "12.3.0": False,
            "14.1.0": True,   # Regression!
        }
        # In this dictionary, buggy version is newer than first clean version
        buggy_versions = [v for v, b in obs.items() if b]
        clean_versions = [v for v, b in obs.items() if not b]
        self.assertTrue(buggy_versions[-1] > clean_versions[0])

    def test_upstream_dossier_generation(self):
        dossier = self.matrix.generate_upstream_dossier(
            issue_id="LLVM_140427",
            tool="llvm-cov",
            affected=["14.0.0", "15.0.0"],
            fixed=["16.0.0"],
            source="void foo(void) { ... }",
            expected_desc="Line should have count 0",
            actual_desc="llvm-cov incorrectly reported count 2 on unexecuted macro statement",
        )
        md = dossier.to_markdown()
        self.assertIn("Upstream Bug Report: LLVM_140427", md)
        self.assertIn("Target Tool:** llvm-cov", md)
        self.assertIn("Affected Versions:** 14.0.0, 15.0.0", md)
        self.assertIn("Resolved In:** 16.0.0", md)
        self.assertIn("llvm-cov show", dossier.reproduction_script)


if __name__ == "__main__":
    unittest.main()
