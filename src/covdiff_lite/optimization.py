"""Multi-Optimization Pipeline and Coverage Degradation Analysis.

Evaluates coverage reporting across compiler optimization tiers:
- -O0: Baseline (no optimization)
- -Og: Optimize for debugging
- -O1: Basic optimization
- -O2: Standard production optimization
- -Os: Optimize for binary size

Analyzes:
1. False-Positive / "Ghost" lines on unexecuted code
2. Dropped / missing coverage on executed statements
3. Divergence gradient between GCC and Clang as optimizations increase
"""

from pathlib import Path
from typing import Dict, List, Optional
from .calibration import execute_case
from .compare import compare_observations

OPTIMIZATION_LEVELS = ["-O0", "-Og", "-O1", "-O2", "-Os"]


def evaluate_statement_degradation(
    manifest: dict,
    report: dict,
    tool_name: str,
    opt_level: str,
) -> dict:
    """Analyze statement coverage accuracy under optimization for a single tool."""
    lines = manifest.get("lines", {})
    tool_lines = report.get("lines", {})

    total_statements = len(lines)
    matching = 0
    ghost_lines = []     # expected 0, but reported > 0
    dropped_lines = []   # expected > 0, but reported 0 or missing
    count_mismatches = []

    for line_str, expected in lines.items():
        exp_count = expected.get("count", 0)
        obs = tool_lines.get(line_str)

        if obs is None or obs.get("state") != "reported":
            # Missing from coverage report
            if exp_count > 0:
                dropped_lines.append({
                    "line": int(line_str),
                    "statement_id": expected.get("statement_id"),
                    "expected": exp_count,
                    "reported": None,
                    "reason": "dropped_by_compiler_pass",
                })
            else:
                # Expected 0 and missing: considered non-ghost (unmapped)
                matching += 1
            continue

        rep_count = obs.get("count", 0)

        if exp_count == 0 and rep_count > 0:
            ghost_lines.append({
                "line": int(line_str),
                "statement_id": expected.get("statement_id"),
                "expected": 0,
                "reported": rep_count,
                "reason": "ghost_coverage_on_dead_code",
            })
        elif exp_count > 0 and rep_count == 0:
            dropped_lines.append({
                "line": int(line_str),
                "statement_id": expected.get("statement_id"),
                "expected": exp_count,
                "reported": 0,
                "reason": "executed_code_reported_zero",
            })
        elif exp_count == rep_count:
            matching += 1
        else:
            count_mismatches.append({
                "line": int(line_str),
                "statement_id": expected.get("statement_id"),
                "expected": exp_count,
                "reported": rep_count,
                "reason": "inaccurate_count_after_optimization",
            })

    fidelity = (matching / total_statements * 100.0) if total_statements > 0 else 100.0
    return {
        "tool": tool_name,
        "opt_level": opt_level,
        "total_statements": total_statements,
        "matching_statements": matching,
        "fidelity_pct": round(fidelity, 2),
        "ghost_count": len(ghost_lines),
        "ghost_lines": ghost_lines,
        "dropped_count": len(dropped_lines),
        "dropped_lines": dropped_lines,
        "count_mismatches": count_mismatches,
    }


def run_optimization_sweep(
    manifest: dict,
    source: Path,
    output_dir: Path,
    tools: dict,
    levels: Optional[List[str]] = None,
) -> dict:
    """Execute a case across multiple optimization levels and measure degradation."""
    if levels is None:
        levels = OPTIMIZATION_LEVELS

    output_dir.mkdir(parents=True, exist_ok=True)
    sweep_results = {}
    fidelity_gradient = {"gcov": {}, "llvm-cov": {}}

    for opt in levels:
        opt_dir = output_dir / f"opt_{opt.replace('-', '')}"
        exec_result = execute_case(manifest, source, opt_dir, tools, opt_level=opt)
        reports = exec_result.get("reports", {})

        opt_eval = {}
        for tool_name in ("gcov", "llvm-cov"):
            if tool_name in reports:
                tool_rep = reports[tool_name]
                degrad = evaluate_statement_degradation(manifest, tool_rep, tool_name, opt)
                opt_eval[tool_name] = degrad
                fidelity_gradient[tool_name][opt] = degrad["fidelity_pct"]
            else:
                opt_eval[tool_name] = {"error": "Tool failed or unavailable at this optimization level"}
                fidelity_gradient[tool_name][opt] = None

        sweep_results[opt] = {
            "evaluation": opt_eval,
            "errors": exec_result.get("errors", []),
        }

    return {
        "case_id": manifest.get("case_id"),
        "levels": levels,
        "fidelity_gradient": fidelity_gradient,
        "sweep": sweep_results,
    }
