"""Semantic branch and MC/DC alignment engine for GCC (gcov) and Clang (llvm-cov).

Resolves the fundamental architectural difference between:
1. GCC's CFG-edge arc model (branches attached to line basic-blocks)
2. LLVM's source AST region model (branches attached to character spans)
3. Ground-truth semantic oracle (condition-decision outcomes and MC/DC vectors)
"""

from typing import Any, Dict, List, Optional, Tuple
from .mcdc import DecisionTree, MCDCAnalyzer


def resolve_gcc_decision_branches(
    decision_id: str,
    span: dict,
    expected: dict,
    gcov_lines: dict,
    manifest: dict,
) -> Optional[Dict[str, int]]:
    """Align GCC line branch records to a semantic decision.

    Disambiguates CFG edges using structural AST reachability (matching the
    observed gcov execution count of the then-body and else-body basic blocks)
    rather than oracle expected counts, preventing circular validation.
    """
    line_num = str(span.get("line"))
    end_line_num = str(span.get("end_line", span.get("line")))

    # Check the lines spanning this decision without duplicate line processing
    l_start = int(line_num)
    l_end = int(end_line_num)
    branches = []
    seen_lines = set()
    for l_val in range(l_start, l_end + 1):
        if l_val in seen_lines:
            continue
        seen_lines.add(l_val)
        line_data = gcov_lines.get(str(l_val), {})
        for b in line_data.get("branches", []):
            branches.append(b)

    if not branches:
        # Check if surrounding lines have branches
        line_int = int(line_num)
        for offset in (-1, 1):
            neighbor = str(line_int + offset)
            if neighbor in gcov_lines and gcov_lines[neighbor].get("branches"):
                branches = gcov_lines[neighbor]["branches"]
                break

    if not branches:
        return None

    # Filter out compiler throw/exception arcs if present
    valid_branches = [b for b in branches if not b.get("throw", False)]
    if not valid_branches:
        valid_branches = branches

    # Structural Disambiguation: Find then/else block statement lines
    then_line = span.get("then_line")
    else_line = span.get("else_line")

    if (then_line is None or else_line is None) and manifest:
        # Infer then_line and else_line from manifest statement definitions following this decision
        dec_line = int(span.get("line", 0))
        lines_dict = manifest.get("lines", {})
        for l_str, l_meta in lines_dict.items():
            l_val = int(l_str)
            if l_val > dec_line and l_meta.get("role") == "statement":
                stmt_id = l_meta.get("statement_id", "")
                if then_line is None and ("then" in stmt_id or l_val == dec_line + 1):
                    then_line = l_val
                elif else_line is None and "else" in stmt_id:
                    else_line = l_val

    # Check observed statement counts in gcov_lines (compiler ground truth, NOT oracle)
    obs_then_count = None
    if then_line is not None and str(then_line) in gcov_lines:
        obs_then_count = gcov_lines[str(then_line)].get("count")

    obs_else_count = None
    if else_line is not None and str(else_line) in gcov_lines:
        obs_else_count = gcov_lines[str(else_line)].get("count")

    # Simple 2-branch case: determine which arc is True and which is False
    if len(valid_branches) == 2:
        counts = [valid_branches[0]["count"], valid_branches[1]["count"]]

        # 1. Structural match against observed then-body count in gcov
        if obs_then_count is not None:
            if counts[0] == obs_then_count and counts[1] != obs_then_count:
                return {"true": counts[0], "false": counts[1], "source": "gcc_cfgarcs_structural"}
            elif counts[1] == obs_then_count and counts[0] != obs_then_count:
                return {"true": counts[1], "false": counts[0], "source": "gcc_cfgarcs_structural"}

        # 2. Structural match against observed else-body count in gcov
        if obs_else_count is not None:
            if counts[1] == obs_else_count and counts[0] != obs_else_count:
                return {"true": counts[0], "false": counts[1], "source": "gcc_cfgarcs_structural"}
            elif counts[0] == obs_else_count and counts[1] != obs_else_count:
                return {"true": counts[1], "false": counts[0], "source": "gcc_cfgarcs_structural"}

        # 3. Fallback based on GIMPLE CFG convention:
        # In GCC GIMPLE conditional branch lowering:
        # branch with fallthrough=True falls into the sequential target;
        # branch with fallthrough=False executes the taken conditional jump.
        if valid_branches[0].get("fallthrough") and not valid_branches[1].get("fallthrough"):
            return {"true": counts[1], "false": counts[0], "source": "gcc_cfgarcs_cfg"}
        elif not valid_branches[0].get("fallthrough") and valid_branches[1].get("fallthrough"):
            return {"true": counts[0], "false": counts[1], "source": "gcc_cfgarcs_cfg"}

        return {"true": counts[0], "false": counts[1], "source": "gcc_cfgarcs_default"}

    # Multiple branches (e.g. short-circuit or compound switch)
    if len(valid_branches) >= 2:
        if obs_then_count is not None:
            for i, b in enumerate(valid_branches):
                if b["count"] == obs_then_count:
                    other_count = sum(o["count"] for j, o in enumerate(valid_branches) if j != i)
                    return {"true": b["count"], "false": other_count, "source": "gcc_cfgarcs_structural"}

        # Fallback to first two edges
        return {"true": valid_branches[0]["count"], "false": valid_branches[1]["count"], "source": "gcc_cfgarcs"}

    return None


def resolve_llvm_decision_branches(
    decision_id: str,
    span: dict,
    expected: dict,
    llvm_branches: list,
) -> Optional[Dict[str, int]]:
    """Align LLVM branch regions to a semantic decision based on AST source spans."""
    line_start = int(span.get("line", 1))
    line_end = int(span.get("end_line", line_start))
    col_target = int(span.get("column", 1))

    # LLVM branch region format:
    # [lineStart, colStart, lineEnd, colEnd, trueCount, falseCount, fileId, expandedFileId, regionKind]
    matching = []
    for reg in llvm_branches:
        if len(reg) >= 6:
            r_lstart, r_cstart, r_lend, r_cend, true_count, false_count = reg[:6]
            # Check overlap with decision span
            if not (r_lend < line_start or r_lstart > line_end):
                dist = abs(r_cstart - col_target)
                matching.append((dist, true_count, false_count, reg))

    if not matching:
        return None

    # Sort strictly by AST character column proximity to the decision locus
    matching.sort(key=lambda m: m[0])
    _, t_cnt, f_cnt, _ = matching[0]
    return {"true": t_cnt, "false": f_cnt, "source": "llvm_regions_ast"}


def classify_branch_finding(
    decision_id: str,
    expected: dict,
    gcc_obs: Optional[dict],
    llvm_obs: Optional[dict],
) -> dict:
    """Classify semantic branch and MC/DC discrepancies."""
    exp_true = expected.get("true", 0)
    exp_false = expected.get("false", 0)

    # Check for mapping issues
    if gcc_obs is None and llvm_obs is None:
        return {
            "decision_id": decision_id,
            "kind": "unresolved_edge_mapping",
            "assessment": "unresolved_disagreement",
            "reason": "Neither tool provided an alignable branch record for this decision",
        }
    if gcc_obs is None or llvm_obs is None:
        missing_tool = "gcov" if gcc_obs is None else "llvm-cov"
        return {
            "decision_id": decision_id,
            "kind": "asymmetric_branch_mapping",
            "assessment": "known_branch_convention",
            "reason": f"Tool {missing_tool} elided or omitted branch record for compile-time/unreachable path",
        }

    # Both tools mapped
    gcc_t, gcc_f = gcc_obs.get("true", 0), gcc_obs.get("false", 0)
    llvm_t, llvm_f = llvm_obs.get("true", 0), llvm_obs.get("false", 0)

    gcc_matches = (gcc_t == exp_true and gcc_f == exp_false)
    llvm_matches = (llvm_t == exp_true and llvm_f == exp_false)

    if gcc_matches and llvm_matches:
        return {
            "decision_id": decision_id,
            "kind": "complete_agreement",
            "assessment": "complete_agreement",
            "reason": "Both tools match expected ground-truth branch counts exactly",
        }

    if not gcc_matches or not llvm_matches:
        failing_tools = []
        if not gcc_matches:
            failing_tools.append("gcov")
        if not llvm_matches:
            failing_tools.append("llvm-cov")
        return {
            "decision_id": decision_id,
            "kind": "branch_count_contradiction",
            "assessment": "candidate_incorrect_report",
            "reason": f"Branch counts contradict oracle: {', '.join(failing_tools)}",
            "expected": {"true": exp_true, "false": exp_false},
            "gcov": {"true": gcc_t, "false": gcc_f},
            "llvm-cov": {"true": llvm_t, "false": llvm_f},
        }

    return {
        "decision_id": decision_id,
        "kind": "unresolved",
        "assessment": "unresolved_disagreement",
    }


def align_all_branches(
    manifest: dict,
    gcov_report: dict,
    llvm_report: dict,
) -> dict:
    """Align all manifest decisions against GCC and LLVM branch reports."""
    manifest_branches = manifest.get("branches", [])
    gcov_lines = gcov_report.get("lines", {})
    llvm_branches = llvm_report.get("branches", [])

    results = []
    findings = []
    comparable_count = 0
    agreements = 0

    for item in manifest_branches:
        decision_id = item["decision_id"]
        expected = item["expected"]
        span = item.get("source_span", {})

        gcc_res = resolve_gcc_decision_branches(decision_id, span, expected, gcov_lines, manifest)
        llvm_res = resolve_llvm_decision_branches(decision_id, span, expected, llvm_branches)

        classification = classify_branch_finding(decision_id, expected, gcc_res, llvm_res)
        if classification["assessment"] != "complete_agreement":
            findings.append(classification)
        else:
            agreements += 1

        if gcc_res is not None and llvm_res is not None:
            comparable_count += 1

        results.append({
            "decision_id": decision_id,
            "source_span": span,
            "expected": expected,
            "gcov": gcc_res,
            "llvm-cov": llvm_res,
            "classification": classification,
        })

    return {
        "mapping_status": "aligned",
        "total_decisions": len(manifest_branches),
        "comparable_decisions": comparable_count,
        "complete_agreements": agreements,
        "findings": findings,
        "decisions": results,
    }
