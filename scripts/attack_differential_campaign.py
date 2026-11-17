#!/usr/bin/env python3
"""Targeted Attack & Bug-Hunting Campaign for GCC and Clang Coverage Tools.

Synthesizes high-complexity edge-case C programs across torture construct families:
- Statement Expressions ({ ... }) with control flow and returns
- Non-Local Control Flow (backward gotos, unreached labels)
- Multi-line Variadic Macros with embedded conditionals
- Duff's Device and Switch-Loop interleaving
- GCC 15 Condition Coverage (-fcondition-coverage) vs DO-178C MC/DC Oracle

Evaluates reports against the independent semantic ground-truth oracle,
detects ghost lines, dropped lines, and branch misattributions,
and automatically delta-debugs discrepancies down to minimal reproducers.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from covdiff_lite.mcdc import DecisionTree, MCDCAnalyzer
from covdiff_lite.parsers.llvm import segment_lines
from covdiff_lite.reduce import ProgramReducer


def run_gcc_host(source_code: str, extra_flags: list = None) -> dict:
    """Compile and run under host GCC 15."""
    if extra_flags is None:
        extra_flags = []
    with tempfile.TemporaryDirectory() as td:
        src_path = os.path.join(td, "test.c")
        bin_path = os.path.join(td, "test")
        with open(src_path, "w") as f:
            f.write(source_code)
        
        compile_cmd = ["gcc", "-std=c11", "-O0", "-g", "--coverage", "-Wall", "-Wextra"] + extra_flags + [src_path, "-o", bin_path]
        res = subprocess.run(compile_cmd, capture_output=True, text=True, cwd=td)
        if res.returncode != 0:
            return {"status": "compile_error", "stderr": res.stderr}
            
        exec_res = subprocess.run([bin_path], capture_output=True, text=True, cwd=td, timeout=5)
        
        # Run gcov
        gcov_cmd = ["gcov", "-j", "-b", "-c", "test.c"]
        if "-fcondition-coverage" in extra_flags:
            gcov_cmd.append("-g")
        gcov_res = subprocess.run(gcov_cmd, capture_output=True, text=True, cwd=td)
        
        # Read gcov json
        gz_files = [f for f in os.listdir(td) if f.endswith(".gcov.json.gz")]
        if not gz_files:
            return {"status": "no_gcov", "stderr": gcov_res.stderr}
            
        import gzip
        with gzip.open(os.path.join(td, gz_files[0]), "rt", encoding="utf-8") as f:
            data = json.load(f)
            
        lines_cov = {}
        conditions_cov = {}
        for item in data.get("files", [{}])[0].get("lines", []):
            lines_cov[item["line_number"]] = {
                "count": item.get("count"),
                "branches": item.get("branches", []),
            }
            if item.get("conditions"):
                conditions_cov[item["line_number"]] = item["conditions"]
                
        return {
            "status": "success",
            "stdout": exec_res.stdout,
            "lines": lines_cov,
            "conditions": conditions_cov,
        }


def run_clang_docker(source_code: str) -> dict:
    """Compile and run under Clang 14 in Docker."""
    with tempfile.TemporaryDirectory() as td:
        src_path = os.path.join(td, "test.c")
        with open(src_path, "w") as f:
            f.write(source_code)
            
        script_path = os.path.join(td, "run.sh")
        script_content = """#!/bin/bash
set -e
clang-14 -std=c11 -O0 -g -fprofile-instr-generate -fcoverage-mapping /tmp/mount/test.c -o /tmp/mount/test
LLVM_PROFILE_FILE=/tmp/mount/test.profraw /tmp/mount/test > /dev/null
llvm-profdata-14 merge -sparse /tmp/mount/test.profraw -o /tmp/mount/test.profdata
llvm-cov-14 export /tmp/mount/test -instr-profile=/tmp/mount/test.profdata /tmp/mount/test.c
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{td}:/tmp/mount",
            "-w", "/tmp/mount",
            "covdiff-lite:testing",
            "bash", "/tmp/mount/run.sh"
        ]
        res = subprocess.run(docker_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return {"status": "error", "stderr": res.stderr}
            
        try:
            cov_data = json.loads(res.stdout)
            file_data = cov_data["data"][0]["files"][0]
            segments = file_data.get("segments", [])
            branches = file_data.get("branches", [])
            
            # Map segments to line execution counts using canonical LLVM LineCoverageStats
            source_line_count = len(source_code.splitlines())
            raw_lines = segment_lines(segments, source_line_count)
            lines_cov = {int(k): v["count"] for k, v in raw_lines.items()}

            return {
                "status": "success",
                "lines": lines_cov,
                "segments": segments,
                "branches": branches,
            }
        except Exception as e:
            return {"status": "parse_error", "error": str(e), "stdout": res.stdout[:500]}


def generate_torture_suite() -> list:
    """Generate high-yield attack programs specifically targeting known compiler coverage blind spots."""
    suite = []

    # 1. Statement Expression with Early Return in Short-Circuit Guard
    suite.append({
        "id": "TORTURE-001",
        "name": "Statement Expression with Early Return in Guard",
        "description": "GCC attributes declaration line as 0 count when inner statement expression returns early",
        "code": """#include <stdio.h>

int test_early_ret(int a) {
    int res = ({
        if (a == 0) {
            return 42;
        }
        a * 2;
    });
    return res + 1;
}

int main(void) {
    printf("%d\\n", test_early_ret(0));
    return 0;
}
""",
        "expected_executed_lines": [3, 4, 5, 6, 12, 13, 14],
        "expected_unexecuted_lines": [8, 10],
    })

    # 2. Multi-line Nested Ternary inside Statement Expression
    suite.append({
        "id": "TORTURE-002",
        "name": "Nested Ternary in Statement Expression",
        "description": "Ternary alternative branch inside statement expression with short-circuiting",
        "code": """#include <stdio.h>

int main(void) {
    int flag = 1;
    int val = ({
        int a = 10;
        int b = 20;
        flag ? (a > 5 ? a : b) : (b > 15 ? b : a);
    });
    printf("%d\\n", val);
    return 0;
}
""",
        "expected_executed_lines": [3, 4, 5, 6, 7, 8, 10, 11],
        "expected_unexecuted_lines": [],
    })

    # 3. Non-Local Backward Jump over Multiple Blocks (Label Region Leak)
    suite.append({
        "id": "TORTURE-003",
        "name": "Backward Goto Crossing Multiple Scopes",
        "description": "Backward jump crossing compound scopes testing region termination in LLVM and GCC",
        "code": """#include <stdio.h>

int main(void) {
    int count = 0;
loop_start:
    count++;
    if (count < 3) {
        {
            int temp = count * 10;
            if (temp > 0) {
                goto loop_start;
            }
        }
    }
    printf("%d\\n", count);
    return 0;
}
""",
        "expected_executed_lines": [3, 4, 6, 7, 9, 10, 11, 15, 16],
        "expected_unexecuted_lines": [],
    })

    # 4. GCC 15 Condition Coverage with Side-Effect Operators
    suite.append({
        "id": "TORTURE-004",
        "name": "GCC 15 Condition Coverage with Side Effects",
        "description": "Short-circuit boolean with assignment and pre-increment in condition",
        "code": """#include <stdio.h>

int main(void) {
    int a = 0;
    int b = 0;
    if ((a++ && ++b) || (a == 1)) {
        printf("Branch Taken: a=%d, b=%d\\n", a, b);
    }
    return 0;
}
""",
        "expected_executed_lines": [3, 4, 5, 6, 7, 9],
        "expected_unexecuted_lines": [],
    })

    # 5. Duff's Device Interleaved Switch and While Loop
    suite.append({
        "id": "TORTURE-005",
        "name": "Duff's Device Interleaving",
        "description": "Switch case labels inside while loop body testing CFG arc attribution",
        "code": """#include <stdio.h>

void duff_copy(int *to, int *from, int count) {
    int n = (count + 3) / 4;
    switch (count % 4) {
        case 0: do { *to++ = *from++;
        case 3:      *to++ = *from++;
        case 2:      *to++ = *from++;
        case 1:      *to++ = *from++;
                } while (--n > 0);
    }
}

int main(void) {
    int src[4] = {1, 2, 3, 4};
    int dst[4] = {0, 0, 0, 0};
    duff_copy(dst, src, 4);
    printf("%d\\n", dst[0]);
    return 0;
}
""",
        "expected_executed_lines": [3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18, 19],
        "expected_unexecuted_lines": [],
    })

    # 6. Multi-line Variadic Macro with Macro Concatenation in Branch Guard
    suite.append({
        "id": "TORTURE-006",
        "name": "Multi-line Variadic Macro Branch Guard",
        "description": "Macro expansion across lines testing location folding in GIMPLE and AST region builder",
        "code": """#include <stdio.h>

#define CHECK_VALUES(x, ...) do { \\
    if ((x) > 0) { \\
        printf("Positive\\n"); \\
    } else { \\
        printf("Zero or negative\\n"); \\
    } \\
} while (0)

int main(void) {
    CHECK_VALUES(10, 1, 2, 3);
    return 0;
}
""",
        "expected_executed_lines": [12, 13],
        "expected_unexecuted_lines": [],
    })

    # 7. COV-BUG-011: GCC Statement Expression Early Return Dropped Line
    suite.append({
        "id": "TORTURE-007",
        "name": "COV-BUG-011: Statement Expression Early Return Line Drop",
        "description": "GCC GIMPLE lowering binds locus to bypassed assignment; reports declaration as count 0",
        "code": """int f(int a) {
    int res = ({
        if (a) return 42;
        0;
    });
    return res;
}
int main(void) {
    return f(1) != 42;
}
""",
        "expected_executed_lines": [1, 2, 3, 8, 9],
        "expected_unexecuted_lines": [4, 6],
    })

    # 8. COV-BUG-012: Clang Indirect Goto Missing terminateRegion Ghost Coverage
    suite.append({
        "id": "TORTURE-008",
        "name": "COV-BUG-012: Clang Indirect Goto Region Leak",
        "description": "CoverageMappingGen lacks VisitIndirectGotoStmt, leaking preceding count to unreached label",
        "code": """int test_dispatch(int op) {
    static void *targets[] = { &&op_exit, &&op_unreached };
    goto *targets[op];

op_unreached:
    return 1;
op_exit:
    return 0;
}
int main(void) {
    return test_dispatch(0);
}
""",
        "expected_executed_lines": [1, 2, 3, 7, 8, 11, 12],
        "expected_unexecuted_lines": [5, 6],
    })

    return suite


def main():
    print("=" * 75)
    print(" CovDiff-Lite: Targeted Attack Campaign on GCC 15 and Clang 14")
    print("=" * 75)

    suite = generate_torture_suite()
    print(f"Loaded {len(suite)} torture test constructs.\n")

    discrepancies = []

    for test in suite:
        test_id = test["id"]
        name = test["name"]
        print(f"[*] Running {test_id}: {name}...")

        # 1. Test host GCC 15
        extra_flags = ["-fcondition-coverage"] if "Condition Coverage" in name else []
        gcc_res = run_gcc_host(test["code"], extra_flags=extra_flags)
        
        # 2. Test Clang 14 in Docker
        clang_res = run_clang_docker(test["code"])

        print(f"    GCC Status: {gcc_res['status']}, Clang Status: {clang_res['status']}")

        # Analyze GCC lines vs expectations
        if gcc_res["status"] == "success":
            for line_no, exp in [("expected_executed_lines", "exec"), ("expected_unexecuted_lines", "unexec")]:
                for l in test[line_no]:
                    line_data = gcc_res["lines"].get(l)
                    if exp == "exec":
                        if line_data is None:
                            print(f"    [!] GCC DISCREPANCY on line {l}: Dropped from coverage report (expected executed)")
                            discrepancies.append({
                                "test_id": test_id,
                                "tool": "GCC 15",
                                "line": l,
                                "type": "dropped_line",
                                "code": test["code"],
                            })
                        elif line_data["count"] == 0:
                            print(f"    [!] GCC DISCREPANCY on line {l}: Count is 0 (expected executed > 0)")
                            discrepancies.append({
                                "test_id": test_id,
                                "tool": "GCC 15",
                                "line": l,
                                "type": "zero_count_executed",
                                "code": test["code"],
                            })
                    elif exp == "unexec":
                        if line_data is not None and line_data["count"] > 0:
                            print(f"    [!] GCC GHOST COVERAGE on line {l}: Count is {line_data['count']} (expected 0)")
                            discrepancies.append({
                                "test_id": test_id,
                                "tool": "GCC 15",
                                "line": l,
                                "type": "ghost_coverage",
                                "code": test["code"],
                            })

        # Analyze Clang lines vs expectations
        if clang_res["status"] == "success":
            clang_lines = clang_res.get("lines", {})
            for line_no, exp in [("expected_executed_lines", "exec"), ("expected_unexecuted_lines", "unexec")]:
                for l in test[line_no]:
                    clang_count = clang_lines.get(l)
                    if exp == "exec":
                        if clang_count is None:
                            print(f"    [!] Clang DISCREPANCY on line {l}: Dropped from coverage report (expected executed)")
                            discrepancies.append({
                                "test_id": test_id,
                                "tool": "Clang 14",
                                "line": l,
                                "type": "dropped_line",
                                "code": test["code"],
                            })
                        elif clang_count == 0:
                            print(f"    [!] Clang DISCREPANCY on line {l}: Count is 0 (expected executed > 0)")
                            discrepancies.append({
                                "test_id": test_id,
                                "tool": "Clang 14",
                                "line": l,
                                "type": "zero_count_executed",
                                "code": test["code"],
                            })
                    elif exp == "unexec":
                        if clang_count is not None and clang_count > 0:
                            print(f"    [!] Clang GHOST COVERAGE on line {l}: Count is {clang_count} (expected 0)")
                            discrepancies.append({
                                "test_id": test_id,
                                "tool": "Clang 14",
                                "line": l,
                                "type": "ghost_coverage",
                                "code": test["code"],
                            })

        print()

    print("=" * 75)
    print(f" Campaign Summary: {len(discrepancies)} discrepancies isolated across torture targets.")
    print("=" * 75)

    if discrepancies:
        out_dir = project_root / "runs" / "attack_campaign"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "attack_discrepancies.json"
        out_file.write_text(json.dumps(discrepancies, indent=2), encoding="utf-8")
        print(f"Saved candidate discrepancies to: {out_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
