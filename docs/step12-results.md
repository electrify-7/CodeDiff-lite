# Environment and handwritten pipeline validation

Measured on 2026-10-09 on the project machine. These results cover steps 1 and 2, not the final generated experiment.

## Environment

| Component | Validated version / identity |
| --- | --- |
| Ubuntu base, linux/amd64 | `ubuntu@sha256:08ea48a03a3e78ebc7cd526e6a275053223aadd88bfc09cc49b06d5281525fde` |
| Archive snapshot | `20261001T000000Z` |
| Built testing image | `sha256:9b1f71840f4946181ccb96fab2d12c933fcf1a0b05b2bc5210dc4a2622d6a641` |
| GCC / gcov | 11.4.0 / 11.4.0 |
| Clang / llvm-cov / llvm-profdata | 14.0.0 / 14.0.0 / 14.0.0 |
| Python interpreter | 3.10.12 |
| Execution | Docker, network disabled, user 1001:1001, four CPU limit, 4 GiB memory limit |

The complete validated package inventory is committed in [environment/packages.lock.tsv](../environment/packages.lock.tsv). The image contains the same inventory. Source code is mounted from the repository, so the image ID identifies the tool environment; use the implementation commit to identify the Python pipeline and fixtures.

Docker daemon access was initially unavailable. The user enabled access, and the image was subsequently built and validated. The host compiler installation was not changed. On Ubuntu 22.04, Clang's profiling runtime comes from `libclang-common-14-dev`; it is included and pinned in the image.

## Observed results

| Check | Result |
| --- | --- |
| Tool preflight | All five tools found; compiler/reporter/profile-tool versions matched within each family |
| E0 smoke | 1/1 passed; two comparable annotated lines |
| E1 calibration | 16/16 passed; 63 comparable annotated lines |
| Functional outputs | Both compilers matched the expected stdout and exit status for every calibration fixture |
| Pipeline failures in corrected E1 run | 0 |
| Oracle count mismatches in corrected E1 run | 0 |
| LLVM display validation | All 16 normalized file views matched `llvm-cov show` |
| LLVM summary validation | Fourteen non-macro cases matched line totals; two macro cases record the distinct function-summary scope |
| Framework tests in Docker | 24 passed, including both real-tool integration tests; no skips |
| Corrected E1 elapsed time | Approximately 1.91 seconds for 16 sequential cases; image build and preflight excluded |

The time is one calibration observation, not a benchmark or an estimate of the final dataset. The 63 lines are selected oracle statement locations mapped by both tools, not all lines in the C files. Unreachable literal-constant bodies can be absent from gcov's mapping and are explicitly excluded when missing. No missing count is silently converted to zero.

An initial calibration run flagged two macro cases because it compared LLVM's file-view line total with its function-summary total. Inspection showed that the file display also includes the macro definition line. The final validation retains the full file counts and checks them against the display, while recording that the summary has a different scope. This was a framework validation correction, not a coverage-tool bug discovery. The initial artifacts remain available separately.

## Commands and retained local evidence

```bash
bash scripts/env.sh build
bash scripts/env.sh doctor --output runs/step12-environment.json
bash scripts/env.sh calibrate --fixtures fixtures/smoke --output runs/step12-smoke
bash scripts/env.sh test
bash scripts/env.sh calibrate --output runs/step12-calibration-validated
```

The corrected persistent E1 run is at `runs/step12-calibration-validated/`. Each case contains source, oracle manifest, normalized counts, GCC and LLVM profiles, raw JSON reports, LLVM display output, command records, stdout, stderr, exit codes and timing. These build/run artifacts are ignored by Git; the fixtures, recipe, package inventory, code and tests are committed.

The tests cover missing-versus-zero data, zero-count regions, multiline segments, gaps and skipped regions, incompatible schemas, raw branch preservation, source-hash validation, both-tools-agree-but-wrong cases, timeouts and logging. Integration tests also verify refusal to reuse run directories and rejection of equal functional outputs that contradict the oracle.

## Completed scope and remaining work

Step 1 is complete: the pinned image builds, Docker access works, the matched coverage toolchains execute, and environment identity is recorded. Step 2 is complete: handwritten fixtures execute through both pipelines, JSON is retained and parsed, selected line counts are checked against independent expectations, and normalization is calibrated.

The current statuses are `calibration_pass`, `oracle_mismatch`, and `pipeline_failure`. They are calibration statuses, not the final discrepancy classifier. Automatic generation, convention rules, three-run confirmation, semantic branch mapping, documented bug reproduction, the main experiment, HTML reporting and reduction remain later work. No documented upstream bug has yet been reproduced, and the final project definition of done has not yet been met.
