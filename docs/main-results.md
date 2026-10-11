# Main coverage experiment: E3 and E4

Completed on 2026-10-11 using committed implementation `c2842c5`, the unchanged pinned image, and [configs/main.json](../configs/main.json). The Git working tree was clean before execution. Generator/template version 1, manifest schema 1, convention-rule version 1, seed `20261010`, and sequential execution were retained from the pilot.

```bash
bash scripts/env.sh experiment --config configs/main.json --output runs/main-new
```

## Results and denominators

| Metric | Result |
| --- | ---: |
| Generated programs / unique source hashes | 320 / 320 |
| Programs per construct family | 40 |
| Successful GCC and Clang oracle trace checks | 320/320 |
| Successful first-pass paired coverage pipelines | 320/320 |
| Annotated statement locations | 2,141 |
| Mutually reported, comparable statement locations | 2,101 |
| Reported annotated locations: gcov / llvm-cov | 2,101 / 2,141 |
| Oracle contradictions: gcov / llvm-cov | 0 / 0 |
| Raw count disagreements, also binary disagreements | 25 |
| Missing/present mapping differences | 1,095 |
| Convention-explained observations | 1,051 |
| Cases with known convention differences | 264 |
| Cases with unresolved disagreements | 56 |
| Probable incorrect reports in the main dataset | 0 |
| Pipeline failures / unstable cases | 0 / 0 |
| Paired coverage collections, including repeats | 960 |

All 320 generated sources are unique within this dataset. Main results, pilot results, documented issues, and forthcoming layout controls are separate experiments. The main dataset contains 4,719 source lines: 2,101 comparable locations, 2,578 unscored source locations, and 40 explicitly unreachable constant-body statements lacking a GCC mapping. Absence is retained as null, not zero. Both tools match the oracle at every annotated location they report.

Every case had at least one source-mapping or convention finding, so every case received three fresh builds/profiles and all were stable. There were no otherwise-agreeing cases eligible for the additional 10% control sample. E4 therefore confirms all 320 cases, rather than only a subset. There were 1,920 instrumented executions and 640 additional noncoverage oracle-trace executions. All compilation, linking, execution, profile extraction/merging, and report commands succeeded; all instrumented outputs matched the manifests. LLVM normalization/display cross-checks passed throughout.

| Family | Cases | Comparable statements | Known-convention cases | Unresolved cases |
| --- | ---: | ---: | ---: | ---: |
| Constants | 40 | 160 | 0 | 40 |
| If/else | 40 | 261 | 40 | 0 |
| Loops | 40 | 280 | 24 | 16 |
| Macros | 40 | 360 | 40 | 0 |
| Multiline | 40 | 280 | 40 | 0 |
| Short circuit | 40 | 280 | 40 | 0 |
| Switch | 40 | 280 | 40 | 0 |
| Ternary | 40 | 200 | 40 | 0 |
| **Total** | **320** | **2,101** | **264** | **56** |

The 25 raw binary differences are on unscored multiline continuation lines. Known-rule observations comprise 866 brace attributions, 40 unreachable-body elisions, 40 statement-macro definition mappings, and 105 multiline continuation attributions. These are observation counts, not independent bugs or case counts.

The 56 unresolved cases contain 69 unresolved observations: 40 constant-condition headers, 13 `FLAG` macro-definition lines, and 16 `do` headers. Gcov omits these locations while LLVM reports a count. They remain unresolved under the frozen rules; their stability alone does not establish an incorrect report. Detailed review and separately run paired layout controls were subsequently completed; see [findings review](findings-review.md) and [layout controls](layout-controls.md). This frozen result snapshot is unchanged.

## Time and resources

The complete experiment took 130.66 seconds; analysis including trace checks and confirmations took 130.43 seconds. Mean first-pass paired collection time was 0.112 seconds, median 0.105 seconds, and p95 0.148 seconds. Confirmation passes totaled 70.92 seconds.

The container retained its four-CPU quota and 4 GiB memory limit while cases ran sequentially. Cgroup peak memory was 425,414,656 bytes; maximum individual child RSS was 88,480 KiB. These are separate kernel accounting measures. Artifacts before the final summary occupied 166,837,259 logical bytes and 240,574,464 allocated bytes across 38,730 files. Host one-minute load was about 0.46 at start and 1.54 at end. Timing excludes image build/startup and is a single local measurement.

No source, oracle, parser, or classifier correction was made during the experiment. The previous 55-test Docker validation applies to this unchanged implementation. The results do not establish reliability for arbitrary C programs: the sample uses finite templates, one version pair, and `-O0`. Semantic branch alignment and reduction remain deferred. The two documented bugs were reproduced separately; they are not counted as main-dataset findings.

## Reproducibility

The dataset SHA-256 is `7527bb52203bbf2309d75cf57b4375e303542b226fb5621ee7a39d7bfce74144`, matching the earlier noncoverage candidate corpus. Image identity, implementation digest, exact tool versions, resource measurements, family denominators, and successful command-stage totals are tracked in [evidence/main-summary.json](evidence/main-summary.json). [Per-case CSV](evidence/main-cases.csv) and [the dataset index/source hashes](evidence/main-dataset.json) are also tracked.

Full raw reports, source/manifests, profiles, command logs, normalized observations, and three-run signatures remain under `runs/main/`, which is ignored by Git. Recreate them with the command above. Each saved case has a reproduction script accepting a new output directory.
