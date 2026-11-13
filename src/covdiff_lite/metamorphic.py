"""Equivalence Modulo Inputs (EMI) Metamorphic Coverage Testing Engine.

Implements property-based metamorphic differential testing for C code-coverage tools:
1. Synthesizes Equivalent-Modulo-Input (EMI) variants by injecting dead-code mutations
   (dead branches, opaque predicates, uncalled functions, dead loops).
2. Metamorphic Coverage Invariants:
   - Invariant I (Functional Output Equivalence): Variant output == Baseline output.
   - Invariant II (Baseline Preservation): Original executed lines must maintain identical counts.
   - Invariant III (Zero Dead-Code Attribution): Injected dead statements MUST NEVER receive >0 counts.
     Any non-zero count is a mathematically proven false-positive compiler coverage bug (Ghost Line).
"""

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class EMIMutation:
    mutation_type: str  # dead_branch, dead_loop, opaque_predicate, dead_function
    injected_lines_range: Tuple[int, int]
    description: str


@dataclass
class EMIVariant:
    baseline_source: str
    variant_source: str
    mutations: List[EMIMutation]
    expected_dead_lines: List[int]


@dataclass
class MetamorphicTestResult:
    case_id: str
    mutation_type: str
    functional_output_match: bool
    gcc_ghost_lines: List[int]
    llvm_ghost_lines: List[int]
    gcc_preserved: bool
    llvm_preserved: bool
    passed: bool
    details: str

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "mutation_type": self.mutation_type,
            "functional_output_match": self.functional_output_match,
            "gcc_ghost_lines": self.gcc_ghost_lines,
            "llvm_ghost_lines": self.llvm_ghost_lines,
            "gcc_preserved": self.gcc_preserved,
            "llvm_preserved": self.llvm_preserved,
            "passed": self.passed,
            "details": self.details,
        }


class EMIMutator:
    """Generates Equivalent-Modulo-Inputs (EMI) mutated variants of deterministic C programs."""

    DEAD_SNIPPETS = [
        "    if (0) {\n        volatile int dead_var = 42;\n        dead_var += 100;\n    }\n",
        "    while (0) {\n        volatile int loop_dead = 1;\n        loop_dead *= 2;\n    }\n",
        "    if (1 == 2) {\n        volatile double d_dead = 3.14;\n        d_dead += 1.0;\n    }\n",
        "    for (int _dead_i = 0; _dead_i < 0; _dead_i++) {\n        volatile int unreachable_acc = _dead_i;\n    }\n",
    ]

    @classmethod
    def inject_dead_code_inside_function(cls, source_code: str, snippet_idx: int = 0) -> EMIVariant:
        """Find the start of a function body (e.g. main) and inject the dead block safely inside."""
        lines = source_code.splitlines(keepends=True)
        target_line = -1
        for idx, line in enumerate(lines):
            if "int main" in line or "{" in line:
                for j in range(idx, min(len(lines), idx + 5)):
                    if "{" in lines[j]:
                        target_line = j + 1
                        break
                if target_line != -1:
                    break

        if target_line == -1:
            target_line = max(1, len(lines) // 2)

        return cls.inject_dead_code_at_line(source_code, target_line, snippet_idx)

    @classmethod
    def inject_dead_code_at_line(cls, source_code: str, line_index: int, snippet_idx: int = 0) -> EMIVariant:
        """Inject a dead-code block immediately after line_index (1-based)."""
        lines = source_code.splitlines(keepends=True)
        if line_index < 1 or line_index > len(lines):
            line_index = min(max(1, line_index), len(lines))

        snippet = cls.DEAD_SNIPPETS[snippet_idx % len(cls.DEAD_SNIPPETS)]
        snippet_lines = snippet.splitlines(keepends=True)

        new_lines = lines[:line_index] + snippet_lines + lines[line_index:]
        variant_source = "".join(new_lines)

        injected_start = line_index + 1
        injected_end = line_index + len(snippet_lines)
        # Dead lines inside the block are the inner lines (excluding the if(0) header line itself)
        dead_inner_lines = list(range(injected_start + 1, injected_end))

        mutation = EMIMutation(
            mutation_type="dead_block_injection",
            injected_lines_range=(injected_start, injected_end),
            description=f"Injected dead block at line {line_index}",
        )

        return EMIVariant(
            baseline_source=source_code,
            variant_source=variant_source,
            mutations=[mutation],
            expected_dead_lines=dead_inner_lines,
        )

    @classmethod
    def inject_opaque_predicate(cls, source_code: str, line_index: int) -> EMIVariant:
        """Inject a mathematically opaque dead predicate: if ((x*x + 1) == 0)."""
        opaque_block = (
            "    volatile int _opq_v = 7;\n"
            "    if ((_opq_v * _opq_v + 1) == 0) {\n"
            "        volatile int _ghost_hit = 999;\n"
            "        _ghost_hit += 1;\n"
            "    }\n"
        )
        lines = source_code.splitlines(keepends=True)
        snippet_lines = opaque_block.splitlines(keepends=True)
        new_lines = lines[:line_index] + snippet_lines + lines[line_index:]
        variant_source = "".join(new_lines)

        injected_start = line_index + 1
        injected_end = line_index + len(snippet_lines)
        dead_inner_lines = [injected_start + 2, injected_start + 3]

        mutation = EMIMutation(
            mutation_type="opaque_predicate",
            injected_lines_range=(injected_start, injected_end),
            description=f"Injected quadratic opaque predicate at line {line_index}",
        )

        return EMIVariant(
            baseline_source=source_code,
            variant_source=variant_source,
            mutations=[mutation],
            expected_dead_lines=dead_inner_lines,
        )


def verify_metamorphic_invariants(
    case_id: str,
    emi_variant: EMIVariant,
    baseline_gcc_cov: Dict[int, int],
    variant_gcc_cov: Dict[int, int],
    baseline_llvm_cov: Dict[int, int],
    variant_llvm_cov: Dict[int, int],
    baseline_output: str,
    variant_output: str,
) -> MetamorphicTestResult:
    """Verify metamorphic coverage invariants across baseline and EMI mutated variant."""
    # 1. Output equivalence
    output_match = (baseline_output == variant_output)

    # 2. Invariant: Dead lines must NOT have execution count > 0
    gcc_ghosts = []
    llvm_ghosts = []
    for dead_line in emi_variant.expected_dead_lines:
        gcc_count = variant_gcc_cov.get(dead_line)
        if gcc_count is not None and gcc_count > 0:
            gcc_ghosts.append(dead_line)

        llvm_count = variant_llvm_cov.get(dead_line)
        if llvm_count is not None and llvm_count > 0:
            llvm_ghosts.append(dead_line)

    # 3. Invariant: Baseline preservation (original lines keep identical counts)
    gcc_preserved = True
    llvm_preserved = True
    # Calculate line offset shift
    shift = len(emi_variant.variant_source.splitlines()) - len(emi_variant.baseline_source.splitlines())
    inj_start = emi_variant.mutations[0].injected_lines_range[0]

    for orig_line, orig_cnt in baseline_gcc_cov.items():
        if orig_cnt > 0:
            mapped_line = orig_line if orig_line < inj_start else orig_line + shift
            if variant_gcc_cov.get(mapped_line) != orig_cnt:
                gcc_preserved = False

    for orig_line, orig_cnt in baseline_llvm_cov.items():
        if orig_cnt > 0:
            mapped_line = orig_line if orig_line < inj_start else orig_line + shift
            if variant_llvm_cov.get(mapped_line) != orig_cnt:
                llvm_preserved = False

    passed = output_match and len(gcc_ghosts) == 0 and len(llvm_ghosts) == 0 and gcc_preserved and llvm_preserved

    details = "PASSED: All metamorphic invariants satisfied." if passed else (
        f"VIOLATIONS: output_match={output_match}, gcc_ghosts={gcc_ghosts}, "
        f"llvm_ghosts={llvm_ghosts}, gcc_preserved={gcc_preserved}, llvm_preserved={llvm_preserved}"
    )

    return MetamorphicTestResult(
        case_id=case_id,
        mutation_type=emi_variant.mutations[0].mutation_type,
        functional_output_match=output_match,
        gcc_ghost_lines=gcc_ghosts,
        llvm_ghost_lines=llvm_ghosts,
        gcc_preserved=gcc_preserved,
        llvm_preserved=llvm_preserved,
        passed=passed,
        details=details,
    )
