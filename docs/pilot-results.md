# Step 4: 40-program pilot

Completed on 2026-10-10 in the pinned Docker image. The main coverage experiment has **not** been run. The pilot used five unique deterministic programs in each of eight families, seed `20261009`, generator/template version 1, convention rules version 1, and sequential execution.

```bash
bash scripts/env.sh experiment --config configs/pilot.json --output runs/pilot-new
```

This command generates the corpus, validates both compilers' independent execution traces, collects and normalizes both coverage reports, checks the oracle, repeats findings, and writes JSON/CSV evidence and resource measurements. Output must be new. HTML reporting remains a later stage.

## Results

| Metric | Result |
| --- | ---: |
| Generated, unique programs | 40 |
| Successful dual-compiler oracle trace checks | 40/40 |
| Successful first-pass coverage pipelines and expected outputs | 40/40 |
| Comparable annotated statement locations | 263 |
| Contradictions of scored statement counts | 0 |
| Raw tool count disagreements | 4 |
| Raw binary disagreements, included in the previous row | 4 |
| Missing/present mapping differences | 136 |
| Observations explained by scoped convention rules | 134 |
| Cases classified as known convention differences | 34 |
| Cases classified as unresolved disagreements | 6 |
| Probable incorrect reports in generated pilot | 0 |
| Pipeline failures or unstable cases | 0 |
| Paired coverage collections, including repeats | 120 |

Raw counts cover all source lines; comparable counts cover explicitly scored, mutually reported statements. These denominators differ. There are 591 total source lines: 263 comparable locations, 323 unscored locations, and five annotated unreachable constant statements lacking a GCC mapping. Missing mappings are not treated as zero.

All 40 cases had at least a mapping/convention observation, so all received three clean paired collections. All signatures were stable. No otherwise-agreeing cases were eligible for the additional 10% control sample; this does not reduce confirmation coverage. The 120 paired collections mean 240 instrumented executions. Oracle validation adds 80 separate executions without coverage.

| Family | Programs | Comparable statements | Known-convention cases | Unresolved cases |
| --- | ---: | ---: | ---: | ---: |
| Constants | 5 | 20 | 0 | 5 |
| If/else | 5 | 33 | 5 | 0 |
| Loops | 5 | 35 | 4 | 1 |
| Macros | 5 | 45 | 5 | 0 |
| Multiline | 5 | 35 | 5 | 0 |
| Short circuit | 5 | 35 | 5 | 0 |
| Switch | 5 | 35 | 5 | 0 |
| Ternary | 5 | 25 | 5 | 0 |
| **Total** | **40** | **263** | **34** | **6** |

The four binary disagreements occur on unscored multiline condition continuations. Their mapping rule preserves each tool's line attribution without inventing a statement-count oracle. The six unresolved cases were inspected: five concern constant `if` headers and one a `do` header. Gcov omits these header lines while LLVM reports a count. The surrounding scored statements and functional outputs are correct. Their ambiguous header semantics remain unresolved; the rules were not broadened to force agreement. See [the review worksheet](evidence/pilot-review.json).

## Time and resources

| Measurement | Observed |
| --- | ---: |
| End-to-end generation and analysis | 15.85 s |
| Analysis, including oracle validation and repeats | 15.79 s |
| Median first paired coverage pass per case | 0.104 s |
| Mean first paired coverage pass per case | 0.108 s |
| 95th percentile first pass | 0.139 s |
| Total confirmation-pass time | 8.52 s |
| Maximum individual child RSS | 88,480 KiB |
| Container cgroup peak memory | 85,991,424 bytes |
| Logical artifact size before final experiment summary | 20,872,271 bytes |
| Allocated artifact size before final experiment summary | 30,076,928 bytes |
| Artifact files before final summary | 4,850 |

The container had a 4 GiB memory limit and a four-CPU quota; cases ran sequentially. RSS is the maximum for an individual child, not aggregate pipeline memory. Cgroup peak is a separate kernel accounting measure including container activity. Measurements exclude image build/startup and the final experiment-summary write. Host one-minute load was about 1.49 at start and 1.38 at end. Timing is a single-machine pilot measurement.

A simple eightfold projection for 320 programs is about 2.1 minutes and 230 MiB allocated artifacts under similar conditions, including three passes per case. This is a planning estimate, not a main-experiment result. Keep one worker for the main run: the observed cost does not justify adding parallel execution now. The 5 GiB artifact budget is ample for this projection.

## Frozen configuration and tomorrow's work

[configs/main.json](../configs/main.json) specifies 320 cases, 40 per family, seed `20261010`, a 10% agreeing-case control fraction, and one worker. Generator/template version 1, manifest schema 1, and convention-rule version 1 are frozen for the planned run. Semantic branch comparison remains deferred; comparable branch outcomes are zero. Automatic reduction remains optional.

Run tomorrow, after deciding to start the main experiment:

```bash
bash scripts/env.sh experiment --config configs/main.json --output runs/main
```

The main candidate corpus was previously checked through noncoverage oracle traces only. The command above regenerates it deterministically and performs the actual main coverage experiment. Pilot and documented-issue fixtures remain separate datasets. The generator's parameter grids are intentionally finite; success on these templates cannot establish reliability for arbitrary C programs.

All 55 framework tests passed in Docker with no skips before the measured pilot. No parser or oracle correction was required by the pilot. Remaining core work is the main experiment, offline HTML report, empirical tables/figures, and a clean demonstration with one ordinary example and one documented discrepancy. Paired layout controls remain planned; branch alignment and reduction are stretch goals.

## Saved evidence

- [Compact summary and environment/resource provenance](evidence/pilot-summary.json)
- [Per-case CSV](evidence/pilot-cases.csv)
- [Manual mapping review](evidence/pilot-review.json)

Full source/manifests, raw JSON, profiles, execution logs, normalized observations, repeat signatures, and reproduction scripts remain in `runs/pilot/`. These artifacts are ignored by Git but can be recreated with the pilot command. Dataset SHA-256: `008320ade7de1af0d2b635137d15628bba155faff67f345d481bf65fcdf54e03`, matching the earlier generator-stage pilot corpus.
