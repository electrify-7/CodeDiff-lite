# Modern Compiler Matrix & Upstream Bug Hunting

## 1. Overview & Research Goal

A major evaluation dimension for compiler empirical studies is tracking how coverage discrepancies evolve across major compiler releases:
* Do coverage discrepancies persist across multiple compiler generations?
* Did an upstream patch resolve a historical flaw, or did a newer optimization pass introduce a silent regression?

CovDiff-Lite implements multi-version toolchain evaluation across:
* **GCC Matrix**: GCC 11.4.0, GCC 12.3.0, GCC 13.2.0, GCC 14
* **Clang / LLVM Matrix**: LLVM 14.0.0, LLVM 16.0.0, LLVM 17.0.0, LLVM 18.1.0

---

## 2. Evolution Taxonomy

Implemented in [`src/covdiff_lite/matrix.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/matrix.py):
1. **`persistent_bug`**: The coverage discrepancy persists across all evaluated compiler versions.
2. **`upstream_fixed_in_modern`**: The flaw was present in older releases but resolved by compiler maintainers in modern toolchains.
3. **`regression_in_modern`**: Clean coverage reporting in older versions that degenerated into incorrect or dropped coverage in newer versions.

---

## 3. Automated Upstream Bug Dossiers

When an unexplainable contradiction against the ground-truth oracle is isolated and confirmed across 3 clean repeat executions, the framework:
1. Runs [`src/covdiff_lite/reduce.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/reduce.py) to extract a minimal 3-to-10 line C reproducer.
2. Formats a complete, ready-to-submit upstream bug dossier with version matrix specifications, expected versus actual counts, and an executable reproduction shell script.
