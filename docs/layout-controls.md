# E6: paired layout controls

Completed on 2026-10-11 using the frozen main dataset as the parent. Sixteen pairs were tested: two contrasting programs per construct family, each accompanied by a whitespace-only variant with braces on separate lines. The controls are a separate experiment, not 32 additional independent main-dataset programs.

```bash
bash scripts/env.sh layout-controls --dataset runs/main/dataset --output runs/layout-controls-new
bash scripts/env.sh review --analysis runs/layout-controls-new/analysis --output runs/layout-controls-new-review.json
```

The parent dataset can also be recreated without repeating its coverage experiment:

```bash
bash scripts/env.sh generate --per-family 40 --seed 20261010 --output runs/main-source-only
bash scripts/env.sh layout-controls --dataset runs/main-source-only --output runs/layout-controls-from-source
```

## Design and oracle safeguards

The intervention moves opening braces, separates `} else {`, and separates the closing brace from a `do` loop's trailing `while`. It leaves executable statement lines, expression tokens, literals, macro definitions, and preprocessor directives intact. Token sequences and directive text are checked for equality. This isolates brace placement; it is not an exhaustive study of arbitrary source layouts or macro rewrites.

The selection uses the generator's two contrasting endpoint parameters per family. The second constant-condition case instead uses a deterministically selected true `FLAG` macro from the frozen main dataset, ensuring that the definition-mapping pattern is exercised. Exact parents and parameters are saved in `pairs.json`. Parent dataset hashes, source hashes, and manifests are validated before any controls are written.

Variants carry versioned `layout_control` metadata alongside their generated-template manifests. Loading a variant reconstructs the original reviewed template and the exact permitted transformation, then checks the entire source, oracle, and relocated source locations. Metadata alone cannot establish trust. Statement IDs, counts, final state, expected output, and semantic branch outcomes remain identical to the parent. Statement and decision locations are relocated programmatically; branch alignment with tool reports remains unimplemented.

Both GCC and Clang independently execute trace twins with the same layout transformation before coverage analysis. The original coverage sources are executed without those trace additions. The suite then collects both tools three times from clean builds/profiles, checks functional witnesses, and compares statements by semantic ID rather than equal numeric line positions.

## Results

| Metric | Result |
| --- | ---: |
| Pairs / source programs | 16 / 32 |
| Successful dual-compiler trace validations | 32/32 |
| Valid coverage programs | 32/32 |
| Pairs preserving all statement observations and correct oracle counts | 16/16 |
| Compared semantic statement pairs | 107 |
| Comparable statement locations across all 32 programs | 210 |
| Oracle contradictions / unstable cases / pipeline failures | 0 / 0 / 0 |
| Paired coverage collections | 96 |
| Pairs with changed mapping totals | 16 |
| Pairs with changed case classification | 13 |

There are 214 annotated statement locations across the 32 programs. Four explicitly unreachable constant-body locations have no GCC mapping, leaving 210 mutually reported locations. Identically missing elidable zero statements are retained when comparing the 107 semantic pairs. A pair cannot pass merely because both sides report the same wrong count: each reported count must also match its oracle.

The 16 rerun parent programs exactly reproduce their original main-experiment semantic signatures, including coverage, branch metadata, and functional outputs. All 32 control programs were stable across three runs. There were 192 instrumented executions and 64 separate noncoverage trace executions.

| Family | Pairs | Mapping differences in parents | Mapping differences in variants |
| --- | ---: | ---: | ---: |
| If/else | 2 | 8 | 21 |
| Loops | 2 | 4 | 11 |
| Switch | 2 | 4 | 10 |
| Short circuit | 2 | 6 | 16 |
| Multiline | 2 | 10 | 20 |
| Ternary | 2 | 2 | 6 |
| Macros | 2 | 10 | 22 |
| Constants | 2 | 11 | 21 |
| **Total** | **16** | **55** | **127** |

Across both layouts there are 182 missing/present mapping differences and four raw binary/count differences on multiline continuations. Under unchanged convention rules, 13 parents have known-convention classifications and three are unresolved; all 16 variants are unresolved. This produces 13 known-convention and 19 unresolved cases overall. These are case classifications, not failed statement-invariance checks.

## Review and interpretation

Separating the function header from its brace creates 16 unresolved header mappings: gcov reports 1 on `int main(void)` while LLVM has no entry on that line. Separating `else` creates 11 unresolved keyword mappings: GCC has no entry while LLVM reports 0 or 1. These syntax-only lines have no scored statement oracle. The original constant and `do` patterns also remain visible.

The control audit checked every source-line/tool observation across all 96 paired collections, verified raw evidence and semantic signatures, and grouped all 35 unresolved observations across 19 cases. The groups are 16 separate function headers, 11 separate `else` keywords, four constant-condition headers, two constant macro definitions, and two `do` headers. They remain unresolved under rule version 1; no main result was reclassified and no rule was broadened.

The experiment demonstrates that the displayed line maps and case classifications depend on layout even when scored statement counts and functional behavior remain invariant. It does not demonstrate a new coverage-tool error. It also identifies a concrete classifier limitation to disclose in the final report: convention rules currently match the original source layouts more fully than the added variants.

## Evidence and validation

Final evidence is retained in `runs/layout-controls-verified/`, with a separate review in `runs/layout-controls-verified-review.json`. An earlier implementation-validation run is retained separately under `runs/layout-controls/`; it is not added to E6 totals. The final run records the complete tested Python implementation digest and the unchanged pinned tool/image identities.

Tracked evidence includes [the summary and provenance](evidence/layout-controls-summary.json), [full paired statement results](evidence/layout-controls-pairs.json), [pair-summary CSV](evidence/layout-controls-pairs.csv), [per-case CSV](evidence/layout-controls-cases.csv), and [the mapping review](evidence/layout-controls-review.json). Raw reports, profiles, logs, sources, and trace twins are retained locally and can be regenerated with the commands above. Dataset SHA-256: `f17e511612666b47a5c4f0c7cdd2a37c888db181e981e66dae53320018cba1bf`.

All 64 framework tests pass in the pinned Docker image with no skips. New checks cover exact source/manifest reconstruction, directive/literal preservation, semantic statement relocation, malformed parent indexes, equal-but-wrong paired counts, explicit zero-count elision, raw-evidence corruption, and actual execution of all 16 pairs. HTML reporting, final figures, and the final demonstration remain subsequent work; branch alignment and reduction remain stretch goals.
