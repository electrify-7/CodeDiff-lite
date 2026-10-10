# Step 3: documented coverage problems

Two distinct documented patterns reproduced locally on 2026-10-10 with GCC/gcov 11.4.0 and Clang/llvm-cov 14.0.0, C11, and `-O0`. This is validation of existing reports, not discovery of new upstream bugs.

```bash
bash scripts/env.sh reproduce-issues --output runs/documented-issues-new
```

The command checks the specified tool and scored source location against the documented symptom. It requires matching coverage signatures, successful functional witnesses, and three fresh builds/profiles. An unrelated disagreement cannot satisfy the check. Negative controls require no scored oracle contradictions. Normalization remains cross-checked against `llvm-cov show`.

| Fixture | Location | Expected | gcov | llvm-cov | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| `gcc_pr93680` | case label, line 6 | 1 | 3 | 1 | GCC documented count error reproduced |
| `llvm_140427` | increment, line 14 | 1 | 1 | 4 | LLVM documented count-error pattern reproduced |
| `llvm_140427_never` | increment, line 14 | 0 | 0 | 2 | LLVM falsely reports binary coverage |
| `llvm_140427_control` | increment, line 16 | 1 | 1 | 1 | Corrective control passes |

All four cases were stable across three clean paired collections, totaling 12 paired collections and 24 instrumented program executions. Every expected stdout and exit status matched. There were no pipeline failures or instability. The positive cases classify as probable incorrect reports; the corrective control still has unresolved mappings elsewhere, which do not contradict its scored statement oracle.

## GCC PR93680

The [GCC maintainer discussion](https://gcc.gnu.org/pipermail/gcc-patches/2023-March/613496.html) attributes the problem to association of a switch label with a loop counter. The adaptation retains a switch with a `do-while` case body and adds a deterministic driver: one call selects case zero and executes its body three times. Its printed return value is 3. The case-selection count is 1 because there is neither fall-through nor a jump back to the label. Gcov JSON reports 3 for the label; LLVM reports 1. We score this reviewed label explicitly, rather than applying a generic unscored-label mapping rule.

## LLVM #140427

The [upstream issue](https://github.com/llvm/llvm-project/issues/140427) describes a conditional return in a macro corrupting the count of a following statement. Our small driver makes six calls: three exit before the macro, two exit inside it, and one reaches the increment. The increment is the only modification of a zero-initialized counter; the printed final value independently witnesses its execution count.

The never-executed adaptation removes the final fall-through call. The counter stays zero, yet LLVM reports 2 at the increment. The corrective control inserts a separate statement before the macro, as suggested in the upstream report; both tools then report the increment correctly. The adaptation reproduces the pattern, without claiming identical erroneous counts to the larger upstream example.

## Provenance and limits

Both primary references were retrieved on 2026-10-10. The cited issue body/discussion excerpt does not specify an exact affected release; our verified affected versions are the pinned local 11.4.0 and 14.0.0. No historical toolchain or optimization change was needed. Fixtures include source hashes, semantic rationale, issue links, adaptation notes, and precise symptom metadata.

Tracked compact evidence is in [evidence/documented-issues.json](evidence/documented-issues.json). Full raw reports, profiles, command logs, LLVM text displays, repeat analyses, and saved reproduction scripts remain in `runs/documented-issues-verified/`. These local run artifacts are intentionally ignored by Git; rerun the command above to recreate them on another machine. The compact evidence includes actual image and implementation digests, source hashes, per-run counts, signatures, and printed witnesses.

Branch mapping remains deferred. These reproductions establish the required two documented line/count patterns; they do not establish prevalence in the generated corpus or current compiler releases.
