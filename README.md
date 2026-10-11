# CovDiff-Lite

Oracle-guided comparison of GCC/gcov and Clang/llvm-cov coverage for deterministic C programs. The proposal is in [project.md](project.md), and the full development plan is in [plan.md](plan.md).

The core project is implemented: deterministic generation/oracles, both coverage pipelines, discrepancy analysis, repeatability, documented issues, layout controls, empirical figures and offline reporting. The measured environment provides GCC/gcov 11.4.0, Clang/LLVM 14.0.0 and Python 3.10.12. Coverage-only commands use the Python standard library; publication uses pinned Matplotlib 3.5.1 in the separate reporting image. Runs require no downloads.

## Final one-command workflow

After the one-time image builds:

```bash
bash scripts/env.sh pipeline --config configs/main.json --output runs/final-main-new
```

For a smaller end-to-end run, use `configs/demo.json` (48 programs). Open the resulting `report/index.html`; it includes source comparisons and the empirical analysis. The existing frozen 320-case results are already published in [the empirical report](docs/empirical-analysis.md), [tables and figures](docs/results/index.html), and [the integrated local dashboard](runs/final-report/index.html). The original main experiment was preserved.

See [setup, output layout, demonstration and exit statuses](docs/final-pipeline.md).

## Run individual checks

Run from this repository with working Docker daemon access:

```bash
bash scripts/env.sh build
bash scripts/env.sh build-reporting
bash scripts/env.sh doctor --output runs/environment.json
bash scripts/env.sh calibrate --fixtures fixtures/smoke --output runs/smoke
bash scripts/env.sh calibrate --output runs/calibration
bash scripts/env.sh test
```

Every calibration output directory must be new. Use a different name for a subsequent run; this prevents stale `.gcda` or `.profraw` data from accumulating. The wrapper runs without network access, as your user, with four CPUs and a 4 GiB memory limit. Building the image requires internet access. Override the image tag using `COVDIFF_IMAGE` if needed.

The suite contains 16 handwritten fixtures: two each for if/else, loops, switch, short-circuit expressions, multiline conditions, ternary expressions, macros, and constant conditions. A separate smoke fixture checks the basic pipeline. Fixture manifests specify expected stdout, exit status, selected statement counts, source hashes, and oracle rationales.

For each fixture the command builds and runs both instrumented programs, checks output against the manifest, retains raw JSON and command evidence, normalizes line coverage, and checks selected statement counts. LLVM normalization is also checked against `llvm-cov show`; its file summary is checked when there are no macro expansions. An oracle mismatch is calibration evidence requiring investigation, not a confirmed tool bug.

## Inspect the evidence

```text
runs/calibration/
  environment.json        # image identity, tool versions, package inventory
  config.json             # suite, selected cases, start time
  summary.json            # totals and per-case statuses
  results.jsonl
  cases/<case-id>/
    case.c
    manifest.json
    normalized.json       # both normalized reports and oracle comparison
    result.json
    gcov/                 # binary, object, profiles, gzip JSON, commands/logs
    llvm-cov/             # binary, profiles, JSON, display, commands/logs
```

Absent observations retain `count: null`, rather than becoming zero. Literal constant bodies explicitly allow a missing mapping when unreachable; those locations are excluded from comparable-line totals. Gcov partial-block and branch data, and LLVM branches and macro expansions, are retained. Semantic branch alignment is deferred.

The CLI returns 0 when every fixture passes, 1 for fixture/pipeline failures, and 2 for invalid configuration or setup. It continues collecting other cases and the other tool after a case-stage failure. Each command has a timeout; failed stages preserve stdout, stderr, arguments and exit codes.

## Environment reproducibility

[Dockerfile](Dockerfile) pins the linux/amd64 Ubuntu image by manifest digest and reads packages from the Ubuntu archive snapshot `20261001T000000Z`. Direct compiler, LLVM and Python package versions are pinned; snapshot resolution freezes dependencies. A checksum-verified CA package bootstraps HTTPS access. The image retains a complete package inventory in `/opt/covdiff/packages.tsv`.

Record the actual built image ID using `doctor` and retain an image export if long-term archival is needed. Snapshot availability is an external service dependency; the recipe intentionally fails rather than falling back to changing package versions. See the [Ubuntu Snapshot Service](https://snapshot.ubuntu.com/) for archive retention and behaviour.

Native debugging is available with the matching tools installed:

```bash
PYTHONPATH=src python3 -m covdiff_lite doctor
PYTHONPATH=src python3 -m covdiff_lite calibrate --output runs/native-calibration
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Native runs are labelled separately. Tool paths can be set through `COVDIFF_GCC`, `COVDIFF_GCOV`, `COVDIFF_CLANG`, `COVDIFF_LLVM_COV`, and `COVDIFF_LLVM_PROFDATA`. Integration tests skip if the matched tools are unavailable; use the Docker test command for complete validation.

## Current boundary

Generate and validate a 40-case pilot corpus:

```bash
bash scripts/env.sh generate --per-family 5 --seed 20261009 --output runs/generated-pilot
bash scripts/env.sh validate-oracle --fixtures runs/generated-pilot/cases --output runs/pilot-traces
bash scripts/env.sh calibrate --fixtures runs/generated-pilot/cases --output runs/pilot-coverage
```

Generation itself requires only Python; `PYTHONPATH=src python3 -m covdiff_lite generate ...` works without Docker. The default is 40 cases per family (320 total), but generating a corpus does not execute a coverage experiment. Every output directory must be new. See [docs/generator-oracle.md](docs/generator-oracle.md) for the reviewed subset, semantic oracle and validation boundaries.

Discrepancy classification, clean repeats, documented issue reproduction, the main experiment, and paired layout controls are complete. The offline dashboard, final empirical analysis/figures and one-command workflow are complete. A separate 48-case demonstration/validation run passes. Semantic branch comparison and reduction remain outside the implemented core. Original measured results are in [docs/step12-results.md](docs/step12-results.md), and fixture semantics are described in [fixtures/README.md](fixtures/README.md).

## Analyze discrepancies

```bash
bash scripts/env.sh analyze --fixtures fixtures/calibration --output runs/analysis-calibration-new
bash scripts/env.sh analyze --case runs/analysis-calibration-new/cases/if_true/manifest.json --output runs/replay
```

Use the actual saved case ID for single-case replay. Every finding receives three clean runs. Results distinguish known mappings, unresolved differences, stable oracle contradictions, instability, and pipeline failure. See [the analysis contract and validation](docs/discrepancy-analysis.md). JSON/CSV evidence and the offline HTML dashboard are available.

## Reproduce documented problems

```bash
bash scripts/env.sh reproduce-issues --output runs/documented-issues-new
```

Two documented patterns reproduce in the pinned image, with a never-executed variant and a corrective control. See [step 3 findings and provenance](docs/documented-issues.md).

## Run a configured experiment

```bash
bash scripts/env.sh experiment --config configs/pilot.json --output runs/pilot-new
```

The 40-program pilot passed all execution and oracle checks: 263 comparable statements, no oracle contradictions, 34 cases with explained mappings and six with unresolved header mappings. All 40 were stable across three runs. See [pilot results and measurements](docs/pilot-results.md).

The 320-program main coverage experiment is complete: all programs passed, 2,101 comparable statements matched their oracles, and all repeated results were stable. See [main results](docs/main-results.md). All main findings have been reviewed, and 16 paired layout controls preserve statement counts while exposing layout-dependent mappings. See [findings review](docs/findings-review.md) and [layout controls](docs/layout-controls.md). Generation, validation, coverage collection, normalization, analysis, and CSV/JSON exports are available in one command. Offline HTML reporting is implemented, including automatic reports for future experiments. All 79 tests pass in the pinned reporting image.

## Audit findings and run layout controls

```bash
bash scripts/env.sh review --analysis runs/main/analysis --output runs/main-reviewed-new.json
bash scripts/env.sh layout-controls --dataset runs/main/dataset --output runs/layout-controls-new
```

The audit checks saved raw evidence and preserves original classifications. Layout controls compare 16 semantic pairs (32 programs) with identical C tokens and behavior but different brace placement. All 16 pairs pass statement-count checks; all change mapping totals. Output paths must be new. The empirical analysis and complete pipeline are available in [the final workflow guide](docs/final-pipeline.md).

## Open the offline dashboard

Open [`runs/final-report/index.html`](runs/final-report/index.html) in a browser. No server or internet connection is required. It contains separate views for the 320-program main experiment, four documented-issue fixtures, and 16 layout pairs, with source/count comparisons, filters, review status, repeat history, raw evidence, and reproduction commands. Keep the entire report folder together when sharing it.

Future `experiment` runs automatically create empirical tables/figures and `report/index.html`. The `pipeline` command additionally runs documented issues, layout controls and evidence audits. To build a report from any saved analysis without rerunning coverage:

```bash
PYTHONPATH=src python3 -m covdiff_lite report --analysis runs/main/analysis \
  --review docs/evidence/main-review.json --output runs/main-report-new
```

See [offline report instructions and validation](docs/offline-dashboard.md) for the combined three-dataset command and interpretation of missing, unscored, and contradictory observations.

Done by : Prateek Butolia, Durgesh Shelke, Parth Aher
