"""Real-World Open-Source Benchmark & CI/CD Coverage Divergence Engine.

Evaluates coverage discrepancy across real-world production C code (e.g. SQLite,
Lua, zlib).

Measures:
1. Macro-level metric divergence: Overall line and branch coverage percentage delta
2. Micro-level divergence: Specific source lines covered by GCC but uncovered by Clang (and vice-versa)
3. CI/CD Threshold Impact: Evaluating whether PR coverage gates pass on GCC but fail on Clang
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class RealWorldComparison:
    target_name: str
    total_source_lines: int
    gcc_covered_lines: int
    gcc_total_lines: int
    gcc_coverage_pct: float
    llvm_covered_lines: int
    llvm_total_lines: int
    llvm_coverage_pct: float
    macro_divergence_pct: float
    gcc_only_covered: List[int]
    llvm_only_covered: List[int]
    both_covered: int
    both_uncovered: int
    ci_threshold_divergence: Dict[int, bool]  # {threshold: would_one_fail}

    def to_dict(self) -> dict:
        return {
            "target_name": self.target_name,
            "total_source_lines": self.total_source_lines,
            "gcc": {
                "covered": self.gcc_covered_lines,
                "total": self.gcc_total_lines,
                "percentage": round(self.gcc_coverage_pct, 2),
            },
            "llvm_cov": {
                "covered": self.llvm_covered_lines,
                "total": self.llvm_total_lines,
                "percentage": round(self.llvm_coverage_pct, 2),
            },
            "macro_divergence_pct": round(self.macro_divergence_pct, 2),
            "micro_discrepancies": {
                "gcc_only_covered_count": len(self.gcc_only_covered),
                "llvm_only_covered_count": len(self.llvm_only_covered),
                "gcc_only_lines_sample": self.gcc_only_covered[:20],
                "llvm_only_lines_sample": self.llvm_only_covered[:20],
            },
            "both_covered_count": self.both_covered,
            "both_uncovered_count": self.both_uncovered,
            "ci_threshold_impact": self.ci_threshold_divergence,
        }


def compare_realworld_reports(
    target_name: str,
    source_lines_count: int,
    gcc_report: dict,
    llvm_report: dict,
    ci_thresholds: Optional[List[int]] = None,
) -> RealWorldComparison:
    """Compare normalized coverage reports on real-world code."""
    if ci_thresholds is None:
        ci_thresholds = [70, 75, 80, 85, 90]

    gcc_lines = gcc_report.get("lines", {})
    llvm_lines = llvm_report.get("lines", {})

    all_line_numbers: Set[int] = set()
    for k in gcc_lines.keys():
        all_line_numbers.add(int(k))
    for k in llvm_lines.keys():
        all_line_numbers.add(int(k))

    gcc_cov = 0
    gcc_tot = len(gcc_lines)
    llvm_cov = 0
    llvm_tot = len(llvm_lines)

    gcc_only: List[int] = []
    llvm_only: List[int] = []
    both_cov = 0
    both_uncov = 0

    for num in sorted(all_line_numbers):
        k = str(num)
        g_entry = gcc_lines.get(k)
        l_entry = llvm_lines.get(k)

        g_covered = bool(g_entry and g_entry.get("state") == "reported" and g_entry.get("count", 0) > 0)
        l_covered = bool(l_entry and l_entry.get("state") == "reported" and l_entry.get("count", 0) > 0)

        if g_covered:
            gcc_cov += 1
        if l_covered:
            llvm_cov += 1

        if g_covered and l_covered:
            both_cov += 1
        elif not g_covered and not l_covered:
            both_uncov += 1
        elif g_covered and not l_covered:
            gcc_only.append(num)
        elif l_covered and not g_covered:
            llvm_only.append(num)

    gcc_pct = (gcc_cov / gcc_tot * 100.0) if gcc_tot > 0 else 0.0
    llvm_pct = (llvm_cov / llvm_tot * 100.0) if llvm_tot > 0 else 0.0
    divergence = abs(gcc_pct - llvm_pct)

    # Check CI threshold gate discrepancies
    threshold_impact = {}
    for th in ci_thresholds:
        gcc_pass = gcc_pct >= th
        llvm_pass = llvm_pct >= th
        # Conflicting gate outcome: one passes while the other fails!
        threshold_impact[th] = (gcc_pass != llvm_pass)

    return RealWorldComparison(
        target_name=target_name,
        total_source_lines=source_lines_count,
        gcc_covered_lines=gcc_cov,
        gcc_total_lines=gcc_tot,
        gcc_coverage_pct=gcc_pct,
        llvm_covered_lines=llvm_cov,
        llvm_total_lines=llvm_tot,
        llvm_coverage_pct=llvm_pct,
        macro_divergence_pct=divergence,
        gcc_only_covered=gcc_only,
        llvm_only_covered=llvm_only,
        both_covered=both_cov,
        both_uncovered=both_uncov,
        ci_threshold_divergence=threshold_impact,
    )
