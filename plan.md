# CovDiff-Lite development and experiment plan

## 1. Approval gate and priorities

This plan develops the proposal in [project.md](project.md). **The user authorized steps 1 and 2 on 2026-10-09:** the testing environment and handwritten coverage pipeline. That scoped instruction is recorded in [docs/approval.md](docs/approval.md); it does not assert separate instructor approval. Implementation status and validated results are recorded in [docs/step12-results.md](docs/step12-results.md). The remaining sections describe the full project, including pending work.

On 2026-10-10 the user authorized the generator/oracle, discrepancy analysis, documented problem reproduction, and the pilot, with a commit after each stage. Generator/oracle progress is recorded in [docs/generator-oracle.md](docs/generator-oracle.md); the analyzer and its validation are recorded in [docs/discrepancy-analysis.md](docs/discrepancy-analysis.md). The pilot is complete; see [docs/pilot-results.md](docs/pilot-results.md). The main coverage experiment was subsequently authorized and completed on 2026-10-11; see [docs/main-results.md](docs/main-results.md).

After approval, record the approving person, approval date, approved scope, and a reference to the written approval. The three-week schedule starts at that point; the days below are project workdays rather than fixed calendar dates.

The required implementation is deterministic C generation, a trustworthy line-coverage oracle, both coverage pipelines, normalization, classification, repeatability checks, and an offline HTML report. Two documented discrepancy patterns have been reproduced on the pinned baseline; see [docs/documented-issues.md](docs/documented-issues.md). Branch comparison and automatic reduction are optional if they threaten the core schedule.

## 2. Machine inventory and environment setup

The following was observed using read-only checks on 2026-10-09. This is an inventory, not evidence that the coverage pipeline works.

| Item | Observed state | Planned action after approval |
| --- | --- | --- |
| Host OS | Ubuntu 22.04.5 LTS, x86-64; Linux 6.8.0-110-generic | Record host and container identities separately |
| CPU | Intel Core i7-12700; 20 logical CPUs | Start sequentially; allow four independent case workers after the pilot |
| Memory | About 15 GiB total; about 8.1 GiB available at inspection | Start with a container memory limit of 4 GiB and monitor peak usage |
| Storage | About 314 GiB free on the project filesystem | Reserve an initial 5 GiB artifact budget; revise from pilot measurements |
| GCC / gcov | Both 11.4.0; GCC package `11.4.0-1ubuntu1~22.04.3` | Candidate baseline; keep compiler and reporter matched |
| LLVM tools | `llvm-cov` 14.0.0; `llvm-profdata` present; LLVM package `1:14.0.0-1ubuntu1.1` | Use a matching Clang, coverage reporter, profile merger, and instrumentation runtime |
| Clang | `clang` and checked versioned names `clang-14`, `clang-15`, `clang-16` were not found on PATH | Provide Clang and its profile runtime in the container |
| Python | Interpreter 3.10.12 | Pin the container interpreter and any development dependencies |
| Docker | Snap executable present; invocation failed because this restricted session cannot create Snap runtime/user directories | Verify Docker and daemon access in the authorized execution environment; usability is unconfirmed |
| Repository | Clean Git working tree; no existing application files were found before these documents | Begin a small Python CLI project after approval |

Use an Ubuntu 22.04 container as the candidate baseline with GCC/gcov 11.4 and Clang/LLVM 14. Exact versions are provisional until a matched toolchain passes the pilot. Pin the Ubuntu base image by digest, exact package versions and Python dependencies, then retain the built image digest and package inventory. Archive or use a package snapshot if exact packages cannot reliably be fetched later; major-version package names alone are insufficient pins.

Build the image once, outside experiment timing. Mount the project artifact directory into the container and retain outputs on this machine. Run cases without network access after setup. Use native tools only for debugging if container access needs repair, and label native runs separately from the container dataset.

Do not silently mix versions to reproduce historical issues. If a documented bug is fixed or absent in the baseline, create a separately pinned historical environment with the same two tool families. Keep that validation experiment separate from the main dataset. Check applicability and version requirements in Week 1 before committing to expensive compiler builds.

## 3. Proposed architecture and files

Use a Python command-line application and an offline static HTML report. A hosted website, web server, database, and external services are unnecessary for the course demonstration.

```text
Template + parameters + seed
        |
        v
C source + oracle manifest + expected output
        |
        +--> GCC build / run --> gcov JSON --------+
        |                                        |
        +--> Clang build / run --> llvm-cov JSON --+
                                                 |
                          validate functional output
                                                 |
                          normalize and check oracle
                                                 |
                          classify / repeat suspects
                                                 |
                          JSON + CSV + offline HTML
```

The following is the target layout. Runners, parsers, generator/oracle, comparison, conventions, repeats, configurations, experiment execution, and offline HTML reporting are implemented; reduction remains optional.

```text
Dockerfile
pyproject.toml
src/covdiff_lite/
  cli.py                  # generate, run, analyze, report, reproduce
  generator.py            # template rendering and deterministic parameters
  oracle.py               # execution expectations and manifest validation
  models.py               # normalized observations and classifications
  runners/gcc.py
  runners/llvm.py
  parsers/gcov.py
  parsers/llvm.py
  compare.py
  conventions.py
  repeat.py
  report.py
  reduce.py               # optional
templates/                # eight construct families
fixtures/                 # handwritten and documented issue cases
tests/                    # oracle, parser, classifier, integration tests
configs/                  # smoke, pilot, main experiment configurations
docs/                     # approval record, issue notes, final analysis
runs/<run-id>/            # generated dataset and retained evidence
```

Keep execution, parsing, semantic expectations, and classification separate. Save raw reports before normalization so a parser fix can reanalyze the same experiment without rerunning programs.

## 4. Oracle and comparison contract

### Deterministic generation

Use C11, `-O0`, bounded inputs and loops, initialized variables, small arithmetic ranges, and explicit sequencing. Avoid undefined behaviour, signed overflow, unspecified evaluation-order dependencies, clocks, randomness at runtime, threads, and external input. Generator randomness is permitted only through a recorded fixed seed.

Begin with one executable statement per line and expand deliberately into multiline and macro cases. Assign stable statement and decision identifiers. Compute line and column locations during final rendering rather than maintaining handwritten line numbers. A case ID must incorporate the template version and parameters; retain the source SHA-256 and generator revision.

Each manifest should contain schema version, case ID, family, template version, seed, parameters, source hash, expected stdout and exit status, statement counts, semantic branch outcomes, source locations, line roles, and comparability annotations with reasons.

Derive expected execution from template semantics independently of both coverage reports. For example, a loop with `n` iterations has body count `n` and, without an early exit, condition outcomes `n` true and one false. Short-circuit operands can be unevaluated; represent that separately from evaluation to false. For `switch`, record the selected case and execution through fall-through as separate events.

### Validate the oracle before trusting it

Manually review at least two contrasting parameter instances per family. Exhaustively check the small Boolean input domains and loop boundaries. For calibration, optionally emit a separate trace-enabled twin with statement counters and compare its execution with the manifest. Do not use coverage from that altered source as evidence about the original program. Require both compiler outputs to match the manifest's expected stdout and exit status, not merely each other.

### Line observations

The primary metric is binary line execution, `covered` versus `uncovered`, on source locations with a defensible mapping. Preserve exact execution counts and compare them where the template and tool semantics make them meaningful, especially for documented count discrepancies.

An absent report entry is not zero. Represent observations with an explicit state such as `reported`, `not_reported`, or `unsupported`, and a count that is an integer only when actually available. Separate comments, braces, macro definitions, condition continuations, case labels, and executable statements. Exclude ambiguous mappings from comparable-line denominators, but show them in the report and count mapping differences separately.

Normalize GCC's line records without discarding `unexecuted_block` or branch metadata. LLVM JSON uses source segments and regions rather than a direct gcov-style line map; account for range endpoints, gap/skipped regions, and macro expansions. Calibrate the conversion against the matching `llvm-cov show` output and line summaries on fixtures. Do not assign a count to every line touched by any region or assume that a maximum region count always matches LLVM's line rules. See the [GCC 11 gcov documentation](https://gcc.gnu.org/onlinedocs/gcc-11.5.0/gcc/Invoking-Gcov.html), [LLVM 14 export documentation](https://releases.llvm.org/14.0.0/docs/CommandGuide/llvm-cov.html), and [LLVM coverage mapping format](https://llvm.org/docs/CoverageMappingFormat.html).

### Branch observations, if enabled

The oracle uses semantic IDs for decision true/false outcomes and evaluated Boolean operands. GCC reports control-flow arcs while LLVM reports source condition regions; these are not automatically equivalent. Never align branches just by array index, gcov branch number, or a presumed true/false ordering. Prove mappings on simple fixtures, attach source spans, and mark complex or ambiguous mappings unsupported. Preserve raw outcomes for inspection and report mapped and unmapped totals separately. `switch` and macro branch mapping can remain unresolved while line analysis proceeds.

## 5. Coverage execution pipeline

For each case and each repetition, create a fresh directory for each tool. Retain all command arguments, working directories, relevant environment variables, stdout, stderr, exit codes, timeouts, durations, and produced artifacts. There must be no reuse or accumulation of profile data across repetitions.

The planned command sequence below is illustrative and must be checked against the pinned tool versions after approval. It is not an available project command today.

```bash
# GCC tool directory; copy the exact case source here first.
gcc -std=c11 -O0 -g --coverage -Wall -Wextra -c case.c -o case.o
gcc -O0 --coverage case.o -o case
./case
gcov -j -b -c -o . case.c

# Separate LLVM tool directory; use identical source bytes.
clang -std=c11 -O0 -g -fprofile-instr-generate -fcoverage-mapping \
  -Wall -Wextra case.c -o case
LLVM_PROFILE_FILE=case.profraw ./case
llvm-profdata merge -sparse case.profraw -o case.profdata
llvm-cov export ./case -instr-profile=case.profdata > coverage.json
```

Gcov JSON output is gzip compressed; parse the produced `.gcov.json.gz` file. The Clang instrumentation, profile merge, and report sequence follows the [Clang 14 source-based coverage documentation](https://releases.llvm.org/14.0.0/tools/clang/docs/SourceBasedCodeCoverage.html).

Start with a 30-second compile timeout, a two-second program timeout, and a 15-second extraction timeout per subprocess; adjust only using pilot evidence. On timeout terminate the process group and record the stage. Separate compilation, execution, extraction, parsing, and functional validation failures from coverage classifications. Compiler warnings are recorded, since constant-condition fixtures intentionally produce some warnings.

## 6. Classification and repeatability

Apply classification at the observation level and roll it up to the case level while preserving all reasons. A case can contain convention differences and a probable incorrect report simultaneously.

1. Validate successful builds, execution, matching expected output, report provenance, and parser support. Failures receive a pipeline status and are excluded from coverage agreement rates.
2. Compare each tool independently against the oracle, even when the tools agree with each other. Also compare the tools directly.
3. Separate binary execution mismatches, comparable count mismatches, and mapping/presence differences. Record affected locations before applying convention rules.
4. Apply narrowly scoped, documented convention rules with an ID, matching predicate, version applicability, and supporting calibration evidence. The presence of a macro or multiline expression alone must not dismiss a mismatch.
5. Rerun every discrepant or suspicious case twice from clean builds and profiles, giving three independent observations. Rerun a deterministic 10% sample of otherwise agreeing main-dataset cases as a control.
6. Classify changing semantic observations as **unstable or non-reproducible**. Ignore incidental differences in timestamps, paths, and runtime when computing stability signatures.
7. Classify a stable contradiction on a trusted comparable location as **probable incorrect coverage report**; retain manual review status. Use **unresolved disagreement** for uncertain oracle or mapping semantics. Known conventions require an actual matching rule. **Complete agreement** requires agreement with the oracle on all comparable observations and no unexplained mapping differences; disclose excluded locations.

Use a case roll-up order of unstable, pipeline failure, probable incorrect report, unresolved, known convention, and complete agreement, with secondary labels preserved. Stability alone is insufficient to establish a tool bug. Review potential oracle and parser faults before attributing responsibility to GCC or LLVM, and describe the compiler/instrumentation/reporter pipeline involved.

## 7. Experiments to run on this machine

E0 and E1 have now been run for the authorized first two steps; see [docs/step12-results.md](docs/step12-results.md). E2 is complete with 40 valid pilot programs and three stable runs per case; E5 reproduces two documented patterns with a corrective control. E3–E4 are complete with 320 valid main cases and three stable runs per case. Findings review is complete and E6 passes all 16 layout pairs (32 programs); E7 remains optional. Carry out further experiments in the pinned container as their implementation is authorized and completed.

| ID | Experiment | Size / conditions | Evidence and purpose |
| --- | --- | --- | --- |
| E0 | Environment preflight | One minimal smoke program through both pipelines | Matched tools, runtime availability, JSON schemas, successful profile writes, expected output |
| E1 | Handwritten calibration | 16 fixtures: two contrasting cases in each of eight families | Reviewed oracle, raw JSON, parser cross-checks, line-role and branch-mapping decisions |
| E2 | Pilot | 40 generated programs: five per family; seed `20261009` | Time, disk and memory measurements; failures; oracle and normalization fixes |
| E3 | Main experiment | 320 generated programs: 40 per family; seed `20261010` | Frozen dataset and primary results, grouped by family and comparability tier |
| E4 | Repeatability | Two additional clean runs of every discrepant/suspicious main case and 32 agreeing control cases, if available | Stable mismatch signatures, failure recurrence, instability rate |
| E5 | Documented issue validation | At least two separately tracked issue fixtures; three clean runs each | Local proof that documented incorrect behaviour is reproduced, version applicability and functional witness |
| E6 | Layout and convention controls | 16 pairs (32 programs), two pairs per family | Same semantic output/statement counts under layout changes; mapping shifts and convention-rule validation |
| E7 | Optional reduction | Up to five stable important cases; ten-minute budget per case | Before/after size, preserved mismatch and fresh repeatability checks |

The main dataset has 320 unique source programs, not 320 executions. Calibration, pilot, known issues, paired controls, and reruns are reported separately. If the pilot reveals resource or schedule limits, use 200 main cases, 25 per family. Expand to 400 only if the core work is complete; do not expand merely to reach a larger count. Remove duplicate source hashes and replace duplicates deterministically. Do not claim the sample is representative of all C programs.

### Main dataset composition

| Family | Unique programs | Planned parameter dimensions |
| --- | --- | --- |
| `if` / `else` | 40 | True and false paths, nesting, early returns, reached and unreached bodies |
| Loops | 40 | `for`, `while`, `do-while`; zero where legal, one and several iterations; bounded `break` / `continue` |
| `switch` | 40 | Selected cases, explicit/implicit default, reached/unreached case bodies, controlled fall-through |
| Short-circuit expressions | 40 | `&&`, `||`, small Boolean combinations, operand evaluated versus skipped |
| Multiline conditions | 40 | Split operands and parentheses; contrasting outcomes and source layouts |
| Ternary expressions | 40 | Each arm selected, nested and multiline forms, arm execution versus whole-line execution |
| Macros | 40 | Expression macros, statement macros, repeated invocation, conditional and early-return bodies |
| Constant conditions | 40 | Literal and defined constants, always-true/false paths, compile-time removal at `-O0` |
| **Total** | **320** | Balanced families with recorded parameters and semantic expectations |

Choose a deterministic parameter grid within each family rather than 40 cosmetic copies of one program. Mark source locations as simple comparable statements, comparable after validated normalization, or unresolved mapping. Include both exercised and deliberately unexercised statements. Optional branch support must not delay generating the full line dataset.

### Documented problem patterns

These are literature-backed candidates, not local findings or promises that the baseline versions contain the issue.

| Candidate | Documented pattern | Planned oracle witness and validation |
| --- | --- | --- |
| GCC PR93680 | `do-while` inside a `switch` case can associate a case-label count with loop executions | Separate switch-entry count from body iterations; inspect raw label/count attribution, then check whether the baseline reproduces the described error rather than ordinary label conventions |
| LLVM #140427 | A macro containing a conditional `return` can give an incorrect count to a following statement | Use a deterministic call schedule covering both returns and fall-through; compare the following statement's count with the manifest and a printed final accumulator; include a variant in which the statement is never executed |
| Optional LLVM #131505 | System-header macros in short-circuit expressions can produce incorrect branch counters | Attempt only the ordinary branch-coverage aspect if supported; use a small controlled local header, not a real package; do not enable MC/DC |

The GCC pattern is described in the [GCC PR93680 patch discussion](https://gcc.gnu.org/pipermail/gcc-patches/2023-March/613496.html). The LLVM line pattern and an example of the incorrect count are documented in [LLVM issue #140427](https://github.com/llvm/llvm-project/issues/140427). The optional branch pattern is documented in [LLVM issue #131505](https://github.com/llvm/llvm-project/issues/131505). Save the issue URL, retrieval date, relevant reported version and commands, adaptation rationale, and local evidence for each attempt.

In Week 1, check whether candidates reproduce in C at `-O0` using ordinary line or branch coverage. If they do not, record **not reproduced on this version**, identify a documented affected version, or replace them with applicable documented C line issues. Do not relabel convention differences or synthetic report corruption as successful bug reproductions. If branch work is deferred, retain two applicable line/count patterns. If two genuine reproductions remain unavailable, report that requirement as incomplete; a clean generated dataset does not satisfy it.

Synthetic report mutations can test the classifier, but those cases must be labelled framework validation and excluded from real-tool findings.

### Resource and timing procedure

Run E0–E2 sequentially. Measure elapsed stage times with a monotonic clock. Use pilot medians and slowest cases to estimate the full experiment, including clean repeats. Run E3 sequentially, as frozen after the pilot; its measured cost does not justify parallel execution. Any later parallel implementation must use four workers at most, each owning separate directories and processes. The generated programs themselves remain single-threaded. Record worker count, container limits, peak resident memory, artifact size, host load context, and elapsed wall time. If parallelism causes failures, confirm sequentially before describing a coverage problem.

## 8. Results and artifacts to collect

### Per-case evidence

Store source, source hash, manifest, parameters, template revision, expected output, both actual outputs and exit statuses, raw compressed gcov JSON, LLVM JSON, normalization results, mismatch locations, rule matches, classifications, manual-review decisions, commands, tool versions, and stage durations. Retain `.gcno`, `.gcda`, `.profraw`, `.profdata`, binaries, and compiler logs within the artifact budget, prioritizing suspicious and documented cases if needed.

For repeats, record each repetition independently with its own semantic signature and command log. For issue cases, save upstream references and exact reproduction instructions. Reproduction must use the saved source and manifest without regenerating a potentially different program.

Planned artifact structure:

```text
runs/<run-id>/
  environment.json        # host, image, tool/package versions, revision
  config.json             # seeds, case counts, timeouts, workers, rules
  cases/<case-id>/
    case.c
    manifest.json
    repeat-0/gcc/          # build, run, raw report and command records
    repeat-0/llvm/
    repeat-1/              # only when repeated
    repeat-2/
    normalized.json
    analysis.json
    reproduce.sh
  results.jsonl           # one case summary per main case
  cases.csv
  observations.csv        # per-location comparison evidence
  summary.json
  issues.csv
  report/index.html
```

### Metrics and denominators

| Metric | Definition |
| --- | --- |
| Generated programs | Unique main-dataset source hashes; separate attempted, duplicate, calibration and issue totals |
| Compilation success | Successful compilations / attempted compilations, per tool; also cases where both compile / generated cases |
| Execution success | Successful expected exits / executable cases, per tool; timeouts and crashes separately |
| Functional validity | Cases matching expected stdout and exit status in both tools / cases executed in both |
| Extraction / parsing success | Successful reports / cases reaching that stage, per tool; unsupported schemas separately |
| Comparable lines | Oracle locations validly mapped to both reports; per-tool comparable locations also reported |
| Comparable branches | Mapped semantic outcomes; report decision and outcome counts separately, plus unmapped totals; `N/A` if deferred |
| Raw tool disagreements | Comparable observations with different binary coverage or counts; presence/mapping differences are a separate count |
| Oracle mismatches | Comparable tool observations contradicting the oracle, per tool; include shared errors where tools agree |
| Convention explanations | Observations explained by validated rules / raw discrepancies of the corresponding kind; counts by rule |
| Stable unexplained discrepancies | Unexplained observation signatures persisting across all three clean runs; separate probable errors from unresolved |
| Unstable cases | Repeated cases with changing semantic observations / all repeated cases; controls separately |
| Documented issues reproduced | Distinct issue IDs with the documented symptom and three stable local runs / attempted issue IDs |
| Analysis time | Mean, median and p95 successful per-case first-pass time and each stage; rerun cost and total batch wall time separately |
| Reduction | Original and reduced nonblank lines and bytes; percentage decrease and reduction elapsed time; `N/A` if omitted |

Also report mutually exclusive case totals using the roll-up rule, affected-case rates, excluded observations by reason, and results by family. Case counts and observation counts must not be mixed. Coverage agreement rates use successfully validated comparable cases/locations, while all failures remain visible in overall totals.

### Final analysis and figures

Produce a pipeline success table, classification counts, a family-by-classification chart, comparable/mapping-excluded line counts per family, and runtime distributions. Add a branch-outcome chart only if mapping is implemented. Generate standalone PNG or SVG figures from frozen CSV data and retain the plotting inputs and script.

Review every probable incorrect report. For unresolved cases, retain review status and disclose any review limit. Discuss whether differences arise from line attribution, region aggregation, macros, constants, or unsupported mapping. Group equivalent discrepancy signatures so 20 variants of one pattern are not claimed as 20 independent bugs. Explain limitations: finite templates, one primary version pair, `-O0` only, single-machine timing, and possible oracle mistakes. Do not invent expected numerical outcomes or claim a general compiler reliability rate.

## 9. Visual report and demonstration

The offline report should provide summary metrics and filters by family, classification and tool. Each case page shows numbered C source beside expected, gcov and LLVM observations; exact counts remain available alongside binary coverage. Use different labelled states for mismatches, conventions, unsupported mappings, and missing data. Include branch spans/outcomes if supported, tool versions, repeat history, matched convention rule, functional output, and a copyable reproduction command. Show all source lines even when excluded from scoring.

Link local raw reports and manifests, escape generated source and output for HTML, use no required external assets, and ensure the report can be opened offline. The report must show **no discrepancies found** accurately if that is the result, rather than manufacturing a showcase case.

The implemented JSON/CSV experiment interface is:

```bash
# Main experiment completed; use a new directory for a subsequent run.
bash scripts/env.sh experiment --config configs/main.json --output runs/main
bash scripts/env.sh analyze --case runs/main/analysis/cases/<case-id>/manifest.json --output runs/replay
```

The Docker wrapper is implemented. The experiment command generates, validates, executes, normalizes, classifies, and repeats cases. HTML generation is implemented: the experiment command now creates `report/index.html` after measurement. Saved runs can also be bundled with `report`; see [docs/offline-dashboard.md](docs/offline-dashboard.md). It should finish collecting the batch despite individual failed cases, record those failures, and provide a meaningful exit status.

The final demonstration runs one known agreeing generated case and one verified discrepancy case from source/manifest through the highlighted report, then reproduces the saved suspicious case in a clean directory. Use a documented fixture if the main generated corpus has no probable errors; identify its separate origin clearly.

## 10. Three-week development milestones

| Workdays | Work | Completion evidence |
| --- | --- | --- |
| Before Day 1 | Obtain and record written project approval | Approval reference and accepted scope; implementation may begin |
| Days 1–2 | Validate Docker, pin environment, run E0; draft normalized schemas | Saved image/package identity; both smoke reports and expected output |
| Days 3–4 | Implement both runners and parsers; run E1; investigate first documented candidate | Reviewed fixture expectations; pipeline logs; at least one genuine reproduction if applicable |
| Day 5 | Validate line normalization and issue-version strategy | Agreement fixtures pass; missing-versus-zero handled; two applicable issue targets selected |
| Days 6–7 | Implement eight template families and manifests; validate oracle | Deterministic source/hash regeneration and reviewed semantic expectations |
| Days 8–9 | Implement comparison, convention rules, clean repeats, and initial HTML report | Both-agree-but-wrong detection; convention reasoning; highlighted saved-case page |
| Day 10 | Run E2; fix oracle/parser issues; freeze main config; decide branch scope | Pilot timing/artifact budget; passing targeted framework tests |
| Days 11–12 | Run E3–E6; reproduce second documented issue; review suspects | 200–500 unique main cases; raw data and clean repeats; two issue dossiers |
| Day 13 | Finalize classifications and report; attempt E7 only if core is complete | Auditable case evidence, consistent totals; optional reduced reproducers |
| Day 14 | Write empirical analysis and generate tables/figures | Frozen machine-readable summaries, explanatory issue examples, limitations |
| Day 15 | Run clean demonstration and package reproducibility materials | One-command pipeline, offline report, normal and discrepancy demo, saved commands |

## 11. Verification and scope decisions

Add focused tests for deterministic generation, oracle boundary counts, line numbers after rendering, missing data, malformed and versioned reports, LLVM multiline/macro regions, ambiguous branches, shared oracle contradictions, convention-rule specificity, and stability signatures. Use labelled synthetic report mutations for detection checks. Run integration tests against the actual pinned tools using reviewed agreeing and documented fixtures. Keep failures and stderr visible rather than accepting partial reports.

After the pilot, freeze schema, template versions, source dataset and convention rules for E3. Any later classifier correction must be versioned and applied to all affected saved reports; changes to source or oracle require rerunning affected cases. Preserve the earlier result snapshot.

If branch mapping remains ambiguous by Day 10, report branch results as unavailable and finish the line study. If reduction is attempted, remove template blocks or simplify parameters, regenerate and revalidate the oracle, and require the same trusted mismatch to persist across fresh runs; line-number changes alone must not satisfy the reduction predicate. Prefer a reviewed manual reproducer when automatic reduction cannot preserve program validity or oracle confidence.

The core is done when the approved one-command pipeline processes the chosen 200–500-case main dataset, preserves auditable evidence, checks both tools against the oracle, confirms suspicious cases, and produces a usable offline report and empirical analysis. Record explicitly whether two documented issues were successfully reproduced and whether branch mapping or reduction was completed. The environment, handwritten calibration, generator/oracle, discrepancy analysis, two documented patterns, and 40-case pilot have implementation and results. The main experiment and repeatability checks are also complete. Findings review and all 16 paired layout controls are complete; see [docs/findings-review.md](docs/findings-review.md) and [docs/layout-controls.md](docs/layout-controls.md). Offline HTML reporting is complete, including separate main/issue/layout views, reviewed findings, portable evidence, and automatic reporting for future experiments. Final empirical analysis/figures and the demonstration remain; the full project is not complete.
