# Deterministic generator and independent semantic oracle

The generator renders a bounded model of C11 to source. A separate interpreter executes that model to compute statement counts, decision true/false outcomes, skipped short-circuit operands, selected switch cases, and expected stdout. Neither component reads compiler or coverage output. They share a model, so a separate C trace check validates the correspondence between rendering and interpretation.

## Supported families

Eight finite parameter grids live in `templates.py`: if/else (including nesting), for/while/do-while loops, switch (including controlled fall-through), short-circuit expressions, multiline conditions, ternary expressions, statement macros, and constant conditions (literal, defined, comparison and negation forms). Inputs and weights are small integers. Loops are bounded; there are no pointers, undefined arithmetic, runtime randomness, external input or unspecified evaluation-order dependencies.

Two contrasting control parameters are selected first in each family. Remaining parameters are ordered by SHA-256 of generator version, seed, family and canonical parameters. This avoids dependencies on Python random state, hash randomization and directory order. Seeds are unsigned 64-bit integers. Requests exceeding a family's finite grid are rejected before creating output.

IDs incorporate family, template version and a parameter digest. Source hashes detect duplication and stale source. Changing the seed changes selection and records provenance; identical template/parameter combinations keep the same source and case ID. A default corpus has 320 unique programs, 40 per family. This is a structured template sample, not a random representative sample of all C.

## Manifest contract

Each C file has an adjacent JSON manifest containing generator and template versions, seed, parameters, source SHA-256, expected output/exit code, statement IDs and counts, line/column locations, all source-line roles, semantic decision outcomes and expected trace events. Locations are assigned while rendering, never handwritten. Branch spans currently identify the enclosing construct; they do not claim exact operand-to-tool alignment.

Ordinary executable statements are compared by exact count. Condition continuations, braces, case labels, jumps and macro definitions have source roles but no invented universal line count. Unreachable constant bodies explicitly allow missing mappings; only their zero-count statements receive that annotation. Decision outcomes distinguish evaluated-false from a skipped operand. `not_evaluated` counts short-circuit/conditional-expression opportunities skipped while evaluating an enclosing expression; it does not count decisions inside an entirely unreached statement block.

Loading a generated case reconstructs its reviewed template, reinterprets it and compares the entire manifest and source. Editing a count, output or event while retaining the source hash is rejected. Saved run copies may rename the source to `case.c` without changing content or source locations.

## Independent C validation

`validate-oracle` renders a separate trace twin. That twin emits statement and decision events to stderr and is compiled at `-O0` with GCC and Clang, without coverage instrumentation. Both event sequences and stdout must match the model. Command logs and twin source are retained. The original source remains unchanged for coverage measurement. Trace validation is evidence for the oracle, not evidence about coverage on altered source.

Focused tests exhaustively check loop boundaries/styles, Boolean input combinations, switch dispatch versus fall-through, macro repetition counts, constant dead paths, nested decisions and ternary selections against independently written arithmetic/truth-table expectations. Integration tests also execute contrasting cases from every family through C traces and both coverage pipelines.

## Stage validation

Measured on 2026-10-10 in the existing pinned testing image:

- The 40-case pilot corpus (five cases per family, seed `20261009`) had 40/40 matching GCC and Clang trace validations.
- Its unmodified sources had 40/40 calibration passes and 263 comparable statement lines, with no pipeline failures or statement-count contradictions.
- A 320-case candidate corpus was generated, with 320 unique source hashes. It has not been used for the main coverage experiment.
- All 320 candidate oracles also matched both compilers' execution traces (640 executions without coverage); these checks validate the generator, not the main coverage results.
- All 34 framework tests passed in Docker, including three real-tool integration tests; no tests were skipped there.
- Repeated generation is byte-identical; the complete manifest is checked when cases load.

Pilot artifacts are in `runs/generator-pilot/`, `runs/generator-pilot-oracle/` and `runs/generator-pilot-coverage/`. Candidate corpus artifacts are in `runs/generator-main/`. These local run artifacts are ignored by Git; the model, templates, interpreter, renderer, CLI and tests are committed.

The generator/oracle does not provide semantic alignment of GCC control-flow arcs with LLVM branch regions. Discrepancy classification, clean confirmation runs and convention rules were subsequently implemented; see [discrepancy analysis](discrepancy-analysis.md) and [the completed pilot](pilot-results.md). The final main experiment remains deferred as instructed by the user.
