"""Enterprise CI/CD Coverage Gate Verifier & Asymmetric Discrepancy Auditor.

Provides commercial/enterprise-grade CI gate auditing:
1. Evaluates whether a pull request passes or fails across different compilers (GCC vs Clang)
2. Flags 'CI Gate Flip' risks where a PR would merge on Linux GCC CI but fail on macOS/iOS Clang CI
3. Outputs GitHub Actions / GitLab CI markdown summaries and SARIF diagnostics
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
from .realworld import compare_realworld_reports
from .parsers.gcov import parse_gcov
from .parsers.llvm import parse_llvm


@dataclass
class AuditVerdict:
    target_name: str
    verdict: str  # PASS, WARNING, FLIP_RISK
    ci_gate_threshold: float
    gcc_percentage: float
    llvm_percentage: float
    macro_divergence_pct: float
    gcc_only_lines: List[int]
    llvm_only_lines: List[int]
    root_cause_categories: Dict[str, int]
    markdown_report: str

    def to_dict(self) -> dict:
        return {
            "target_name": self.target_name,
            "verdict": self.verdict,
            "ci_gate_threshold": self.ci_gate_threshold,
            "gcc_percentage": self.gcc_percentage,
            "llvm_percentage": self.llvm_percentage,
            "macro_divergence_pct": self.macro_divergence_pct,
            "gcc_only_lines_count": len(self.gcc_only_lines),
            "llvm_only_lines_count": len(self.llvm_only_lines),
            "root_cause_categories": self.root_cause_categories,
        }


def classify_line_attribution_cause(source_lines: List[str], line_no: int) -> str:
    """Heuristic classifier for compiler line reporting differences."""
    if not (1 <= line_no <= len(source_lines)):
        return "out_of_bounds"

    line_text = source_lines[line_no - 1].strip()
    if not line_text:
        return "empty_line_continuation"
    if line_text.startswith("#"):
        return "macro_preprocessor_directive"
    if line_text in ("{", "}", ");", ");"):
        return "delimiter_token_mapping"
    if line_text.startswith("if (") or line_text.startswith("if(") or "&&" in line_text or "||" in line_text:
        return "conditional_split_branch"
    if line_text.startswith("/*") or line_text.startswith("//") or line_text.endswith("*/"):
        return "comment_token_attribution"
    return "statement_execution"


def audit_coverage_gate(
    target_name: str,
    source_file: Path,
    gcc_report_path: Path,
    llvm_report_path: Path,
    ci_threshold: float = 75.0,
) -> AuditVerdict:
    """Run an enterprise audit comparing GCC vs LLVM coverage against a CI threshold."""
    source_text = source_file.read_text()
    source_lines = source_text.splitlines()

    parsed_gcc = parse_gcov(gcc_report_path, source_file)
    parsed_llvm = parse_llvm(llvm_report_path, source_file)

    comparison = compare_realworld_reports(
        target_name=target_name,
        source_lines_count=len(source_lines),
        gcc_report=parsed_gcc,
        llvm_report=parsed_llvm,
        ci_thresholds=[int(ci_threshold)]
    )

    gcc_pct = comparison.gcc_coverage_pct
    llvm_pct = comparison.llvm_coverage_pct
    macro_div = comparison.macro_divergence_pct

    gcc_pass = gcc_pct >= ci_threshold
    llvm_pass = llvm_pct >= ci_threshold

    if gcc_pass != llvm_pass:
        verdict = "FLIP_RISK"
    elif macro_div > 2.0:
        verdict = "WARNING"
    else:
        verdict = "PASS"

    gcc_only = set(comparison.gcc_only_covered)
    llvm_only = set(comparison.llvm_only_covered)

    root_causes = {}
    for l in (gcc_only | llvm_only):
        cat = classify_line_attribution_cause(source_lines, l)
        root_causes[cat] = root_causes.get(cat, 0) + 1

    # Format Markdown Report
    status_icon = "❌ **CRITICAL: CI GATE FLIP DETECTED**" if verdict == "FLIP_RISK" else \
                  "⚠️ **WARNING: HIGH COMPILER DIVERGENCE**" if verdict == "WARNING" else \
                  "✅ **PASS: CROSS-COMPILER COVERAGE CONSISTENT**"

    md = f"""# CovDiff-Lite Enterprise CI Coverage Audit: {target_name}

{status_icon}

### CI Gate Evaluation (Threshold: {ci_threshold:.1f}%)
* **GCC (`gcov`) Coverage:** **{gcc_pct:.2f}%** ({'PASS' if gcc_pass else 'FAIL'})
* **Clang (`llvm-cov`) Coverage:** **{llvm_pct:.2f}%** ({'PASS' if llvm_pass else 'FAIL'})
* **Macro Divergence:** **{macro_div:.2f}%**
* **Total Discrepant Lines:** {len(gcc_only) + len(llvm_only)} lines ({len(gcc_only)} GCC-only, {len(llvm_only)} Clang-only)

### Asymmetric Line Breakdown
| Compiler | Instrumented Lines | Covered Lines | Coverage % | Gate Status |
| :--- | :---: | :---: | :---: | :---: |
| **GCC 11** | {comparison.gcc_total_lines} | {comparison.gcc_covered_lines} | {gcc_pct:.2f}% | {'✅ PASS' if gcc_pass else '❌ FAIL'} |
| **Clang 14** | {comparison.llvm_total_lines} | {comparison.llvm_covered_lines} | {llvm_pct:.2f}% | {'✅ PASS' if llvm_pass else '❌ FAIL'} |

### Root Cause Attribution
"""
    for cat, cnt in sorted(root_causes.items(), key=lambda x: -x[1]):
        md += f"* **{cat.replace('_', ' ').title()}:** {cnt} lines\n"

    return AuditVerdict(
        target_name=target_name,
        verdict=verdict,
        ci_gate_threshold=ci_threshold,
        gcc_percentage=gcc_pct,
        llvm_percentage=llvm_pct,
        macro_divergence_pct=macro_div,
        gcc_only_lines=sorted(list(gcc_only)),
        llvm_only_lines=sorted(list(llvm_only)),
        root_cause_categories=root_causes,
        markdown_report=md,
    )
