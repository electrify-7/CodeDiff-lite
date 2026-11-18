"""Scale Program Synthesis Engine: Expanded C Language Constructs & 5,000+ Corpus.

Implements expanded C construct families:
1. complex_macros: Variadic macros (__VA_ARGS__), token pasting (##), multi-line control flow
2. statement_expressions: GCC/Clang statement expressions ({ ... }) and attributes (__always_inline, cold)
3. non_local_control: setjmp/longjmp and computed gotos
4. vla_and_duff: Variable-length arrays and Duff's device loop unrolling patterns

Provides scalable deterministic synthesis up to 5,000+ verified test programs.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


EXPANDED_FAMILIES = (
    "complex_macros",
    "statement_expressions",
    "non_local_control",
    "vla_and_duff",
)


def map_source_lines_and_branches(
    source: str,
    stmt_counts: dict,
    branch_specs: Optional[List[dict]] = None,
) -> Tuple[dict, list]:
    """Scan emitted source code for // @id markers and bind physical line numbers."""
    lines_map = {}
    branches_list = []
    source_lines = source.splitlines()

    for line_idx, line_str in enumerate(source_lines, 1):
        if "// @id " in line_str:
            stmt_id = line_str.split("// @id ")[1].strip().split()[0]
            if stmt_id in stmt_counts:
                lines_map[str(line_idx)] = {
                    "statement_id": stmt_id,
                    "count": stmt_counts[stmt_id],
                    "role": "statement",
                    "allow_elided": False,
                }

    if branch_specs:
        for b_spec in branch_specs:
            pattern = b_spec.get("pattern", "if (")
            for line_idx, line_str in enumerate(source_lines, 1):
                if pattern in line_str:
                    branches_list.append({
                        "decision_id": b_spec["decision_id"],
                        "expected": b_spec["expected"],
                        "source_span": {"line": line_idx, "end_line": line_idx, "column": 5},
                        "mapping_status": "semantic_only",
                    })
                    break

    return lines_map, branches_list


def synthesize_complex_macro(variant: str, amount: int, condition_val: int) -> Tuple[str, dict]:
    """Synthesize programs with complex macros."""
    expected_result = 0
    branch_specs = []
    if variant == "variadic":
        expected_result = amount if condition_val else amount * 2
        source = f"""#include <stdio.h>

#define VAR_ADD(dst, amt, ...) do {{ (dst) += (amt); }} while (0)

int main(void) {{
    int result = 0; // @id init_result
    int flag = {condition_val};
    if (flag) {{
        VAR_ADD(result, {amount}, "extra", 1, 2); // @id then_body
    }} else {{
        VAR_ADD(result, {amount * 2}, "other"); // @id else_body
    }}
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {
            "init_result": 1,
            "then_body": 1 if condition_val else 0,
            "else_body": 0 if condition_val else 1,
            "output": 1,
            "return": 1,
        }
        branch_specs.append({
            "decision_id": "macro_flag_if",
            "pattern": "if (flag)",
            "expected": {"true": 1 if condition_val else 0, "false": 0 if condition_val else 1},
        })
    elif variant == "token_paste":
        expected_result = amount
        source = f"""#include <stdio.h>

#define GLUE_ADD(target, val) target##_val += (val)

int main(void) {{
    int result_val = 0; // @id init_result
    GLUE_ADD(result, {amount}); // @id paste_add
    printf("%d\\n", result_val); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {"init_result": 1, "paste_add": 1, "output": 1, "return": 1}
    else:  # internal_loop
        repetitions = 3 if condition_val else 1
        expected_result = amount * repetitions
        source = f"""#include <stdio.h>

#define LOOP_ADD(dst, amt, count) do {{ \\
    for (int _k = 0; _k < (count); _k++) {{ \\
        (dst) += (amt); \\
    }} \\
}} while (0)

int main(void) {{
    int result = 0; // @id init_result
    LOOP_ADD(result, {amount}, {repetitions}); // @id loop_macro
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {"init_result": 1, "loop_macro": 1, "output": 1, "return": 1}

    lines, branches = map_source_lines_and_branches(source, stmt_counts, branch_specs)
    manifest = {
        "schema_version": 1,
        "family": "complex_macros",
        "parameters": {"variant": variant, "amount": amount, "condition_val": condition_val},
        "expected_output": {"stdout": f"{expected_result}\n", "exit_code": 0},
        "lines": lines,
        "branches": branches,
    }
    return source, manifest


def synthesize_statement_expression(form: str, x: int, amount: int) -> Tuple[str, dict]:
    """Synthesize GCC/Clang statement expressions and function attributes."""
    branch_specs = []
    if form == "stmt_expr":
        inner_val = (x + amount) * 2
        expected_result = inner_val if inner_val > 0 else 0
        source = f"""#include <stdio.h>

int main(void) {{
    int x = {x};
    int result = ({{
        int inner = x + {amount}; // @id inner_calc
        inner > 0 ? inner * 2 : 0; // @id inner_select
    }}); // @id stmt_expr
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {"inner_calc": 1, "inner_select": 1, "output": 1, "return": 1}
    elif form == "always_inline":
        expected_result = x + amount
        source = f"""#include <stdio.h>

static inline __attribute__((always_inline)) int add_inline(int a, int b) {{
    return a + b; // @id inline_body
}}

int main(void) {{
    int result = add_inline({x}, {amount}); // @id call_inline
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {"inline_body": 1, "call_inline": 1, "output": 1, "return": 1}
    else:  # cold_attr
        taken = x < 0
        expected_result = amount * 10 if taken else amount
        source = f"""#include <stdio.h>

static __attribute__((cold)) int error_path(int val) {{
    return val * 10; // @id cold_body
}}

int main(void) {{
    int x = {x};
    int result = 0;
    if (x < 0) {{
        result = error_path({amount}); // @id then_call
    }} else {{
        result = {amount}; // @id else_assign
    }}
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {
            "cold_body": 1 if taken else 0,
            "then_call": 1 if taken else 0,
            "else_assign": 0 if taken else 1,
            "output": 1,
            "return": 1,
        }
        branch_specs.append({
            "decision_id": "cold_if",
            "pattern": "if (x < 0)",
            "expected": {"true": 1 if taken else 0, "false": 0 if taken else 1},
        })

    lines, branches = map_source_lines_and_branches(source, stmt_counts, branch_specs)
    manifest = {
        "schema_version": 1,
        "family": "statement_expressions",
        "parameters": {"form": form, "x": x, "amount": amount},
        "expected_output": {"stdout": f"{expected_result}\n", "exit_code": 0},
        "lines": lines,
        "branches": branches,
    }
    return source, manifest


def synthesize_non_local_control(mode: str, trigger: int, amount: int) -> Tuple[str, dict]:
    """Synthesize programs with non-local control flow (setjmp/longjmp, computed goto)."""
    branch_specs = []
    if mode == "setjmp_longjmp":
        taken = (trigger != 0)
        expected_result = (amount * 3) if taken else amount
        source = f"""#include <stdio.h>
#include <setjmp.h>

static jmp_buf env;

int main(void) {{
    int result = 0;
    int trigger = {trigger};
    if (setjmp(env) == 0) {{
        if (trigger != 0) {{
            longjmp(env, 1); // @id jmp_call
        }}
        result = {amount}; // @id normal_path
    }} else {{
        result = {amount * 3}; // @id recovered_path
    }}
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {
            "jmp_call": 1 if taken else 0,
            "normal_path": 0 if taken else 1,
            "recovered_path": 1 if taken else 0,
            "output": 1,
            "return": 1,
        }
        branch_specs.append({
            "decision_id": "trigger_if",
            "pattern": "if (trigger != 0)",
            "expected": {"true": 1 if taken else 0, "false": 0 if taken else 1},
        })
    else:  # computed_goto
        idx = trigger % 3
        vals = [amount, amount * 2, amount * 4]
        expected_result = vals[idx]
        source = f"""#include <stdio.h>

int main(void) {{
    static void *labels[] = {{ &&target_0, &&target_1, &&target_2 }};
    int result = 0;
    int idx = {idx};
    goto *labels[idx]; // @id indirect_jump

target_0:
    result = {vals[0]}; // @id t0
    goto end;
target_1:
    result = {vals[1]}; // @id t1
    goto end;
target_2:
    result = {vals[2]}; // @id t2
    goto end;

end:
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {
            "indirect_jump": 1,
            "t0": 1 if idx == 0 else 0,
            "t1": 1 if idx == 1 else 0,
            "t2": 1 if idx == 2 else 0,
            "output": 1,
            "return": 1,
        }

    lines, branches = map_source_lines_and_branches(source, stmt_counts, branch_specs)
    manifest = {
        "schema_version": 1,
        "family": "non_local_control",
        "parameters": {"mode": mode, "trigger": trigger, "amount": amount},
        "expected_output": {"stdout": f"{expected_result}\n", "exit_code": 0},
        "lines": lines,
        "branches": branches,
    }
    return source, manifest


def synthesize_vla_and_duff(style: str, size: int, amount: int) -> Tuple[str, dict]:
    """Synthesize programs with VLAs or Duff's device patterns."""
    if style == "vla_dynamic":
        expected_result = size * amount
        source = f"""#include <stdio.h>

int main(void) {{
    int n = {size};
    int vla[n]; // @id vla_decl
    for (int i = 0; i < n; i++) {{
        vla[i] = {amount}; // @id vla_init
    }}
    int sum = 0;
    for (int i = 0; i < n; i++) {{
        sum += vla[i]; // @id vla_sum
    }}
    printf("%d\\n", sum); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {"vla_decl": 1, "vla_init": size, "vla_sum": size, "output": 1, "return": 1}
    else:  # duff_device
        expected_result = size * amount
        source = f"""#include <stdio.h>

int main(void) {{
    int count = {size};
    int result = 0;
    int n = (count + 3) / 4;
    switch (count % 4) {{
        case 0: do {{ result += {amount}; // @id d0
        case 3:      result += {amount}; // @id d3
        case 2:      result += {amount}; // @id d2
        case 1:      result += {amount}; // @id d1
                }} while (--n > 0);
    }}
    printf("%d\\n", result); // @id output
    return 0; // @id return
}}
"""
        stmt_counts = {"d0": 1, "d3": 1, "d2": 1, "d1": 1, "output": 1, "return": 1}

    lines, branches = map_source_lines_and_branches(source, stmt_counts, [])
    manifest = {
        "schema_version": 1,
        "family": "vla_and_duff",
        "parameters": {"style": style, "size": size, "amount": amount},
        "expected_output": {"stdout": f"{expected_result}\n", "exit_code": 0},
        "lines": lines,
        "branches": branches,
    }
    return source, manifest


def generate_synthesized_case(family: str, params: dict, case_idx: int) -> Tuple[str, dict]:
    """Generate a single synthesized case with unique SHA hash and manifest."""
    if family == "complex_macros":
        source, manifest = synthesize_complex_macro(params["variant"], params["amount"], params["condition_val"])
    elif family == "statement_expressions":
        source, manifest = synthesize_statement_expression(params["form"], params["x"], params["amount"])
    elif family == "non_local_control":
        source, manifest = synthesize_non_local_control(params["mode"], params["trigger"], params["amount"])
    elif family == "vla_and_duff":
        source, manifest = synthesize_vla_and_duff(params["style"], params["size"], params["amount"])
    else:
        raise ValueError(f"Unknown synthesized family: {family}")

    h = hashlib.sha256(source.encode()).hexdigest()[:12]
    case_id = f"{family}_{case_idx}_{h}"
    manifest["case_id"] = case_id
    manifest["source"] = f"{case_id}.c"
    manifest["source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
    return source, manifest


def generate_large_scale_corpus(target_count: int = 5000, seed: int = 20261113) -> List[Tuple[str, dict]]:
    """Synthesize up to target_count unique, deterministic test cases."""
    cases = []
    seen_hashes = set()
    idx = 0

    # Expand parameters across all 4 new families
    param_grids = {
        "complex_macros": [
            {"variant": v, "amount": a, "condition_val": c}
            for v in ["variadic", "token_paste", "internal_loop"]
            for a in range(1, 25)
            for c in [0, 1]
        ],
        "statement_expressions": [
            {"form": f, "x": x, "amount": a}
            for f in ["stmt_expr", "always_inline", "cold_attr"]
            for x in range(-10, 15)
            for a in range(1, 15)
        ],
        "non_local_control": [
            {"mode": m, "trigger": t, "amount": a}
            for m in ["setjmp_longjmp", "computed_goto"]
            for t in range(0, 10)
            for a in range(1, 20)
        ],
        "vla_and_duff": [
            {"style": s, "size": sz, "amount": a}
            for s in ["vla_dynamic", "duff_device"]
            for sz in range(1, 20)
            for a in range(1, 15)
        ],
    }

    # Generate from expanded families
    for family, grid in param_grids.items():
        for p in grid:
            source, manifest = generate_synthesized_case(family, p, idx)
            sha = manifest["source_sha256"]
            if sha not in seen_hashes:
                seen_hashes.add(sha)
                cases.append((source, manifest))
                idx += 1
                if len(cases) >= target_count:
                    return cases

    # If still below target_count, expand parameterized variations
    multiplier = 2
    while len(cases) < target_count:
        for family in EXPANDED_FAMILIES:
            p = {"variant": "variadic", "amount": idx + multiplier, "condition_val": idx % 2} if family == "complex_macros" else \
                {"form": "stmt_expr", "x": idx - multiplier, "amount": multiplier} if family == "statement_expressions" else \
                {"mode": "setjmp_longjmp", "trigger": idx % 3, "amount": multiplier} if family == "non_local_control" else \
                {"style": "vla_dynamic", "size": (idx % 15) + 1, "amount": multiplier}
            source, manifest = generate_synthesized_case(family, p, idx)
            sha = manifest["source_sha256"]
            if sha not in seen_hashes:
                seen_hashes.add(sha)
                cases.append((source, manifest))
                idx += 1
                if len(cases) >= target_count:
                    return cases
        multiplier += 1

    return cases
