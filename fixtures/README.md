# Handwritten calibration oracle

The calibration suite deliberately uses manually selected statement locations. Expected counts were written from the C semantics before running either coverage tool. The `@cov` comments make those locations reviewable, and the adjacent JSON files are the oracle inputs. Their SHA-256 values reject manifests paired with changed source.

| Family | Contrasting cases | Semantic expectation |
| --- | --- | --- |
| If/else | Positive and negative input | Exactly one body executes once |
| Loops | Zero-iteration while and three-iteration for | Body counts zero and three; final output once |
| Switch | Case one and unmatched selector | Only the selected body executes; each path breaks |
| Short circuit | False AND left; false OR left | RHS call counts zero and one, witnessed in stdout |
| Multiline | Both operands true; first false | Then versus else; continuations retained but unscored |
| Ternary | True and false selector | Whole assignment once; selected arm confirmed by output |
| Macros | Enabled and disabled invocation | Invocation count one or zero; accumulator witnessed |
| Constants | Literal true and literal false | Live body once; dead body zero or explicitly elided |

Each fixture prints one deterministic result and exits normally. All programs use C11 at `-O0`, small integer values and bounded execution. There is no runtime nondeterminism or undefined arithmetic. Different branches and skipped statements provide negative controls as well as positive execution checks.

Counts are checked exactly at annotated statements, not across every syntactic line. Case labels, braces, macro definitions and multiline condition fragments can have tool-specific mappings. Both full normalized reports remain available for inspection. Raw branches are retained but their semantic alignment is not implemented.

LLVM 14's JSON line normalization is checked against the primary `llvm-cov show` view on every case. For macro cases that view includes the definition line, while file summary statistics aggregate function views. The validation records that scope difference and does not assume equal totals. It still requires every normalized line count to agree with the display. Non-macro fixtures also require matching mapped and covered line totals.

When editing a fixture, re-derive its semantic expectation and update its manifest and SHA-256 together. Changing an expectation simply to match a tool report would invalidate its role as an independent oracle. These fixtures are calibration programs, not documented tool-bug reproductions or the final generated dataset.
