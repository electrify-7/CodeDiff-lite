# Final one-command pipeline

The complete workflow runs generation, independent trace-oracle validation, GCC/gcov and Clang/LLVM collection, normalization, classification and clean repeats, two documented problem patterns, 16 paired layout controls, raw-evidence reviews, empirical tables/figures, and an offline HTML dashboard.

## Build once

```bash
bash scripts/env.sh build
bash scripts/env.sh build-reporting
```

The original `covdiff-lite:testing` compiler image is retained. `Dockerfile.reporting` extends it with `python3-matplotlib=3.5.1-2build1` from the same fixed Ubuntu snapshot and records the updated package inventory. Building needs network access; execution uses `--network none`, four CPUs, 4 GiB and the invoking user's UID/GID.

The wrapper selects `covdiff-lite:reporting` for `pipeline`, `experiment`, `empirical`, `plots` and the full test suite. Coverage-only commands continue to default to `covdiff-lite:testing`. `COVDIFF_IMAGE` overrides this selection; an overridden image must include Matplotlib when plotting is requested. Native plotting needs the `figures` optional dependency (`pip install '.[figures]'`); coverage-only commands and the basic dashboard use the Python standard library.

## Run everything with one command

```bash
bash scripts/env.sh pipeline --config configs/main.json --output runs/final-main-new
```

This performs a **new** 320-program experiment. It does not overwrite `runs/main`, which remains the frozen study. The output directory must not already exist.

```text
runs/final-main-new/
  pipeline.json                 # completion/check status, errors and stage wall times
  experiment/
    dataset/                    # deterministic corpus and manifests
    analysis/                   # raw and normalized reports, repeats, CSV and logs
    experiment.json             # primary measurement/resource scope
  documented-issues/            # separate positive fixtures and corrective control
  layout-controls/              # separate 16 semantic pairs, traces and results
  reviews/primary.json
  reviews/layout.json
  empirical/
    index.html                  # readable analysis, tables and figures
    analysis.md
    metrics.json                # denominators, timings, provenance and evidence digests
    publication.json            # artifact checksums
    tables/
    figures/                    # four figures, each as SVG and PNG
  report/index.html             # dashboard; all three datasets remain separate
  report/empirical/index.html    # portable bundled analysis and figures
```

Open `report/index.html` directly in a browser. **Empirical analysis** links to the bundled tables/figures; its dashboard link returns to the source comparison. Keep the report folder together when sharing. Instrumented binaries/profiles remain in the full run archive; the portable report retains source, manifests, raw reports, commands and logs.

`experiment` remains the smaller single-dataset interface and now automatically creates both `empirical/` and `report/`. `pipeline` adds the issue fixtures, layout controls and reviews without generating duplicate intermediate dashboards.

## Short validation and demonstration

```bash
bash scripts/env.sh pipeline --config configs/demo.json --output runs/final-demo-new
```

The demo config uses 48 generated programs, six per family, with the same seed as the main experiment. It contains the contrasting cases and true constant-macro case needed by the layout-control selection. The original 40-case pilot config lacks that macro case and is refused by the full pipeline before creating output; it remains valid for `experiment`.

The completed validation run is retained separately under `runs/final-validation`. It passed all seven pipeline stages, reproduced two documented patterns, and passed 16 layout pairs. It is framework validation, not another main empirical dataset.

For the demonstration:

1. Open `runs/final-validation/report/index.html`, choose the primary dataset and search for `if_else_v1_2e5ae00ba7a0a231`. Its scored statements agree with the oracle; unscored brace conventions remain visibly labelled. This is the ordinary statement-agreement example, even though the full case label is “known convention.”
2. Open **Documented issues**, select `llvm_140427_never`, and inspect line 14: expected `0`, gcov `0`, LLVM `2`. Check the expected/actual output, three repeat signatures and raw reports. The issue's origin stays separate from generated programs.
3. Select `llvm_140427_control` to see the documented following-statement symptom removed.
4. Open **Layout controls**, follow a parent/variant pair and inspect equal statement counts at relocated source lines.
5. Open **Empirical analysis** for the selected run's tables and figures. The frozen 320-program empirical analysis is separately available in `docs/results/index.html` and `runs/final-report/index.html`.
6. Copy the suspicious case's reproduction command and use a new output directory. A saved source/manifest can also be replayed directly:

```bash
bash scripts/env.sh analyze \
  --case runs/final-report/evidence/issues/cases/llvm_140427_never/manifest.json \
  --output runs/final-replay-new
```

## Rebuild publication from frozen results

The final frozen-study dashboard is `runs/final-report/index.html`. Its empirical artifacts are tracked under `docs/results`. To regenerate them, choose new directories and use the `empirical` and `report` commands:

```bash
bash scripts/env.sh empirical --analysis runs/main/analysis \
  --review docs/evidence/main-review.json \
  --documented-issues runs/documented-issues-verified \
  --layout-controls runs/layout-controls-verified \
  --layout-review docs/evidence/layout-controls-review.json \
  --output runs/final-empirical-new

bash scripts/env.sh report --analysis runs/main/analysis \
  --review docs/evidence/main-review.json \
  --documented-issues runs/documented-issues-verified \
  --layout-controls runs/layout-controls-verified \
  --layout-review docs/evidence/layout-controls-review.json \
  --empirical runs/final-empirical-new --output runs/final-report-new
```

Figures can be redrawn from retained plotting inputs without raw profiles or another compiler execution:

```bash
bash scripts/env.sh plots --tables docs/results/tables --output runs/redrawn-figures
```

## Status and failure handling

CLI exit `0` means collection/publication completed and the pipeline's execution, issue and pair checks passed. Exit `1` signals failed/unstable measurements, unconfirmed issue symptoms, failed layout checks or failed raw-evidence audits; ordinary known/unresolved coverage classifications do not themselves cause failure. Exit `2` signals invalid configuration, unsupported/corrupt input evidence or a fatal setup/publication error.

Cases requiring human inspection remain labelled and counted; a successful command does not certify a new bug or resolve an ambiguous mapping. Failed raw-evidence audits are recorded, review overlays are omitted for those suites, and publication is still attempted using saved pipeline classifications. Fatal stage failures leave an incomplete `pipeline.json` and the collected evidence available for inspection. Existing output directories are never reused.

Primary elapsed/resource measurements stop before publication and exclude Docker startup/build. `pipeline.json` separately records stage wall times and total workflow time. Stage boundaries may include their own file-writing overhead; their sum need not equal total wall time exactly. In single-dataset `experiment` runs, `empirical_seconds` and `report_seconds` record publication costs separately.

Semantic branch alignment and automatic reduction remain outside the implemented core. The final empirical findings claim two reproduced documented patterns, not a newly discovered coverage bug.
