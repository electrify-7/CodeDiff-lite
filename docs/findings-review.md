# Findings review

Completed on 2026-10-11 after the main results were committed as `5ce75a1`. No scored statement contradiction was found in the 320-program main experiment. All 56 unresolved cases were reviewed, covering 69 unresolved observations. Their original classifications remain unresolved: inspection identifies the affected syntax and confirms the evidence, but does not assign a universal line-count meaning to those locations.

## Evidence audit

```bash
bash scripts/env.sh review --analysis runs/main/analysis --output runs/main-reviewed-new.json
```

The audit reads saved files; it does not compile or execute programs. The recorded main review was performed by the same Python implementation on the host. Coverage measurements themselves were performed in the pinned container.

For all 320 cases and 960 paired collections, the audit reconstructed the reviewed template/oracle, verified source hashes and annotated locations, checked displayed counts against raw gcov JSON and native LLVM text output, checked command exits and functional stdout, recomputed semantic signatures from saved normalized reports and actual outputs, and rechecked every recorded convention-rule predicate. It checked 28,314 source-line/tool observations across the three repetitions. No evidence inconsistency was found.

The review preserves the frozen main analysis. Current review statuses are stored as an overlay in [evidence/main-review.json](evidence/main-review.json); the original `manual_review` fields remain the historical values recorded before review. A future dashboard should use the overlay rather than rewriting original observations.

## Unresolved patterns

| Pattern | Observations | gcov | llvm-cov | Review decision |
| --- | ---: | --- | --- | --- |
| Constant `if` header | 40 | No line entry | Count 1 | Retain unresolved header mapping |
| Constant `FLAG` definition | 13 | No line entry | Count 1 | Retain unresolved macro-definition mapping |
| `do` header | 16 | No line entry | Count 1–5 | Retain unresolved loop-header mapping |

The 13 macro-definition observations occur in cases already counted among the 40 constant-header cases. Thus 69 observations affect 56 distinct cases, not 69 independent programs or bugs. All these locations are unscored; surrounding annotated statements and outputs agree with the independent oracle. The reviewed `do` counts vary with body iterations, while there is no separate GCC observation to compare against a shared header-count contract.

The 25 raw binary disagreements are all unscored multiline continuations with gcov count 0 and LLVM count 1. Each matches the existing scoped continuation rule. Neither these nor the missing mappings contradict a scored statement oracle. The 1,051 convention-rule observations were rechecked without expanding the rule set.

The review tool marks novel patterns, scored contradictions, or insufficient confirmation as requiring further inspection. Zero cases remain outside the reviewed pattern groups in this experiment. This does **not** mean that unresolved source-line semantics have been settled or that every possible compiler behavior has been tested.

## Paired control findings

The separately run [16 layout pairs](layout-controls.md) preserve identical C tokens, expected outputs, semantic trace events, and all 107 paired statement observations. Yet all 16 pairs change mapping totals and 13 change case classifications. The added unresolved mappings concern separate function headers and `else` keywords. Their location-level evidence is retained in [the control review](evidence/layout-controls-review.json).

This supports keeping the statement oracle and source-mapping interpretation separate. It also exposes a limitation of the current classifier: its narrow frozen rules cover the original templates more fully than these formatting variants. The controls pass the statement-invariance test while retaining their actual unresolved case classifications. Neither the main results nor rule version 1 were revised to improve the apparent agreement rate.

The main experiment therefore found no probable incorrect reports on scored locations within these finite templates. The two documented incorrect-report patterns remain separately validated examples; they are not counted as newly discovered main-dataset bugs.
