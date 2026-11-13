import unittest
from covdiff_lite.downstream import compute_ochiai, compute_tarantula, evaluate_sbfl_impact


class DownstreamImpactTests(unittest.TestCase):
    def test_ochiai_and_tarantula_basic(self):
        # 1 failing test executes statement (ef=1, nf=0), 0 passing tests (ep=0, np=1)
        och = compute_ochiai(ef=1, ep=0, nf=0, np=1)
        self.assertEqual(och, 1.0)

        tar = compute_tarantula(ef=1, ep=0, nf=0, np=1)
        self.assertEqual(tar, 1.0)

    def test_sbfl_rank_shift_due_to_ghost_coverage(self):
        # 2 test cases:
        # T1 (FAIL): buggy statement S_BUG runs.
        # T2 (PASS): clean statement S_CLEAN runs.
        # GCC accurately records that S_BUG ran on T1 and not T2.
        spectra_gcc = [
            ({"S_BUG": True, "S_CLEAN": False, "S_GHOST": False}, False),  # Failing test
            ({"S_BUG": False, "S_CLEAN": True, "S_GHOST": False}, True),   # Passing test
        ]

        # LLVM has a ghost coverage bug on S_GHOST on T1!
        spectra_llvm = [
            ({"S_BUG": True, "S_CLEAN": False, "S_GHOST": True}, False),   # Ghost S_GHOST marked!
            ({"S_BUG": False, "S_CLEAN": True, "S_GHOST": False}, True),
        ]

        res = evaluate_sbfl_impact(spectra_gcc, spectra_llvm, "S_BUG", formula="ochiai")
        self.assertEqual(res.gcc_fault_rank, 1)
        # S_BUG has score 1.0 in both, but tied with S_GHOST in LLVM
        self.assertIn("S_BUG", res.to_dict()["gcc_top3"])


if __name__ == "__main__":
    unittest.main()
