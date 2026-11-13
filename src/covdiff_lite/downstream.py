"""Downstream Software Engineering Impact: Spectrum-Based Fault Localization (SBFL).

Evaluates the practical harm of coverage tool errors on automated debugging:
Runs Ochiai and Tarantula fault localization algorithms on test execution spectra
derived from GCC vs Clang coverage traces, and measures whether coverage divergence
distorts suspiciousness rankings and fault localization accuracy (Top-1, Top-5 rank shifts).
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class SBFLRanking:
    statement: str
    suspiciousness: float
    rank: int


@dataclass
class DownstreamImpactResult:
    formula: str
    gcc_rankings: List[SBFLRanking]
    llvm_rankings: List[SBFLRanking]
    target_fault_statement: str
    gcc_fault_rank: int
    llvm_fault_rank: int
    rank_shift: int
    ranking_inverted: bool

    def to_dict(self) -> dict:
        return {
            "formula": self.formula,
            "target_fault_statement": self.target_fault_statement,
            "gcc_fault_rank": self.gcc_fault_rank,
            "llvm_fault_rank": self.llvm_fault_rank,
            "rank_shift": self.rank_shift,
            "ranking_inverted": self.ranking_inverted,
            "gcc_top3": [r.statement for r in self.gcc_rankings[:3]],
            "llvm_top3": [r.statement for r in self.llvm_rankings[:3]],
        }


def compute_ochiai(ef: int, ep: int, nf: int, np: int) -> float:
    """Ochiai coefficient: ef / sqrt((ef + nf) * (ef + ep))."""
    total_failed = ef + nf
    if total_failed == 0 or (ef + ep) == 0:
        return 0.0
    denominator = math.sqrt(total_failed * (ef + ep))
    return ef / denominator if denominator > 0 else 0.0


def compute_tarantula(ef: int, ep: int, nf: int, np: int) -> float:
    """Tarantula coefficient: (ef / (ef + nf)) / ((ef / (ef + nf)) + (ep / (ep + np)))."""
    total_failed = ef + nf
    total_passed = ep + np
    if total_failed == 0:
        return 0.0
    fail_ratio = ef / total_failed
    pass_ratio = (ep / total_passed) if total_passed > 0 else 0.0
    total_ratio = fail_ratio + pass_ratio
    return (fail_ratio / total_ratio) if total_ratio > 0 else 0.0


def rank_statements(scores: Dict[str, float]) -> List[SBFLRanking]:
    """Sort statements by descending suspiciousness score and assign ranks."""
    sorted_items = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    rankings = []
    current_rank = 1
    for stmt, score in sorted_items:
        rankings.append(SBFLRanking(statement=stmt, suspiciousness=round(score, 4), rank=current_rank))
        current_rank += 1
    return rankings


def evaluate_sbfl_impact(
    spectra_gcc: List[Tuple[Dict[str, bool], bool]],
    spectra_llvm: List[Tuple[Dict[str, bool], bool]],
    fault_statement: str,
    formula: str = "ochiai",
) -> DownstreamImpactResult:
    """Compute SBFL rankings using spectra from GCC vs Clang and measure rank shift.

    spectra format: list of (coverage_dict, test_passed)
    coverage_dict: {statement_id: was_executed_bool}
    test_passed: bool (True if passing test, False if failing)
    """
    calc_func = compute_ochiai if formula.lower() == "ochiai" else compute_tarantula

    def get_rankings(spectra: List[Tuple[Dict[str, bool], bool]]) -> List[SBFLRanking]:
        # Collect statements
        all_stmts = set()
        for cov, _ in spectra:
            all_stmts.update(cov.keys())

        total_failed = sum(1 for _, passed in spectra if not passed)
        total_passed = sum(1 for _, passed in spectra if passed)

        scores = {}
        for s in all_stmts:
            ef = sum(1 for cov, passed in spectra if not passed and cov.get(s, False))
            ep = sum(1 for cov, passed in spectra if passed and cov.get(s, False))
            nf = total_failed - ef
            np = total_passed - ep
            scores[s] = calc_func(ef, ep, nf, np)

        return rank_statements(scores)

    gcc_ranked = get_rankings(spectra_gcc)
    llvm_ranked = get_rankings(spectra_llvm)

    gcc_rank = next((r.rank for r in gcc_ranked if r.statement == fault_statement), len(gcc_ranked) + 1)
    llvm_rank = next((r.rank for r in llvm_ranked if r.statement == fault_statement), len(llvm_ranked) + 1)

    rank_shift = abs(gcc_rank - llvm_rank)
    inverted = (gcc_rank == 1 and llvm_rank > 1) or (llvm_rank == 1 and gcc_rank > 1)

    return DownstreamImpactResult(
        formula=formula,
        gcc_rankings=gcc_ranked,
        llvm_rankings=llvm_ranked,
        target_fault_statement=fault_statement,
        gcc_fault_rank=gcc_rank,
        llvm_fault_rank=llvm_rank,
        rank_shift=rank_shift,
        ranking_inverted=inverted,
    )
