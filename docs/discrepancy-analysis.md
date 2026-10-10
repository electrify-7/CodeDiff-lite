# Discrepancy analysis

Implemented on 2026-10-10, after the generator/oracle commit.

```bash
bash scripts/env.sh analyze --fixtures fixtures/calibration --output runs/analysis-calibration-new
bash scripts/env.sh analyze --fixtures runs/generator-pilot/cases --output runs/pilot-analysis
```

Each output directory must be new. Generated manifests are reconstructed and checked against independently compiled GCC and Clang trace twins before trusting their oracle. Functional output, stage failures, raw reports, LLVM display cross-checks, and exact command logs are retained.

The analyzer compares both tools independently to every explicitly scored oracle location, including cases where the tools agree with each other but are wrong. Missing observations remain null. It records binary and exact-count disagreements separately from missing mappings. All source lines remain visible; only annotated, mutually reported locations enter the comparable-line denominator.

Every case with a discrepancy or pipeline failure receives two additional executions, each with fresh builds and profiles. A deterministic 10% sample of otherwise agreeing cases is also repeated. Semantic signatures include normalized coverage, branch metadata, functional outputs, and failure stages, excluding paths and timing. A changing signature is unstable; a stable execution failure is a pipeline failure. A trusted count contradiction becomes a probable incorrect report only after three matching runs. Stable uncertain mappings remain unresolved. Both retain pending manual review.

Convention rules are restricted to GCC/gcov 11.4.0 and Clang/LLVM 14.0.0. They cover unscored braces, selected macro definitions, generated unscored switch-label mappings, generated multiline continuations, and explicitly elidable unreachable constant bodies. A rule cannot dismiss a reported contradiction on a scored statement. These are operational mapping rules, not claims that every macro or label disagreement is harmless. See the [GCC line reporting documentation](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/Invoking-Gcov.html) and [LLVM 14 coverage documentation](https://releases.llvm.org/14.0.0/tools/clang/docs/SourceBasedCodeCoverage.html).

Outputs include `summary.json`, `results.jsonl`, `cases.csv`, `observations.csv`, per-case and per-repeat analyses, frozen source/manifests, and per-case `reproduce.sh`. Run reproduction scripts from the repository root and pass a new output directory. The environment records a digest of the Python implementation as well as the container/tool identities. Analysis exits nonzero for pipeline failures or unstable observations; research findings themselves are recorded without aborting the batch.

## Validation

All 48 tests passed in the pinned image, including real-tool integration checks and fresh-directory confirmations. A synthetic report mutation verifies the probable-error classification; it is a framework test and is excluded from research findings.

An initial analysis of the 16 handwritten calibration fixtures produced 16 valid cases, 63 comparable locations, and no scored oracle contradictions. Twelve cases had explained mapping differences; four retained unresolved constant-condition or multiline mappings. All received three clean runs, totaling 48 paired coverage collections. This illustrates why successful calibration on selected statements does not imply agreement on every source line.

Semantic branch alignment and HTML visualization remain unimplemented. Raw branch data are retained, and comparable branch outcomes are explicitly zero.
