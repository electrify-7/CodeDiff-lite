# Compiler Optimization Inaccuracies & Coverage Degradation

## 1. Overview & Research Problem

While software testing in developer development loops frequently occurs at `-O0`, production binaries, benchmarks, and safety-critical deployments often require optimized builds (`-O1`, `-O2`, `-Os`, or `-Og`). 

Compilers perform complex AST and CFG transformations during optimization:
* **Dead-code elimination (DCE)**: Pruning branches or statements statically proven unreachable.
* **Function inlining**: Cloning function bodies into call sites, altering line table mappings.
* **Loop unrolling & vectorization**: Grouping loop iterations, altering execution counter frequencies.
* **Instruction scheduling**: Interleaving instructions from adjacent source lines.

When source-based coverage tools measure optimized code, these transformations cause severe coverage distortions:
1. **Ghost Lines**: Unexecuted code falsely marked as executed (`expected == 0`, but reported `count > 0`).
2. **Dropped Lines**: Actually executed code reported as unexecuted or unmapped.
3. **Counter Distortion**: Altered execution counts from loop unrolling.

---

## 2. Invariant Optimization Oracle

CovDiff-Lite evaluates optimization accuracy using an **Optimization-Invariant Oracle**:
* Ground-truth execution counts are derived independently from the program model.
* The test case is executed across the standard optimization tiers:
  * **`-O0`**: Baseline, unoptimized.
  * **`-Og`**: Optimized for debugging (retains debug info and line fidelity where possible).
  * **`-O1`**: Basic optimizations.
  * **`-O2`**: Standard production optimizations (aggressive inlining, scheduling).
  * **`-Os`**: Code-size optimizations.

### 2.1 Metrics Formulated
* **Fidelity Score ($F_{\text{opt}}$)**:
  $$F_{\text{opt}} = \frac{N_{\text{matching statements}}}{N_{\text{total scored statements}}} \times 100\%$$
* **Ghost Rate ($G_{\text{opt}}$)**:
  $$G_{\text{opt}} = \frac{N_{\text{unexecuted statements with count} > 0}}{N_{\text{unexecuted statements}}}$$
* **Dropped Rate ($D_{\text{opt}}$)**:
  $$D_{\text{opt}} = \frac{N_{\text{executed statements with count} == 0 \text{ or unmapped}}}{N_{\text{executed statements}}}$$

---

## 3. Implementation

The multi-optimization pipeline is implemented in:
* [`src/covdiff_lite/optimization.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/optimization.py): Implements `evaluate_statement_degradation()` and `run_optimization_sweep()`.
* [`src/covdiff_lite/runners/gcc.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/runners/gcc.py): Parametrized `opt_level` support for compilation and linking.
* [`src/covdiff_lite/runners/llvm.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/runners/llvm.py): Parametrized `opt_level` support for Clang source coverage compilation.
* [`tests/test_optimization.py`](file:///home/mahoraga/Software/CodeDiff-lite/tests/test_optimization.py): Unit tests verifying ghost line and dropped line detection.
