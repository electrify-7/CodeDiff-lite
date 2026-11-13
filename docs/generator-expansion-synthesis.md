# Generator Expansion & Scaled Program Synthesis (5,000+ Cases)

## 1. Overview & Research Goal

A frequent reviewer criticism of differential testing studies is reliance on small or overly uniform synthetic datasets. To transition CovDiff-Lite from a 320-program course prototype into an industrial-scale empirical study suitable for top SE venues (ICSE/ISSTA/ASE), we expanded the C grammar synthesizer across two axes:
1. **Modern and Complex C Language Constructs**: Testing preprocessor, GCC/Clang language extensions, non-local jumps, and complex loop structures.
2. **Corpus Scale**: Expanding synthesis capacity from 320 to **5,000+ unique, deterministic test programs** with verified semantic outputs and zero hash collisions.

---

## 2. Expanded Construct Families

Implemented in [`src/covdiff_lite/synthesis.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/synthesis.py):

### 2.1 `complex_macros`
Tests preprocessor interactions that traditionally distort compiler debug info:
* **Variadic macros (`__VA_ARGS__`)**: Macro definitions accepting variable arguments.
* **Token concatenation (`##`)**: Identifier pasting (`target##_val`).
* **Multi-line macros with internal control flow**: Compound statements containing internal loops and local variables.

### 2.2 `statement_expressions`
Tests GCC and Clang language extensions:
* **Statement Expressions (`({ ... })`)**: Compound blocks enclosed in parentheses that evaluate to a final expression value.
* **Function Attributes**:
  * `__attribute__((always_inline))`: Forcing aggressive inlining.
  * `__attribute__((cold))`: Annotating unreached error branches.

### 2.3 `non_local_control`
Tests abnormal stack unwinding and non-linear control jumps:
* **`setjmp` / `longjmp`**: Stack context preservation and non-local jumping.
* **Computed `goto` (`goto *labels[idx]`)**: Indirect branching through pointer arrays.

### 2.4 `vla_and_duff`
Tests runtime stack allocations and interleaved loop structures:
* **Variable-Length Arrays (VLAs)**: Dynamic array allocation based on runtime integers.
* **Duff's Device**: Interleaved `switch` cases inside a `do-while` loop for manual unrolling.

---

## 3. Scalable Synthesis Performance

* The function `generate_large_scale_corpus(target_count=5000)` executes parameter grids and deterministic variations.
* Verified by [`tests/test_synthesis.py`](file:///home/mahoraga/Software/CodeDiff-lite/tests/test_synthesis.py), ensuring 100% unique SHA-256 program identities with validated execution expectations.
