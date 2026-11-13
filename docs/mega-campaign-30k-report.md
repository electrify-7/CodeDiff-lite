# Mega-Campaign Empirical Report: 30,000 Executions & SQLite Benchmark

## 1. Executive Summary

To rigorously establish the empirical foundations of compiler code coverage fidelity and cross-compiler divergence at research and industrial scale, we launched the **CovDiff-Lite Mega-Campaign**. Utilizing high-throughput parallel multiprocessing across 24 CPU cores, the campaign subjected **5,000 unique synthesized programs** across **4 complex construct families** to differential coverage profiling across **6 compiler/optimization tiers**:
* `GCC 11.4 -O0`
* `GCC 11.4 -Og`
* `GCC 11.4 -O2`
* `Clang / LLVM 14.0 -O0`
* `Clang / LLVM 14.0 -Og`
* `Clang / LLVM 14.0 -O2`

Simultaneously, the campaign benchmarked industrial-scale software by executing the differential pipeline on the **SQLite Amalgamation (`sqlite3.c`, 255,932 LOC)**, the world's most widely deployed database engine.

### Key Metrics
* **Total Differential Executions**: 30,000
* **Successful Executions**: 30,000 (100.0% pass rate; 0 crashes, 0 timeouts)
* **Execution Throughput**: 62.74 executions/sec
* **Total Execution Wall-Clock**: 478.13 seconds (~8 minutes)
* **Hardware Profile**: 24-core AMD/Intel Host, 32GB RAM, Linux 6.17 x86_64

---

## 2. Multi-Tier Optimization Gradient

A primary research question is how compiler optimization levels (`-O0`, `-Og`, `-O2`) degrade code coverage fidelity and alter executable line attribution.

| Compiler & Optimization Flag | Total Executions | Mapped Executable Lines | Covered Lines | Empirical Coverage Rate | Coverage Stability Delta |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **GCC 11.4 `-O0`** | 5,000 | 43,763 | 40,536 | 92.62% | Baseline |
| **GCC 11.4 `-Og`** | 5,000 | 39,332 | 38,720 | 98.44% | -4,431 lines (-10.12%) |
| **GCC 11.4 `-O2`** | 5,000 | 39,052 | 38,440 | 98.43% | -4,711 lines (-10.76%) |
| **LLVM-cov 14.0 `-O0`** | 5,000 | 59,550 | 52,071 | 87.44% | Baseline |
| **LLVM-cov 14.0 `-Og`** | 5,000 | 59,550 | 52,071 | 87.44% | 0 lines (0.00% drift) |
| **LLVM-cov 14.0 `-O2`** | 5,000 | 59,550 | 52,071 | 87.44% | 0 lines (0.00% drift) |

### Key Optimization Insights
1. **GCC CFG-Pruning Degradation**: As GCC optimizes code from `-O0` to `-Og` and `-O2`, basic blocks are aggressively combined, dead code is elided, and prologue/epilogue sequences are merged. Consequently, GCC's denominator shrinks by **4,711 lines (10.76%)**, artificially inflating its apparent coverage percentage from 92.62% to 98.43%.
2. **LLVM AST Source-Region Invariance**: In contrast, Clang/`llvm-cov` source-based code coverage operates directly on the Clang AST rather than the LLVM backend CFG. As a result, Clang maintains **100.0% structural denominator invariance** (59,550 executable lines) across `-O0`, `-Og`, and `-O2`.
3. **Ghost Line Vulnerability in GCC**: Optimization transformations in GCC (such as loop unrolling and block hoisting) introduce "ghost line" coverage counts where unexecuted loop guards or trailing statements receive non-zero hit counts.

---

## 3. Construct Family Breakdown

The 5,000 synthesized programs were systematically partitioned across four advanced grammar families:

| Grammar Construct Family | Executions | Success Rate | Primary Divergence Mechanism |
| :--- | :---: | :---: | :--- |
| **Statement Expressions `({ ... })`** | 10,926 | 100.0% | GCC gcov fails to attribute execution counts to internal statements within the block; Clang records distinct AST regions. |
| **VLA & Duff's Device Fall-Through** | 7,734 | 100.0% | Dynamic stack allocation and interleaved switch fall-through create cross-compiler block entry count mismatches. |
| **Non-Local Control (`setjmp`/`longjmp`)** | 5,994 | 100.0% | Non-local unwinding leaves CFG basic-block edges unresolved in GCC gcov arcs, whereas Clang marks regions up to the jump point. |
| **Complex Macros (Variadic & `##`)** | 5,346 | 100.0% | GCC aggregates all token execution onto the macro invocation line; Clang tracks individual macro expansion records. |
| **Total** | **30,000** | **100.0%** | Comprehensive cross-language coverage verification. |

---

## 4. SQLite Industrial Amalgamation Benchmark

To evaluate real-world industrial impact on safety-critical, high-assurance software, we profiled the complete SQLite Amalgamation:
* **Target File**: `sqlite3.c` (v3.45)
* **Total Source Lines**: 255,932 lines
* **Test Workload**: In-memory database initialization, schema creation, indexed insertion, and parameterized queries.

### Empirical Findings

```
================================================================================
              SQLITE AMALGAMATION DIFFERENTIAL COVERAGE PROFILE
================================================================================
Metric                                GCC 11.4 (gcov)       Clang 14 (llvm-cov)
--------------------------------------------------------------------------------
Executable Lines Mapped:               46,527                77,190  (+65.9%)
Covered Lines:                          8,980                16,502
Reported Coverage Percentage:          19.30%                21.38%
--------------------------------------------------------------------------------
Lines Covered by Both Tools:                                  8,771
Lines Uncovered by Both Tools:                               61,214
Lines Covered Exclusively by GCC:                               209
Lines Covered Exclusively by LLVM:                            7,731
Macro Divergence (Absolute Gap):                              2.08%
================================================================================
```

### CI/CD Quality Gate Conflict Analysis
In automated CI/CD pipelines where test suites must meet target coverage thresholds to pass, the 2.08% divergence causes severe false-alarm build failures:
* **Threshold @ 20.0%**: GCC reports **19.30% (FAIL / BLOCK CI)**, while Clang reports **21.38% (PASS)**.
* **Threshold @ 21.0%**: GCC reports **19.30% (FAIL / BLOCK CI)**, while Clang reports **21.38% (PASS)**.

Developers migrating CI runners from GCC to Clang or vice versa will observe arbitrary gate flips without any change to the underlying test suite or production codebase.

---

## 5. Artifact Reference & Reproducibility

All campaign data, JSON telemetry, and execution traces are permanently recorded in the project repository:
* **Full Campaign Telemetry**: [campaign_30k_final_report.json](file:///home/mahoraga/Software/CodeDiff-lite/runs/campaign_30k/campaign_30k_final_report.json)
* **Extended Real-World Summary**: [extended_realworld_summary.json](file:///home/mahoraga/Software/CodeDiff-lite/runs/extended_realworld/extended_realworld_summary.json)
* **Compiler Matrix Dossiers**: [matrix_summary.json](file:///home/mahoraga/Software/CodeDiff-lite/runs/phase5_matrix/compiler_matrix/matrix_summary.json)
* **Academic Paper LaTeX Tables**:
  * [optimization_matrix.tex](file:///home/mahoraga/Software/CodeDiff-lite/docs/paper/tables/optimization_matrix.tex)
  * [realworld.tex](file:///home/mahoraga/Software/CodeDiff-lite/docs/paper/tables/realworld.tex)
