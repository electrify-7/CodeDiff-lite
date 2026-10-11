# Offline coverage dashboard

The final integrated dashboard is `runs/final-report/index.html`, with an **Empirical analysis** link to bundled tables and figures. The original dashboard-stage bundle remains at `runs/offline-dashboard/index.html`. Open either in a browser. The dashboard reads embedded JSON and local assets; it needs neither a server nor an internet connection. Keep the entire folder together when copying or archiving it, including `dashboard.css`, `dashboard.js`, and `evidence/`.

## Generate from saved measurements

From the repository root:

```bash
PYTHONPATH=src python3 -m covdiff_lite report \
  --analysis runs/main/analysis \
  --review docs/evidence/main-review.json \
  --documented-issues runs/documented-issues-verified \
  --layout-controls runs/layout-controls-verified \
  --layout-review docs/evidence/layout-controls-review.json \
  --output runs/offline-dashboard
```

The output directory must be new. To regenerate, choose a different output directory. Reporting requires only Python 3.10 or later; `bash scripts/env.sh report ...` also works inside the pinned Docker image. The command reads existing measurements and review overlays, validates their source hashes and saved observations, and copies portable evidence. It does not compile programs, rerun coverage, modify a convention rule, or reclassify a case. JSON schemas and original measurement implementation hashes remain visible.

The dashboard keeps three datasets separate:

| View | Scope | Findings |
| --- | --- | --- |
| Main experiment | 320 generated programs; 960 paired collections | 2,101 comparable lines; zero scored oracle contradictions; 264 convention cases and 56 reviewed, unresolved cases |
| Documented issues | Four fixtures, including a corrective control | Two documented patterns reproduced; three positive fixtures are not three independent bugs |
| Layout controls | 16 pairs / 32 programs; 96 paired collections | 107 semantic statement pairs preserved; source mapping differences remain visible |

## Explore a case

Filter by construct, classification, or findings involving a tool. Search matches case IDs, family names, and C source. Dataset metric cards always describe the whole selected dataset; the case counter describes the filtered list.

The source table displays every line, with exact expected and observed counts. `0` means reported and uncovered, **Not reported** means the tool did not map that line, and **Unavailable** means no usable report was collected for that tool. **Unscored** means the oracle assigns no universal statement count to that source location. Red rows identify scored contradictions, amber rows unresolved differences, purple rows matched convention rules, and green rows validated oracle agreement. Labels accompany every color.

Use **Findings only** to focus the table, or select a coverage collection to inspect that repeat's counts, findings, output, errors, signature, and raw evidence. The first-pass comparable-line total stays explicitly labelled. Case classification is the saved roll-up across repeats. A contradictory row in an unstable or failed case does not establish a stable tool error. Review overlays update the displayed review status while retaining the original classification.

Layout cases link both members of the pair and, where included, the original main case. Their statement table aligns semantic IDs across changed line numbers using recorded first-collection observations. Branch outcomes and raw branch counters are available under evidence, but semantic branch alignment is deferred and comparable outcomes remain zero.

Copy the reproduction command and run it from the repository root with Docker available. It uses the bundled manifest and source and requests a new analysis directory. Change the output directory for another repeat; update the manifest path if you move the dashboard. The copied original `reproduce.sh` is archival evidence and retains its original measurement path.

## Automatic reporting for future experiments

```bash
bash scripts/env.sh experiment --config configs/pilot.json --output runs/pilot-with-html
```

This single command now generates programs, validates oracles, collects and normalizes coverage, classifies and repeats cases, generates empirical tables/figures, then creates `runs/pilot-with-html/report/index.html`. An experiment's default report contains its own dataset. The separate `report` command adds optional documented issues and layout controls.

Coverage/generation elapsed time and resource measurements stop before HTML rendering. `empirical_seconds` records empirical publication and `report_seconds` records HTML generation separately, and `html_report` gives the relative report path. The dashboard's bundled `experiment.json` is the snapshot written immediately before rendering; the run-root file additionally records the completed report's duration and path. The existing main experiment was not rerun to add HTML.

## Evidence and validation

The current combined bundle contains 27,079 evidence files and is approximately 95 MiB on this machine. It retains saved source/manifests, repeat assessments, normalized JSON, raw coverage JSON, stdout/stderr, command logs, summaries, CSV tables, review overlays, and pair/issue results. Large instrumented binaries, object files, and profiles remain in the original run directories. Preserve those original directories for a complete measurement archive.

`report.json` records input-summary and rendered-asset SHA-256 hashes plus dataset counts. Generated bundles stay under ignored `runs/`; the report implementation, assets, tests, instructions, and compact validation record are tracked in Git.

Validation includes the full pinned-container test suite, opening the actual bundle via `file://` in Firefox, desktop/mobile layout checks, filters, deep source links, repeat-specific evidence, pair navigation, the documented zero-versus-two contradiction, and its corrective control. Separate labelled synthetic cases check HTML escaping, failed reports, changing repeat counts, and copy feedback. See [the saved validation record](evidence/dashboard-validation.json).

The full workflow, reporting-image setup, and the `report --empirical` option are documented in [final-pipeline.md](final-pipeline.md). The frozen-study interpretation is in [empirical-analysis.md](empirical-analysis.md).
