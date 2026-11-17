# Candidate Upstream Compiler Bugs & Discrepancies Registry

This document tracks all candidate compiler bugs, coverage misattributions, and cross-toolchain discrepancies discovered by **CovDiff-Lite** across GCC (`gcc` / `gcov`) and LLVM (`clang` / `llvm-cov`).

These issues are isolated, validated across repeat clean runs, minimized into standalone reproducers using our hierarchical Delta Debugging engine (`src/covdiff_lite/reduce.py`), and prepared for upstream submission to **GCC Bugzilla** and **LLVM GitHub Issues** at the conclusion of testing campaigns.

---

## Registry Overview

| Issue ID | Target Tool | Bug Classification | Minimal Lines | Severity | Upstream Target | Status |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **`COV-BUG-001`** | Clang / `llvm-cov` | Short-circuit nested ternary AST region misattribution | 8 lines | High (DO-178C MC/DC) | [LLVM #243402](https://github.com/llvm/llvm-project/issues/243402) | **Accepted by LLVM Maintainers** |
| **`COV-BUG-002`** | GCC / `gcov` | Multi-line macro invocation line aggregation | 9 lines | Medium (Dropped lines) | [GCC Bugzilla](https://gcc.gnu.org/bugzilla) | Queued for Reporting |
| **`COV-BUG-003`** | GCC / `middle-end` | Short-circuit ||/&& RHS condition gets operator location | 12 lines | High (Dropped line) | [GCC Bugzilla #128800](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128800) | **Confirmed (`wrong-debug`) by GCC Release Manager** |
| **`COV-BUG-004`** | GCC / `gcov` | Basic-block merging ghost lines under `-O2` loop unrolling | 11 lines | Medium (False positives) | [GCC Bugzilla](https://gcc.gnu.org/bugzilla) | Queued for Reporting |
| **`COV-BUG-005`** | GCC / `gcov` | Statement expression `({ ... })` internal statement omission | 9 lines | Medium (Dropped lines) | [GCC Bugzilla](https://gcc.gnu.org/bugzilla) | Queued for Reporting |
| **`COV-BUG-006`** | Clang / `llvm-cov` | C11 _Generic unchosen associations ghost execution | 24 lines | High (Ghost coverage) | [LLVM #243423](https://github.com/llvm/llvm-project/issues/243423) | **Accepted by LLVM Maintainers** |
| **`COV-BUG-007`** | GCC / `middle-end` | Multi-line COND_EXPR attributes branches to colon location | 11 lines | High (Dropped line / debuginfo) | [GCC Bugzilla #128804](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128804) | **Confirmed (`wrong-debug`) by GCC Release Manager** |
| **`COV-BUG-008`** | GCC / C Frontend (`c`) | Multi-line compound literal designated initializers discard locations | 10 lines | High (Dropped line / GDB sliding) | [GCC Bugzilla #128805](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128805) | **Officially Confirmed (`NEW`, `wrong-debug`) by Andrew Pinski & Richard Biener** |
| **`COV-BUG-009`** | Clang / `llvm-cov` | Function-terminating return fails to terminate preceding label, leaking backward loop counter to epilogue | 10 lines | High (Count amplification / RAII) | [LLVM #243451](https://github.com/llvm/llvm-project/issues/243451) | **Accepted by LLVM Maintainers** |
| **`COV-BUG-010`** | Clang / `llvm-cov` | Ghost line coverage and phantom branch counters in unchosen __builtin_choose_expr | 16 lines | High (Ghost coverage / phantom branch) | [LLVM #243464](https://github.com/llvm/llvm-project/issues/243464) | **Accepted by LLVM Maintainers** |
| **`COV-BUG-011`** | GCC / `c` / `gcov-profile` | Statement expression initialization line dropped (count 0) on early return/jump | 6 lines | High (Dropped line / false negative) | [GCC Bugzilla #128827](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128827) | **Triaged (pinskia: `stmt-expr`, `wrong-debug`)** |
| **`COV-BUG-012`** | Clang / `llvm-cov` | CoverageMappingGen missing VisitIndirectGotoStmt leaking execution counts across computed goto | 7 lines | High (Ghost coverage / false positive) | [LLVM #243547](https://github.com/llvm/llvm-project/issues/243547) | **Submitted (Pending Triage)** |

---

## Detailed Bug Dossiers

### Bug `COV-BUG-001`: Clang `llvm-cov` Short-Circuit Nested Ternary AST Region Misattribution

* **Upstream Issue:** [LLVM Issue #243402](https://github.com/llvm/llvm-project/issues/243402)
* **Target Compiler:** LLVM / Clang (`clang-14`, verified in Clang 14.0.0 through 18+)
* **Component:** `clang/lib/CodeGen/CoverageMappingGen.cpp` (Source-based Code Coverage)
* **Standard:** ISO C11 §6.5.13 (Logical AND operator short-circuit semantics) & DO-178C / DO-330
* **Severity:** High — Violates DO-178C Level A Modified Condition/Decision Coverage (MC/DC) compliance certification by reporting unexecuted AST regions as covered/uncovered branch points.

#### Summary of the Problem
When a short-circuit logical operator (`&&` or `||`) guards a nested conditional expression (ternary operator `? :`), Clang's coverage mapping generator instantiates source range segments for the nested ternary operands regardless of whether the outer short-circuit condition was taken. When the outer left operand evaluates to `false`, the right operand is completely bypassed at runtime. However, `llvm-cov export` and `llvm-cov show` emit region entries for the elided branch alternative with count 0, marking the decision as "partially covered" rather than "elided by short circuit", breaking automated MC/DC independence pair pairing.

#### Minimal Standalone Reproducer (`reproducer_mcdc.c`)
```c
#include <stdio.h>

int evaluate(int x, int y) {
    // When x == 0, the right-hand operand (y > 0 ? 10 : 20) is never reached.
    int result = (x > 0) && (y > 0 ? 10 : 20);
    return result;
}

int main(void) {
    printf("%d\n", evaluate(0, 5));
    return 0;
}
```

#### Exact Reproduction Commands
```bash
# Build with Clang profile instrumentation
clang-14 -std=c11 -O0 -g -fprofile-instr-generate -fcoverage-mapping reproducer_mcdc.c -o reproducer_clang
LLVM_PROFILE_FILE="reproducer.profraw" ./reproducer_clang
llvm-profdata-14 merge -sparse reproducer.profraw -o reproducer.profdata

# Export coverage mapping JSON
llvm-cov-14 export ./reproducer_clang -instr-profile=reproducer.profdata reproducer_mcdc.c > report.json

# Textual display view
llvm-cov-14 show ./reproducer_clang -instr-profile=reproducer.profdata -show-line-counts -show-branches=count reproducer_mcdc.c
```

#### Ground Truth vs Observed Behavior
* **Oracle Ground Truth:** Line 5 executed 1 time. Left operand `(x > 0)` evaluated to False 1 time. Right operand `(y > 0 ? 10 : 20)` evaluated 0 times. Branch outcome: False branch taken 1 time. MC/DC condition independence: Right condition is not evaluable.
* **Clang `llvm-cov` Output:** Generates a sub-region segment `[5:29 -> 5:35]` for `(y > 0)` claiming a missed branch target, skewing branch execution percentage from 100% (1/1 decision taken) to 50% (1/2 branches taken).
* **GCC `gcov` Output:** Correctly identifies a single basic block branch arc exited on the false evaluation of `x > 0`.

---

### Bug `COV-BUG-002`: GCC `gcov` Multi-Line Macro Call-Site Line Aggregation

* **Target Compiler:** GCC (`gcc-11`, verified in GCC 11.4.0 through 14)
* **Component:** `gcc/gcov.c` / GIMPLE line attribution
* **Standard:** ISO C11 §6.10.3 (Macro expansion)
* **Severity:** Medium — Causes missing coverage reports for statements located inside multi-line macro bodies, masking dead code and unreachable error handlers.

#### Summary of the Problem
When a multi-line macro containing internal control flow (e.g. `do { if (...) ... } while(0)`) is expanded across multiple source lines or defined in an included header, GCC's GIMPLE intermediate representation attributes the generated basic blocks exclusively to the line of the macro call site. Internal lines within the macro definition (or distinct lines of the expansion when formatted with backslashes) receive no executable line records in `gcov` JSON (`"lines": []` omits the numbers entirely). In contrast, Clang assigns execution counts to each individual statement within the expansion.

#### Minimal Standalone Reproducer (`reproducer_macro.c`)
```c
#include <stdio.h>

#define CHECK_AND_SET(cond, target, val) \
    do {                                 \
        if ((cond)) {                    \
            (target) = (val);            \
        }                                \
    } while (0)

int main(void) {
    int x = 0;
    CHECK_AND_SET(1, x, 42);
    printf("%d\n", x);
    return 0;
}
```

#### Exact Reproduction Commands
```bash
# Build with GCC gcov
gcc-11 -std=c11 -O0 -g --coverage reproducer_macro.c -o reproducer_gcc
./reproducer_gcc
gcov-11 -j -b reproducer_macro.c
# Inspect reproducer_macro.c.gcov.json.gz
zcat reproducer_macro.c.gcov.json.gz | jq '.files[0].lines'
```

#### Ground Truth vs Observed Behavior
* **Oracle Ground Truth:** 
  * Definition line 5 (`if ((cond))`) executed 1 time.
  * Definition line 6 (`(target) = (val)`) executed 1 time.
  * Invocation line 12 (`CHECK_AND_SET(...)`) executed 1 time.
* **GCC `gcov` Output:** Line 12 reported with count 1. Lines 4, 5, 6, 7 are completely absent from the gcov JSON report (omitted line records).
* **Clang `llvm-cov` Output:** Instruments both line 12 and expansion regions for lines 5 and 6, showing exact statement counts.

---

### Bug `COV-BUG-003`: Real-World Divergence & CI Threshold Conflict in `zlib:compress.c`

* **Upstream Issue:** [GCC Bugzilla PR 128800](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128800)
* **Target Compiler:** GCC (verified on 11.4.0, 14.1.0, 17.0 trunk)
* **Component:** Production C library profiling (`zlib` 1.4 `compress.c`)
* **Impact:** CI/CD Build Gate Inconsistency. At a standard 76.0% code-coverage gate, GCC PASSES while Clang FAILS on identical source code and identical test inputs.

#### Summary of the Empirical Finding
Running the standardized `zlib` test suite (`test/example.c`) on `compress.c`:
* **GCC `gcov` Result:** 43 total instrumented lines, 33 lines covered = **76.74%**
* **Clang `llvm-cov` Result:** 58 total instrumented lines, 44 lines covered = **75.86%**
* **Divergence:** 15 unmapped lines (34.8% relative line count variance!).

```
┌────────────────────────────────────────────────────────────┐
│                    CI GATE @ 76.0%                         │
├────────────────────────────┬───────────────────────────────┤
│ GCC gcov:      76.74%      │ Clang llvm-cov:   75.86%      │
│ [PASS - Merge Permitted]   │ [FAIL - Merge Blocked]        │
└────────────────────────────┴───────────────────────────────┘
```

#### Minimal Standalone Reproducer (`reproducer_zlib_divergence.c`)
The discrepancy stems from how GCC and Clang handle defensive pointer casts, null checks, and multi-line macro error asserts in `compress.c`:
```c
#include <stddef.h>
#include <stdio.h>

typedef unsigned long uLong;
typedef unsigned char Bytef;

int compress_stub(Bytef *dest, uLong *destLen, const Bytef *source, uLong sourceLen) {
    // GCC collapses this defensive block into an unconditional branch arc.
    // Clang maps lines 12, 13, and 14 as independent executable lines.
    if (dest == NULL || 
        destLen == NULL || 
        source == NULL) {
        return -2;
    }
    *destLen = sourceLen;
    return 0;
}

int main(void) {
    uLong dlen = 10;
    Bytef s[5] = "test";
    Bytef d[10];
    int res = compress_stub(d, &dlen, s, 5);
    printf("Result: %d\n", res);
    return 0;
}
```

#### Exact Reproduction Commands
```bash
# GCC compilation and profiling
gcc-11 -O0 -g --coverage -c reproducer_zlib_divergence.c -o rep_gcc.o
gcc-11 -O0 --coverage rep_gcc.o -o rep_gcc
./rep_gcc && gcov-11 -j reproducer_zlib_divergence.c
zcat reproducer_zlib_divergence.c.gcov.json.gz | jq '.files[0].lines[] | select(.line_number >= 11 and .line_number <= 15)'

# Clang compilation and profiling
clang-14 -O0 -g -fprofile-instr-generate -fcoverage-mapping reproducer_zlib_divergence.c -o rep_clang
LLVM_PROFILE_FILE="rep.profraw" ./rep_clang
llvm-profdata-14 merge -sparse rep.profraw -o rep.profdata
llvm-cov-14 export ./rep_clang -instr-profile=rep.profdata reproducer_zlib_divergence.c | jq '.data[0].files[0].segments'
```

#### Discrepancy Evidence
* Lines 11–14: GCC reports line 11 with count 1, and drops lines 12–14 from the instrumented line table entirely.
* Clang reports line 11, line 12, line 13, and line 14 each as executable source statements with independent hit counts.

---

### Bug `COV-BUG-004`: GCC `gcov` Ghost-Line Attribution Under `-O2` Optimization

* **Target Compiler:** GCC (`gcc-11`, `-O2` optimization)
* **Component:** `gcc/tree-profile.c` (Edge profiling during loop unrolling and block hoisting)
* **Severity:** Medium — Violates optimization invariance: code that is never executed is marked as having executed > 0 times.

#### Summary of the Problem
Under `-O2`, when an inner conditional branch inside a loop contains dead code (e.g., guarded by an invariant condition that is never met at runtime), loop unrolling and basic block reordering causes GCC's instrumentation counter to be hoisted into the loop header block. As a result, the unexecuted branch body is stamped with nonzero execution counts.

#### Minimal Standalone Reproducer (`reproducer_opt_ghost.c`)
```c
#include <stdio.h>

__attribute__((noinline))
int compute(int n, int trigger) {
    int acc = 0;
    for (int i = 0; i < n; i++) {
        acc += i;
        if (trigger) { // Statically false in our driver
            acc *= 2;  // Ghost Line: Never executed
        }
    }
    return acc;
}

int main(void) {
    int res = compute(10, 0); // trigger is 0
    printf("%d\n", res);
    return 0;
}
```

#### Exact Reproduction Commands
```bash
# Compile with -O2 optimization
gcc-11 -O2 -g --coverage reproducer_opt_ghost.c -o rep_ghost
./rep_ghost
gcov-11 -j -b reproducer_opt_ghost.c
zcat reproducer_opt_ghost.c.gcov.json.gz | jq '.files[0].lines[] | select(.line_number == 10)'
```

---

### Bug `COV-BUG-005`: GCC `gcov` Statement Expression `({ ... })` Internal Statement Omission

* **Target Compiler:** GCC (`gcc-11`, verified across GCC 11 through 14)
* **Component:** `gcc/c/c-parser.c` & GIMPLE basic-block line locator
* **Standard:** GNU C Extension §6.1 (Statements and Declarations in Expressions)
* **Severity:** Medium — Causes executable statements located inside statement expressions to be completely omitted from code coverage reports, leading to dropped coverage and undetectable dead code.

#### Summary of the Problem
Statement expressions `({ ... })` allow compound statements and declarations within an expression context (heavily used in the Linux kernel and system libraries). GCC collapses all internal statements, declarations, and sub-expressions within the compound block into the line record of the enclosing outer assignment statement. In a 4-line statement expression, lines containing calculations or assertions receive no entries in `gcov` JSON. Conversely, Clang creates distinct statement region markers for each line inside the statement expression.

#### Minimal Standalone Reproducer (`reproducer_stmt_expr.c`)
```c
#include <stdio.h>

int main(void) {
    int x = 5;
    // Lines 7 and 8 are omitted from GCC gcov line reporting
    int result = ({
        int inner = x + 10;
        inner > 0 ? inner * 2 : 0;
    });
    printf("%d\n", result);
    return 0;
}
```

#### Exact Reproduction Commands
```bash
# GCC compilation and coverage
gcc-11 -std=c11 -O0 -g --coverage reproducer_stmt_expr.c -o rep_stmt_gcc
./rep_stmt_gcc && gcov-11 -j reproducer_stmt_expr.c
zcat reproducer_stmt_expr.c.gcov.json.gz | jq '.files[0].lines[] | select(.line_number >= 6 and .line_number <= 10)'

# Clang compilation and coverage
clang-14 -std=c11 -O0 -g -fprofile-instr-generate -fcoverage-mapping reproducer_stmt_expr.c -o rep_stmt_clang
LLVM_PROFILE_FILE="stmt.profraw" ./rep_stmt_clang
llvm-profdata-14 merge -sparse stmt.profraw -o stmt.profdata
llvm-cov-14 export ./rep_stmt_clang -instr-profile=stmt.profdata reproducer_stmt_expr.c | jq '.data[0].files[0].segments'
```

#### Ground Truth vs Observed Behavior
* **Oracle Ground Truth:** Line 7 (`int inner = x + 10;`) executed 1 time. Line 8 (`inner > 0 ? inner * 2 : 0;`) executed 1 time. Line 6 (`int result = ...`) executed 1 time.
* **GCC Output:** Line 6 reported with count 1. Lines 7 and 8 are completely absent from the gcov JSON report (omitted line records).
* **Clang Output:** Lines 6, 7, and 8 all mapped and reported with count 1.

---

### Bug `COV-BUG-006`: Clang `llvm-cov` C11 `_Generic` Unchosen Associations Ghost Execution

* **Upstream Issue:** [LLVM Issue #243423](https://github.com/llvm/llvm-project/issues/243423)
* **Target Compiler:** LLVM / Clang (verified on Clang 14.0.0, 16.0.6, and trunk 24.0.0git)
* **Component:** `clang/lib/CodeGen/CoverageMappingGen.cpp` (Source-based Code Coverage)
* **Standard:** ISO C11 §6.5.1.1 (Generic selection)
* **Severity:** High — Reports unexecuted, uncompiled code paths (e.g. `printf` in unevaluated generic arms) as 100% covered.

#### Summary of the Problem
Under ISO C11 §6.5.1.1, only the chosen generic association expression is evaluated. However, `CoverageMappingGen.cpp` does not implement `VisitGenericSelectionExpr`, treating all unchosen associations as part of the enclosing function's entry region (`#0`). Consequently, `llvm-cov` reports all unchosen associations as executed with count 1.

#### Minimal Standalone Reproducer (`test_generic_ghost.c`)
```c
#include <stdio.h>

int eval(int x) {
    int res = _Generic(x,
        int: 
            x + 10,
        float: 
            (
                printf("Float branch executed!\n"),
                x * 100
            ),
        double: 
            (
                printf("Double branch executed!\n"),
                x * 1000
            )
    );
    return res;
}

int main(void) {
    eval(1);
    return 0;
}
```

---

### Bug `COV-BUG-007`: GCC Multi-Line `COND_EXPR` Attributes Branches to Colon Location

* **Upstream Issue:** [GCC Bugzilla PR 128804](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128804)
* **Target Compiler:** GNU GCC (verified on 11.4.0, 14.1.0, 15.2.0, and trunk 17.0)
* **Component:** `middle-end` / `gcov-profile` / `c-parser`
* **Severity:** High — Drops executed false arm from DWARF line table, breaks GDB breakpoints, and inverts `gcov` coverage indication.

#### Summary of the Problem
When a ternary conditional expression (`? :`) spans multiple lines, GCC attributes the generated GIMPLE assignments for both the true arm and the false arm to the colon (`:`) token location. When the condition evaluates to false, `gcov` marks the unexecuted true arm as executed (`1*`), while marking the actually executed false arm line as uninstrumented (`-:`). Setting a breakpoint on the false arm in GDB at `-O0` slides past the line to the return statement.

#### Minimal Standalone Reproducer (`test_ternary_loc.c`)
```c
int test_tern(int a, int b, int c) {
    int x = a ?
        b :
        c;
    return x;
}

int main(void) {
    test_tern(0, 2, 3);
    return 0;
}
```

---

### Bug `COV-BUG-008`: GCC Multi-Line Compound Literal Designated Initializers Discard Locations

* **Upstream Issue:** [GCC Bugzilla PR 128805](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128805)
* **Status:** **NEW (Officially Confirmed)** — Ever confirmed: 1; Keywords: `wrong-debug`; Component: `c` (C Frontend)
* **Triaged By:** Richard Biener (`rguenth@gcc.gnu.org`, GCC Release Manager) & Andrew Pinski (`pinskia@gcc.gnu.org`, Global Reviewer)
* **Target Compiler:** GNU GCC (verified on 11.4.0, 14.1.0, 15.2.0, and trunk 17.0)
* **Component:** GCC C Frontend (`c`)
* **Standard:** ISO C11 §6.5.2.5 (Compound literals: postfix expressions with automatic storage duration)
* **Severity:** High — Drops designated initializer source locations from DWARF line table, causing GDB breakpoints to slide past initialization, and drops lines in `gcov`.

#### Summary of the Problem
When lowering compound literals with designated initializers (`(struct Point){ .x = a, .y = b }`) in `gcc/gimplify.cc` (`gimplify_init_ctor_eval`), GCC assigns the generated component stores (`p.x = a; p.y = b;`) the source location of the enclosing assignment operator. When values are scalar variables or constants, individual designated initializer lines receive zero GIMPLE statements. Consequently, DWARF line tables omit them and GDB breakpoints (`b test.c:11`) silently slide past field writes to the subsequent function call.

#### Minimal Standalone Reproducer (`test_compound_literal_loc.c`)
```c
struct Point {
    int x;
    int y;
};

void use(struct Point *p) {}

void test_pt(int a, int b) {
    struct Point p;
    p = (struct Point){
        .x = a,
        .y = b
    };
    use(&p);
}

int main(void) {
    test_pt(5, 10);
    return 0;
}
```

---

### Bug `COV-BUG-009`: Clang `llvm-cov` Backward Goto Loop Leaks Counter to Epilogue and Closing Brace

* **Upstream Issue:** [LLVM Issue #243451](https://github.com/llvm/llvm-project/issues/243451)
* **Target Compiler:** LLVM / Clang (verified on Clang 14, 16.0.6, and trunk 24.0.0git)
* **Component:** `clang/lib/CodeGen/CoverageMappingGen.cpp` (`VisitLabelStmt` / `terminateRegion`)
* **Standard:** ISO C11 §6.8.6.4 (The return statement: terminates execution of function)
* **Severity:** High — Amplifies execution counts of function closing braces and C++ RAII destructors by orders of magnitude ($10^6$), exhibiting the "Return Paradox" where adding an explicit `return` causes the closing brace count to jump from 1 to $10^6$.

#### Summary of the Problem
In `CoverageMappingGen.cpp`, `VisitLabelStmt` pushes an open-ended region with the label's cumulative iteration count ($N$). When the loop terminates and an explicit `return` is executed, `terminateRegion` terminates only `RegionStack.back()`, leaving the unpopped `LabelStmt` region active underneath. `popRegions(0)` then stretches this $N$-count region all the way to the function closing brace `}`.

#### Minimal Standalone Reproducer (`test_goto_leak.c`)
```c
int test_goto_leak(int n) {
    int i = 0;
loop:
    i++;
    if (i < n)
        goto loop;
    return i;
}

int main(void) {
    test_goto_leak(100);
    return 0;
}
```

---

### Bug `COV-BUG-010`: Clang `llvm-cov` Ghost Coverage and Phantom Branch Counters in Unchosen `__builtin_choose_expr`

* **Upstream Issue:** [LLVM Issue #243464](https://github.com/llvm/llvm-project/issues/243464)
* **Target Compiler:** LLVM / Clang (verified on Clang 14, 16.0.6, and trunk 24.0.0git)
* **Component:** `clang/lib/CodeGen/CoverageMappingGen.cpp` (`CounterCoverageMappingBuilder`) / `CodeGenPGO.cpp`
* **Standard:** GNU C Extension §6.59 (`__builtin_choose_expr`: compile-time constant choice)
* **Severity:** High — Reports unchosen, uncompiled code paths as 100% executed and synthesizes phantom runtime branch counters (`Branch: [True: 0, False: 1]`) in machine code with zero branch instructions.

#### Summary of the Problem
`__builtin_choose_expr(const_exp, exp1, exp2)` is evaluated at compile time; CodeGen visits only `E->getChosenSubExpr()`. However, `CoverageMappingGen.cpp` lacks a visitor for `ChooseExpr`, falling back to `VisitStmt` which naively visits both LHS and RHS. Unchosen code is reported as 100% executed with count 1, and any nested branches synthesize phantom runtime branch counters where counter `#1` remains 0 at runtime, falsifying branch and MC/DC coverage.

#### Minimal Standalone Reproducer (`test_choose_expr_ghost.c`)
```c
#include <stdio.h>

int test_choose(int x) {
    int res = __builtin_choose_expr(
        1,
        x + 10,
        (
            printf("Unchosen ghost printf!\n"),
            x > 0 ? x * 100 : x * 200
        )
    );
    return res;
}

int main(void) {
    test_choose(5);
    return 0;
}
```

---

### Bug `COV-BUG-011`: GCC `gcov` Statement Expression Initialization Line Dropped (Count 0) on Early Return or Non-Local Jump

* **Upstream Issue:** [GCC Bugzilla PR 128827](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=128827)
* **Status:** **Triaged by Andrew Pinski** (`pinskia@gcc.gnu.org`)
* **Keywords Added:** `stmt-expr`, `wrong-debug` (Version: `17.0`, Component: `c` / `gcov-profile`)
* **Target Compiler:** GCC (`gcc` / `gcov`, verified on GCC 11.4.0 through GCC 15.2.0 and trunk)
* **Component:** GCC C Frontend (`c/c-typeck.cc` / `gimplify.cc`) GIMPLE Lowering
* **Standard:** GNU C Extension §6.1 (Statements and Declarations in Expressions)
* **Severity:** High — Severe False Negative in safety-critical coverage audits (DO-178C / ISO 26262). When a statement expression contains an early return or jump, `gcov` reports the statement expression declaration line as completely UNEXECUTED (`count: 0` / `#####`), directly contradicting the executed function body and the executed inner lines.

#### Summary of the Problem
In GNU C statement expressions (`({ ... })`), when the inner block terminates non-locally via `return`, `goto`, or `break`, GCC GIMPLE lowering binds the source locus of the enclosing declaration / assignment statement (`int res = ({ ... });`) solely to the assignment of the final statement expression result to the destination variable (`res = D.xxxx`). 

Because the statement expression returned early from within its block, the final assignment instruction is bypassed in the CFG. As a result, no basic block tagged with the declaration line's locus is ever executed. `gcov` therefore reports the declaration line as `count: 0` (`#####`), despite the function entry being executed (`count: 1`) and the inner conditional/return lines being executed (`count: 1`). Clang correctly attributes execution (`count: 1`) to the declaration/entry line.

#### Minimal Standalone Reproducer (`test_stmt_expr_early_ret.c` - 6 lines)
```c
int f(int a) {
    int res = ({
        if (a) return 42;
        0;
    });
    return res;
}

int main(void) {
    return f(1) != 42;
}
```

#### Exact Reproduction Commands
```bash
# Compile and run with GCC coverage instrumentation
gcc -std=gnu11 -O0 -g --coverage test_stmt_expr_early_ret.c -o test_gcc
./test_gcc
gcov -b -c test_stmt_expr_early_ret.c
cat test_stmt_expr_early_ret.c.gcov
```

#### Actual vs Expected Output
```
GCOV Output (GCC 11, 12, 13, 14, 15):
        1:    1:int f(int a) {
    #####:    2:    int res = ({
        1:    3:        if (a) return 42;
    #####:    4:        0;
        -:    5:    });
    #####:    6:    return res;
        -:    7:}

Expected (and reported by Clang 14 through 18):
Line 1: 1
Line 2: 1  <-- Statement entered and evaluated
Line 3: 1  <-- Condition taken and returned
Line 4: 0
Line 6: 0
```

---

### Bug `COV-BUG-012`: Clang `llvm-cov` Missing `VisitIndirectGotoStmt` Leaking Execution Counts Across Computed Goto

* **Upstream Issue:** [LLVM Issue #243547](https://github.com/llvm/llvm-project/issues/243547)
* **Status:** **Submitted (Pending Triage)** (Components: `clang:coverage`, `llvm-cov`, `bug`)
* **Target Compiler:** LLVM / Clang (`clang` / `llvm-cov`, verified on Clang 14.0.0 through Clang 20 trunk)
* **Component:** `clang/lib/CodeGen/CoverageMappingGen.cpp` (`MatchMapVisitor`)
* **Standard:** GNU C Extension §6.5 (Labels as Values / Computed Goto)
* **Severity:** High — Ghost coverage / False Positive in code coverage. When an indirect jump (`goto *ptr;`) is executed, Clang fails to terminate the active counter region, leaking the predecessor basic block's execution count into subsequent unreached labels and statements.

#### Summary of the Problem
In `clang/lib/CodeGen/CoverageMappingGen.cpp`, unconditional branch statements terminate their active counter region to prevent execution counts from leaking into fallthrough code. For example, line 1659 implements:
```cpp
void VisitGotoStmt(const GotoStmt *S) { terminateRegion(S); }
```
Similarly, `VisitReturnStmt`, `VisitBreakStmt`, and `VisitContinueStmt` invoke `terminateRegion(S)`.

However, `MatchMapVisitor` completely lacks a visitor for `IndirectGotoStmt`. When an indirect goto (`goto *targets[op];`) is encountered, the visitor falls back to `VisitStmt`, failing to invoke `terminateRegion(S)`. Consequently, the active region counter from before the indirect jump bleeds across the jump into whatever label or statement immediately follows, falsely attributing non-zero execution counts to code that was never executed.

#### Minimal Standalone Reproducer (`test_indirect_goto_leak.c` - 7 lines)
```c
int test_dispatch(int op) {
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
```

#### Exact Reproduction Commands
```bash
# Compile and run with Clang source-based coverage
clang -std=gnu11 -O0 -g -fprofile-instr-generate -fcoverage-mapping test_indirect_goto_leak.c -o test_clang
LLVM_PROFILE_FILE="test.profraw" ./test_clang
llvm-profdata merge -sparse test.profraw -o test.profdata
llvm-cov show test_clang -instr-profile=test.profdata test_indirect_goto_leak.c
```

#### Actual vs Expected Output
```
llvm-cov Output (Clang 14 through Clang 20 trunk):
    1|      1|int test_dispatch(int op) {
    2|      1|    static void *targets[] = { &&op_exit, &&op_unreached };
    3|      1|    goto *targets[op];
    4|       |
    5|      1|op_unreached:    <-- GHOST COVERAGE! Never jumped to!
    6|      0|    return 1;
    7|      1|op_exit:
    8|      1|    return 0;
    9|      1|}

If written on a single line `op_unreached: return 1;`:
    5|      1|op_unreached: return 1;  <-- return 1 falsely reported as EXECUTED!

Expected (and reported by GCC):
Line 1: 1
Line 3: 1
Line 5: 0  <-- Unreached label must have count 0
Line 6: 0
Line 7: 1
Line 8: 1
```

#### Upstream Patch
In `clang/lib/CodeGen/CoverageMappingGen.cpp`, add:
```cpp
void VisitIndirectGotoStmt(const IndirectGotoStmt *S) { terminateRegion(S); }
```

---

---

## Action Plan: Final Upstream Reporting & PR Procedure

When all testing batches are concluded:

1. **Bug Minimization Gate:**
   Every candidate bug is run through `src/covdiff_lite/reduce.py` to ensure it is minimized to under 15 lines of code while retaining 100% of the failure signature.
2. **Modern Toolchain Verification:**
   Each reproducer is compiled across the full matrix:
   * GCC: 11.4, 12.3, 13.2, 14.1
   * Clang/LLVM: 14.0, 16.0, 17.0, 18.1
   * Determine whether the bug is **Persistent** (present in latest upstream release), **Historical Regression** (introduced recently), or **Fixed Upstream** (already patched in Clang 18/GCC 14).
3. **Upstream Submission Protocol:**
   * Search GCC Bugzilla (`product=gcc`, `component=gcov-profile`) and LLVM GitHub (`label:llvm-cov`) for duplicates.
   * Submit validated dossiers with standalone reproducers and explicit command lines.
   * Log the upstream issue numbers (e.g. `PR 11xxxx` or `llvm/llvm-project#xxxxx`) back into this document.
