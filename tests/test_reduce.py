import unittest
from covdiff_lite.reduce import delta_debug_lines, ProgramReducer, ReductionResult


class ReducerTests(unittest.TestCase):
    def test_delta_debug_lines_minimization(self):
        # A list of 10 lines where only lines 2 and 8 are required
        lines = [
            "line 0",
            "line 1",
            "REQUIRED_START",
            "line 3",
            "line 4",
            "line 5",
            "line 6",
            "line 7",
            "REQUIRED_END",
            "line 9",
        ]

        def predicate(text: str) -> bool:
            return "REQUIRED_START" in text and "REQUIRED_END" in text

        minimized = delta_debug_lines(lines, predicate)
        self.assertEqual(minimized, ["REQUIRED_START", "REQUIRED_END"])

    def test_program_reducer_on_c_code(self):
        source = """#include <stdio.h>
// Unused comment line 1
// Unused comment line 2

int main(void) {
    int unused1 = 100;
    int unused2 = 200;
    int target_bug = 42;
    printf("%d\\n", target_bug);
    return 0;
}
"""

        # Interestingness: program must compile and print "42\n"
        def predicate(candidate_source: str) -> bool:
            # Simple syntax & content check simulating compilation & execution
            return ("target_bug = 42" in candidate_source and
                    "printf" in candidate_source and
                    "main" in candidate_source and
                    "{" in candidate_source and
                    "}" in candidate_source)

        reducer = ProgramReducer(predicate)
        result = reducer.reduce(source)

        self.assertLess(result.reduced_lines, result.original_lines)
        self.assertGreater(result.reduction_pct, 0.0)
        self.assertIn("target_bug = 42", result.reduced_source)
        self.assertNotIn("Unused comment", result.reduced_source)


if __name__ == "__main__":
    unittest.main()
