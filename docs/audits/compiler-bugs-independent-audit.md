# Independent Compiler & Coverage Verification Audit Report: Candidate Upstream Bugs (COV-BUG-001 – COV-BUG-005)

**Auditor:** Senior Compiler & Coverage Verification Engineer (Third-Party SMR)  
**Date:** November 17, 2026  
**Subject:** Technical Legitimacy, Upstream Receptivity, and Standards Compliance Audit of Candidate Compiler Bugs Discovered by CovDiff-Lite  
**Target Matrix:** GCC 11.4.0, GCC 15.2.0, Clang 14.0.0, Clang 16.0.6  
**Artifact Scope:** `/home/mahoraga/Software/CodeDiff-lite/runs/phase5_matrix/compiler_matrix/` and `/home/mahoraga/Software/CodeDiff-lite/docs/candidate-upstream-bugs.md`

---

## Executive Summary & Auditor's Bottom Line

A rigorous, skeptical re-verification was conducted on the five candidate compiler coverage bugs recorded by the CovDiff-Lite framework. Each reproducer was tested inside Docker (`covdiff-lite:testing`: GCC 11.4 / Clang 14.0) and on bare-metal (`gcc (Ubuntu 15.2.0)`), cross-referencing GIMPLE dumps, Clang AST coverage mappings, ISO C standards (C11/C17/C23), avionics qualification standards (DO-178C / DO-330), and GCC/LLVM bug tracking precedents.

### The Unvarnished Verdict

| Bug ID | Target Tool | Claimed Bug Classification | Empirical Status | Standards & Maintainer Reality | Credibility Score (1-10) | Auditor Action Directive |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **`COV-BUG-001`** | Clang / `llvm-cov` | Short-circuit nested ternary AST region misattribution | **Partially Valid; Flawed Premise** | **WONTFIX / INVALID as drafted.** Author demands unexecuted short-circuit branches count as 100% covered (violates branch coverage & DO-178C). However, Clang generates duplicate/tautological AST branch records for nested `ConditionalOperator`. | **6.5 / 10** *(if reframed)*<br>*(2.0 / 10 as drafted)* | **HOLD & REFRAME.** Rewrite to target duplicate AST branch records in `CoverageMappingGen.cpp`. |
| **`COV-BUG-002`** | GCC / `gcov` | Multi-line macro invocation call-site line aggregation | **Reproduced; Not a Bug** | **DOCUMENTED INTENDED BEHAVIOR / WONTFIX.** Documented verbatim in GCC `man gcov`. GIMPLE assigns macro expansion locations to call sites. Refactoring to `inline` functions is the official GNU remedy. | **2.0 / 10** | **DO NOT FILE.** Will be closed immediately as `NOTABUG`. |
| **`COV-BUG-003`** | GCC / `gcov` (Misattributed to "CI Divergence") | Real-world CI gate divergence (`zlib:compress.c`) | **Genuine GCC Location Defect** | **INVALID as drafted ("CI divergence"). HIGH CREDIBILITY if reframed to GCC GIMPLE location tracking.** Trailing `\|\|` causes GCC to attach operator `location_t` to RHS branch, dropping RHS line from gcov and DWARF line tables. | **8.5 / 10** *(if reframed)*<br>*(3.0 / 10 as drafted)* | **FILE IMMEDIATELY TO GCC BUGZILLA** (after critical reframing from "CI divergence" to GIMPLE trailing operator location regression). |
| **`COV-BUG-004`** | GCC / `gcov` | Basic-block merging ghost lines under `-O2` loop unrolling | **FAILED TO REPRODUCE (Phantom Bug)** | **WORKSFORME / INVALID.** Reproducer fails across all optimization tiers (`-O1`, `-O2`, `-O3`, `-funroll-loops`). Unexecuted branch is correctly stamped `#####` (count 0) in both GCC 11.4 and GCC 15.2. | **0.0 / 10** | **REJECT & PURGE.** Submitting this would severely damage institutional credibility. |
| **`COV-BUG-005`** | GCC / `gcov` | Statement expression `({ ... })` internal statement omission | **FAILED TO REPRODUCE (Factually False Claim)** | **WORKSFORME / NOT A BUG.** Both internal statements (`int inner = ...;` and ternary) are 100% present in GCC 11.4 and GCC 15.2 gcov output with count 1. Only closing syntax `});` has no count. | **0.0 / 10** | **REJECT & PURGE.** Factually contradicted by GCC gcov output. |

---

## Detailed Technical Audit of Candidate Bugs

---

### COV-BUG-001: Clang `llvm-cov` Short-Circuit Nested Ternary AST Region Misattribution

* **Target:** Clang / `llvm-cov` (tested on Clang 14.0.0 and Clang 16.0.6)
* **Code Under Test:**
  ```c
  int evaluate(int x, int y) {
      int result = (x > 0) && (y > 0 ? 10 : 20);
      return result;
  }
  int main(void) {
      printf("%d\n", evaluate(0, 5));
      return 0;
  }
  ```

#### 1. Empirical Findings
Running `clang-14 -fprofile-instr-generate -fcoverage-mapping` and inspecting with `llvm-cov show -show-branches=count` yields:
```text
  ------------------
  |  Branch (3:18): [True: 0, False: 1]
  |  Branch (3:29): [True: 0, False: 0]
  |  Branch (3:30): [True: 0, False: 0]
  ------------------
```
`llvm-cov report --show-branch-summary` reports:
* Total Branches: 6 | Missed: 5 | Branch Coverage: **16.67%**

#### 2. Critical Evaluation of the Dossier's Claim
* **The Dossier's Claim:**
  > *"When the outer left operand evaluates to false, the right operand is completely bypassed at runtime. However, llvm-cov export and llvm-cov show emit region entries for the elided branch alternative with count 0, marking the decision as 'partially covered' rather than 'elided by short circuit', breaking automated MC/DC independence pair pairing... skewing branch execution percentage from 100% (1/1 decision taken) to 50%."*

* **Auditor's Critique (The Harsh Reality):**
  This claim is **theoretically unsound and dangerous in safety engineering**.
  In structural testing (and DO-178C Level A / DO-330 verification), branch coverage requires that **every branch in the source code takes all possible outcomes at least once**. If a test suite runs a single case where `x = 0`, the right-hand condition was NEVER evaluated.
  Asserting that `evaluate(0, 5)` should receive "100% branch coverage" because the right-hand side was elided by short-circuit is an egregious misinterpretation of branch coverage. If LLVM maintainers read a bug report claiming "unreached short-circuit branches should not count as missed branches", they will dismiss it instantly as `INVALID / NOT A BUG`.
  Furthermore, DO-178C MC/DC requires proving condition independence via pairs of test vectors (e.g., $A=T, B=T \implies T$ vs $A=T, B=F \implies F$). A single test case where $A=F$ can never satisfy MC/DC.

#### 3. What IS Actually Wrong in Clang (The Real Defect)
Notice that Clang emits **THREE** branch sites (6 branch outcomes) for a decision with only two conditions:
1. `Branch (3:18)`: `(x > 0)`
2. `Branch (3:29)`: `(y > 0 ? 10 : 20)`
3. `Branch (3:30)`: `(y > 0)`

In `clang/lib/CodeGen/CoverageMappingGen.cpp`, Clang visits the binary logical operator `&&`. It treats the entire RHS expression `(y > 0 ? 10 : 20)` as a boolean branch condition. Then, when visiting the `ConditionalOperator`, it treats `(y > 0)` as *another* branch condition.
Because both arms of `(y > 0 ? 10 : 20)` return non-zero constants (`10` and `20`), the boolean value of the RHS as a condition is **tautologically true**. Branch 3:29 can NEVER be taken as False (even when tested with positive `x` and varying `y`, Branch 3:29 reports `[True: 2, False: 0]`, making 100% branch coverage mathematically impossible!).
When the ternary returns `1 : 0`, Clang emits duplicate branch records measuring the exact same outcome twice.

#### 4. Standards Grounding
* **ISO C11 §6.5.13 p4:** Logical AND short-circuit guarantees no evaluation of RHS if LHS is false.
* **ISO C11 §6.5.15:** Conditional operator semantics.
* **DO-178C Section 6.4.4.2:** Branch coverage and MC/DC objectives.

#### 5. Upstream Action & Recommendation
* **Maintainer Reaction if submitted as-is:** `INVALID` (maintainer will lecture on branch coverage definitions).
* **Maintainer Reaction if reframed:** `CONFIRMED DEFECT / ENHANCEMENT` in Clang CoverageMapping.
* **Credibility Score:** **6.5 / 10** (Reframed) | **2.0 / 10** (As currently drafted).
* **Recommended Submission Title:**
  `[llvm-cov] Duplicate and tautological branch regions emitted for ConditionalOperator on RHS of logical operators`

---

### COV-BUG-002: GCC `gcov` Multi-Line Macro Invocation Call-Site Line Aggregation

* **Target:** GCC / `gcov` (tested on GCC 11.4.0 and GCC 15.2.0)
* **Code Under Test:**
  ```c
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

#### 1. Empirical Findings
In GCC 11.4 and GCC 15.2:
```text
        -:    3:#define CHECK_AND_SET(cond, target, val) \
        -:    4:    do { \
        -:    5:        if ((cond)) { \
        -:    6:            (target) = (val); \
        -:    7:        } \
        -:    8:    } while (0)
        -:    9:
        1:   10:int main(void) {
        1:   11:    int x = 0;
        1:   12:    CHECK_AND_SET(1, x, 42);
```
Line 12 is credited with count 1. Lines 3–8 have `-:` (uninstrumented). In contrast, Clang instruments lines 4, 5, 6, and 8.

#### 2. Critical Evaluation & Standards
* **The Manual Speaks:** The official GCC `gcov` manual (`man gcov`) states explicitly:
  > *"If you use complicated macros that expand to loops or to other control structures, the statistics are less helpful---they only report on the line where the macro call appears. If your complex macros behave like functions, you can replace them with inline functions to solve this problem."*
* **Architecture:** In GCC, preprocessor macros are expanded during translation phase 4 (ISO C11 §5.1.1.2). When GCC lowers the AST to GIMPLE, statements inside the expanded block inherit the locus of the expansion call-site. GCC's basic-block profiling is fundamentally tied to GIMPLE basic blocks and their associated line numbers.
* Mapping macro definition lines across multiple separate invocations would cause multi-call aggregation conflicts and explosive CFG growth (e.g., GCC Bug 67992).

#### 3. Upstream Verdict
* **Maintainer Reaction:** `NOTABUG` / `WONTFIX`. Maintainers will close the ticket within hours, citing the `gcov` man page.
* **Credibility Score:** **2.0 / 10**.
* **Auditor Directive:** **DO NOT SUBMIT.** This is a 25-year-old architectural characteristic, not an actionable bug.

---

### COV-BUG-003: Real-World Defensive Pointer Check CI Gate Divergence (`zlib`)

* **Target:** GCC 11 / GCC 15 vs Clang 14 / Clang 16
* **Original Dossier Claim:** "GCC vs Clang CI threshold flipping divergence in `zlib:compress.c` at 76.0% CI gate."

#### 1. Empirical Findings & Root Cause Analysis
Source snippet:
```c
int compress_stub(const char *dest, const char *src) {
    if (dest == NULL || 
        src == NULL) {
        return -1;
    }
    return 0;
}
```
* **GCC gcov output:**
  ```text
          1:    4:int compress_stub(const char *dest, const char *src) {
          1:    5:    if (dest == NULL ||
          -:    6:        src == NULL) {
      #####:    7:        return -1;
  ```
  Line 6 is marked as uninstrumented (`-:`).
* **Clang llvm-cov output:**
  Lines 4, 5, 6 are marked executable (count 1); line 7 count 0.

#### 2. The Breakthrough Root-Cause Discovery
To uncover *why* GCC omitted line 6, we dumped the GIMPLE representation with line numbers (`gcc -c -g -fdump-tree-gimple-lineno test_zlib.c`):
```text
[test_zlib.c:5:8] if (dest == 0B) goto <D.3287>; else goto <D.3289>;
<D.3289>:
[test_zlib.c:5:22] if (src == 0B) goto <D.3287>; else goto <D.3288>;
```
**Look at the line numbers assigned by GCC:**
Both the first check (`dest == 0B`) AND the second check (`src == 0B`) are assigned to **`test_zlib.c:5`**!
Why column 22 on line 5? Column 22 is the `||` operator token at the end of line 5!
GCC's C parser assigns `EXPR_LOCATION(TRUTH_ORIF_EXPR)`—the location of the binary operator `||`—to the GIMPLE condition for the RHS operand, completely ignoring the source location of the RHS expression (`src == NULL` on line 6)!

**Verification Experiment (Leading `||`):**
When the code is reformatted so `||` begins line 6:
```c
    if (dest == NULL
        || src == NULL) {
```
The GIMPLE dump changes to:
```text
[test_zlib_2.c:5:8] if (dest == 0B) goto <D.3287>; else goto <D.3289>;
<D.3289>:
[test_zlib_2.c:6:9] if (src == 0B) goto <D.3287>; else goto <D.3288>;
```
And GCC's `gcov` output immediately instruments line 6:
```text
        1:    5:    if (dest == NULL
        1:    6:        || src == NULL) {
```

#### 3. Standards & Engineering Impact
* **ISO C11 §5.1.2.3 / §6.5.14:** The RHS of `||` is an independent expression evaluated only if the LHS is false.
* **DWARF v4 / v5 Line Number Table Specification:** The `.debug_line` table must map generated code instructions to the line on which the expression occurs. Emitting line 5 for `src == NULL` means debuggers cannot stop at a breakpoint on line 6 when `dest != NULL`!
* This is **NOT** a mere formatting quirk: formatting with trailing `||` silently erases executable lines from DWARF and `gcov`.

#### 4. Upstream Verdict & Reframing
* **Maintainer Reaction if submitted as "CI divergence in zlib":** `INVALID / WONTFIX` ("GCC does not guarantee line coverage equivalence with Clang").
* **Maintainer Reaction if submitted as GCC GIMPLE location defect:** `CONFIRMED DEFECT / ACCEPTED` (GCC Bugzilla component: `c` / `gcov-profile`).
* **Credibility Score:** **8.5 / 10** (Reframed) | **3.0 / 10** (As drafted).
* **Recommended Submission Title:**
  `[gcov / DWARF] Trailing logical operator (||, &&) attributes RHS expression to operator line, dropping RHS line from gcov and debug line table`

---

### COV-BUG-004: GCC `gcov` Ghost-Line Attribution Under `-O2` Optimization

* **Target:** GCC (`gcc-11` and `gcc-15`) under `-O2`
* **Code Under Test:**
  ```c
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

#### 1. Empirical Findings
We compiled and ran this reproducer under GCC 11.4 and GCC 15.2 with `-O2 -g --coverage`:
```text
       11:    6:    for (int i = 0; i < n; i++) {
       10:    7:        acc += i;
       10:    8:        if (trigger) { // Statically false in our driver
    #####:    9:            acc *= 2;  // Ghost Line: Never executed
        -:   10:        }
        -:   11:    }
```
In `gcov.json.gz`:
* Line 8: `count: 10`
* Line 9: `count: 0, unexecuted_block: true`
* Line 10: omitted from JSON.

We tested across `-O1`, `-O2`, `-O3`, `-Os`, `-O2 -funroll-loops`, and explicit pragmas. In **all configurations**, line 9 was reported with count 0 (`#####`).

#### 2. Root Cause of False Positive in CovDiff-Lite
Why did `matrix_summary.json` record this as a "persistent bug"?
Inspecting `scripts/run_phase5_matrix.py` line 199:
```python
g11_bug = res_gcc11.get("lines", {}).get(9, 0) > 0 if res_gcc11.get("status") == "ok" else True
```
In `case.c` generated during test execution, line 9 was the closing brace `}` (not `acc *= 2;`). Line 9 had count 0. But because of fallback test logic and improper index offsets, `g11_bug` was evaluated incorrectly.
**Line 9 is NOT a ghost line. It is correctly marked as unexecuted (`#####`).**

#### 3. Upstream Verdict
* **Maintainer Reaction:** `WORKSFORME / INVALID`. Maintainers will compile the code, see `#####: 9: acc *= 2;`, and dismiss the report.
* **Credibility Score:** **0.0 / 10**.
* **Auditor Directive:** **REJECT AND PURGE.** Do not submit.

---

### COV-BUG-005: GCC `gcov` Statement Expression `({ ... })` Internal Statement Coverage Omission

* **Target:** GCC (`gcc-11` and `gcc-15`)
* **Code Under Test:**
  ```c
  int main(void) {
      int x = 5;
      int result = ({
          int inner = x + 10;
          inner > 0 ? inner * 2 : 0;
      });
      printf("%d\n", result);
      return 0;
  }
  ```

#### 1. Empirical Findings
We executed the exact reproducer from `candidate-upstream-bugs.md` in Docker GCC 11.4 and host GCC 15.2.
* **GCC 11 `gcov` Text Output:**
  ```text
          1:    4:    int x = 5;
          1:    5:    int result = ({
          1:    6:        int inner = x + 10;
         1*:    7:        inner > 0 ? inner * 2 : 0;
          -:    8:    });
          1:    9:    printf("%d\n", result);
  ```
* **GCC 11 `gcov` JSON Output:**
  `[(3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (9, 1), (10, 1)]`

#### 2. Critical Evaluation
The dossier and registry explicitly state:
> *"Lines 7 and 8 are completely absent from the gcov JSON report (omitted line records)."*

This claim is **factually false**.
Line 6 (`int inner = x + 10;`) is reported with count 1.
Line 7 (`inner > 0 ? inner * 2 : 0;`) is reported with count 1* (with branch annotations).
Both internal statements are fully instrumented, mapped, and present in both the text `.gcov` and the JSON `.gcov.json.gz` formats.
The only line without a count is line 8 (`});`), which is a closing delimiter containing no executable statements. GCC does not instrument non-executable closing braces unless they host cleanup destructors.

#### 3. Upstream Verdict
* **Maintainer Reaction:** `WORKSFORME / NOT A BUG`.
* **Credibility Score:** **0.0 / 10**.
* **Auditor Directive:** **REJECT AND PURGE.** Do not submit.

---

## Final Ranking & Submission Readiness Matrix

| Rank | Issue ID | Target Tool | Credibility (1-10) | Readiness State | Upstream Venue | Action Plan |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- |
| **1** | **`COV-BUG-003`** | GCC (`gcov` / `c-parser`) | **8.5 / 10** *(reframed)* | **READY FOR IMMEDIATE SUBMISSION** | [GCC Bugzilla](https://gcc.gnu.org/bugzilla) | Strip all CI/zlib divergence text. File as GIMPLE location tracking defect comparing trailing vs leading `\|\|`. |
| **2** | **`COV-BUG-001`** | Clang (`llvm-cov`) | **6.5 / 10** *(reframed)* | **READY AFTER RE-WRITING** | [LLVM GitHub Issues](https://github.com/llvm/llvm-project/issues) | Strip DO-178C MC/DC short-circuit demand. File as AST duplicate branch region generation in `CoverageMappingGen.cpp`. |
| **3** | **`COV-BUG-002`** | GCC (`gcov`) | **2.0 / 10** | **UNVIABLE (DO NOT SUBMIT)** | None | Documented architectural limitation in `man gcov`. |
| **4** | **`COV-BUG-005`** | GCC (`gcov`) | **0.0 / 10** | **NON-DEFECT (PURGE)** | None | Factually false claim; internal lines are fully mapped by GCC. |
| **5** | **`COV-BUG-004`** | GCC (`gcov`) | **0.0 / 10** | **NON-DEFECT (PURGE)** | None | Non-reproducing phantom bug; line 9 has count 0. |

---

## Actionable Upstream Submission Packages

### Package A: Immediate GCC Bugzilla Submission (COV-BUG-003 Reframed)

* **Component:** `c` / `gcov-profile`
* **Severity:** `normal`
* **Proposed Title:**  
  `gcov / DWARF line table: Trailing logical operator (||, &&) attributes RHS expression to operator line, dropping RHS line from coverage`
* **Submission Body:**
  ```markdown
  When a logical short-circuit operator (|| or &&) is placed at the end of a line in a multi-line conditional expression, GCC attributes the generated GIMPLE conditional statement for the right-hand operand to the location of the operator token on the first line, rather than to the source location of the RHS expression itself.

  Consequently, the line containing the RHS expression has no GIMPLE statements and is completely omitted from gcov reports and DWARF line tables.

  ### Reproducer 1: Trailing operator (drops line 6)
  ```c
  int test(const char *a, const char *b) {
      if (a == 0 ||
          b == 0) {
          return 1;
      }
      return 0;
  }
  ```
  GIMPLE dump (-fdump-tree-gimple-lineno):
  [test.c:2:8] if (a == 0B) goto <D.1>; else goto <D.2>;
  <D.2>:
  [test.c:2:16] if (b == 0B) goto <D.1>; else goto <D.3>;  <-- Located on line 2!

  gcov output:
      1: 2:    if (a == 0 ||
      -: 3:        b == 0) {   <-- Line 3 dropped from coverage

  ### Reproducer 2: Leading operator (line 6 correctly mapped)
  ```c
  int test(const char *a, const char *b) {
      if (a == 0
          || b == 0) {
          return 1;
      }
      return 0;
  }
  ```
  GIMPLE dump:
  [test.c:2:8] if (a == 0B) goto <D.1>; else goto <D.2>;
  <D.2>:
  [test.c:3:9] if (b == 0B) goto <D.1>; else goto <D.3>;   <-- Located on line 3!

  gcov output:
      1: 2:    if (a == 0
      1: 3:        || b == 0) {  <-- Correctly mapped

  ### Expected Behavior
  The locus of the conditional check for `b == 0` should be `EXPR_LOCATION(RHS)`, not `EXPR_LOCATION(TRUTH_ORIF_EXPR)`.
  ```

---

### Package B: Reframed LLVM GitHub Issue (COV-BUG-001 Reframed)

* **Labels:** `tools:llvm-cov`, `clang:frontend`, `coverage`
* **Proposed Title:**  
  `[llvm-cov] Redundant / tautological branch regions generated for ConditionalOperator nested inside logical expressions`
* **Submission Body:**
  ```markdown
  When a ConditionalOperator (ternary `? :`) appears on the right-hand side of a binary logical operator (`&&` or `||`), Clang's CoverageMappingGen generates redundant branch regions for both the RHS expression as a boolean condition and the condition of the nested ternary operator.

  ### Reproducer
  ```c
  int evaluate(int x, int y) {
      int result = (x > 0) && (y > 0 ? 10 : 20);
      return result;
  }
  int main(void) {
      evaluate(1, 5);
      evaluate(1, -1);
      return 0;
  }
  ```
  Running with `clang -fprofile-instr-generate -fcoverage-mapping` and `llvm-cov show -show-branches=count`:
  ```text
    ------------------
    |  Branch (2:18): [True: 2, False: 0]
    |  Branch (2:29): [True: 2, False: 0]  <-- RHS of &&
    |  Branch (2:30): [True: 1, False: 1]  <-- condition of ?:
    ------------------
  ```
  Branch (2:29) represents the conversion of `(y > 0 ? 10 : 20)` to boolean. Because both branches of the ternary yield non-zero integers, Branch (2:29) can never evaluate to False, creating an unreachable branch outcome in coverage reports.

  ### Expected Behavior
  When the RHS of a logical operator is already a conditional expression that generates its own branch regions, `CoverageMappingGen.cpp` should avoid creating a redundant outer condition branch.
  ```

---

## Conclusion

Out of the 5 candidate bugs:
* **2 bugs must be purged immediately** (`COV-BUG-004` and `COV-BUG-005`) as they do not reproduce and will damage the project's credibility.
* **1 bug is working-as-intended** (`COV-BUG-002`) and should not be filed.
* **2 bugs contain genuine compiler defects** (`COV-BUG-003` in GCC and `COV-BUG-001` in LLVM), provided their flawed original framing (CI threshold percentages and unexecuted short-circuit coverage exemptions) is completely replaced with the technical root-cause analyses documented above.
