# Real-World Open-Source Evaluation & CI/CD Coverage Divergence

## 1. Overview & Research Goal

A fundamental research question in coverage validation is: **"Does compiler coverage discrepancy matter in real-world production software?"**

Software engineering workflows rely heavily on CI/CD code coverage gates (e.g., Codecov, Coveralls, GitHub Actions). Pull requests are automatically blocked if line coverage falls below a specified threshold (e.g., 80% or 90%). 

However, open-source repositories often build on heterogeneous CI runners (e.g., Ubuntu runners using GCC vs macOS runners using Apple Clang). If GCC and Clang disagree on which lines count or are covered, developers encounter **flaky or conflicting CI gating**.

---

## 2. Methodology & Metrics

Implemented in [`src/covdiff_lite/realworld.py`](file:///home/mahoraga/Software/CodeDiff-lite/src/covdiff_lite/realworld.py):

### 2.1 Macro-Level Metric Divergence
Measures the overall repository-level delta in reported line coverage:
$$\Delta_{\text{macro}} = |\text{Coverage}_{\text{GCC}}\% - \text{Coverage}_{\text{LLVM}}\%|$$

### 2.2 Micro-Level Asymmetric Attribution
Categorizes specific source lines into mutually exclusive sets:
* **$L_{\text{both}}$**: Lines marked covered by both tools.
* **$L_{\text{gcc\_only}}$**: Lines marked covered by GCC (`count > 0`), but marked uncovered (`count == 0`) or unmapped (`null`) by Clang.
* **$L_{\text{llvm\_only}}$**: Lines marked covered by Clang (`count > 0`), but marked uncovered (`count == 0`) or unmapped (`null`) by GCC.
* **$L_{\text{neither}}$**: Lines marked uncovered by both tools.

### 2.3 CI/CD Gate Conflict Rate
Given a threshold $\tau \in \{70\%, 75\%, 80\%, 85\%, 90\%\}$:
$$\text{GateConflict}(\tau) = (\text{Coverage}_{\text{GCC}} \ge \tau) \oplus (\text{Coverage}_{\text{LLVM}} \ge \tau)$$
Quantifies whether the same test suite passes on GCC CI but is rejected on Clang CI.

---

## 3. Evaluation & Verification

* Tested on canonical open-source C structures (SQLite, Lua, zlib).
* Verified by [`tests/test_realworld.py`](file:///home/mahoraga/Software/CodeDiff-lite/tests/test_realworld.py), demonstrating precise quantification of macro divergence, micro asymmetric line sets, and CI gate flip rates.
