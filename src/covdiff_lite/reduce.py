"""Automated Test-Case Reduction Engine (Delta Debugging for Coverage Discrepancies).

Implements hierarchical Delta Debugging (ddmin) to minimize suspicious programs
exhibiting compiler coverage bugs or discrepancies down to 3-10 line reproducers.

Strictly preserves:
1. Valid C syntax and compilation under GCC and Clang
2. Identical functional output and exit status
3. The exact coverage discrepancy / oracle contradiction
"""

import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple


@dataclass
class ReductionResult:
    original_lines: int
    reduced_lines: int
    original_bytes: int
    reduced_bytes: int
    reduction_pct: float
    elapsed_seconds: float
    reduced_source: str
    reproduction_command: str

    def to_dict(self) -> dict:
        return {
            "original_lines": self.original_lines,
            "reduced_lines": self.reduced_lines,
            "original_bytes": self.original_bytes,
            "reduced_bytes": self.reduced_bytes,
            "reduction_pct": round(self.reduction_pct, 2),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "reproduction_command": self.reproduction_command,
        }


def default_predicate(source_text: str, expected_stdout: str, expected_exit: int = 0, compiler: Optional[str] = None) -> bool:
    """Check that source compiles with gcc/clang and runs producing expected output."""
    if compiler is None:
        compiler = shutil.which("gcc-11") or shutil.which("gcc") or shutil.which("clang-14") or shutil.which("clang") or "gcc"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        c_file = tmp_path / "test.c"
        bin_file = tmp_path / "test"
        c_file.write_text(source_text)

        compile_cmd = [compiler, "-std=c11", "-O0", "-g", str(c_file), "-o", str(bin_file)]
        res = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return False

        try:
            run_res = subprocess.run([str(bin_file)], capture_output=True, text=True, timeout=2)
            if run_res.returncode != expected_exit:
                return False
            if run_res.stdout != expected_stdout:
                return False
        except (subprocess.TimeoutExpired, OSError):
            return False

        return True


def delta_debug_lines(
    lines: List[str],
    is_interesting: Callable[[str], bool],
) -> List[str]:
    """Hierarchical ddmin algorithm on lines of code."""
    n = 2
    current = list(lines)

    while len(current) >= 2:
        length = len(current)
        step = length // n
        if step == 0:
            step = 1

        reduced = False
        # Try removing each of the n chunks
        for i in range(0, length, step):
            candidate = current[:i] + current[i + step:]
            candidate_text = "\n".join(candidate) + "\n"
            if candidate and is_interesting(candidate_text):
                current = candidate
                n = max(n - 1, 2)
                reduced = True
                break

        if not reduced:
            if n >= length:
                break
            n = min(n * 2, length)

    # 1-minimal pass: try removing each line individually
    i = 0
    while i < len(current):
        candidate = current[:i] + current[i + 1:]
        candidate_text = "\n".join(candidate) + "\n"
        if candidate and is_interesting(candidate_text):
            current = candidate
        else:
            i += 1

    return current


class ProgramReducer:
    """Reduces a program exhibiting a coverage bug or discrepancy."""

    def __init__(self, interestingness_test: Callable[[str], bool]):
        self.is_interesting = interestingness_test

    def reduce(self, source: str) -> ReductionResult:
        start_time = time.monotonic()
        original_lines = len(source.splitlines())
        original_bytes = len(source.encode("utf-8"))

        if not self.is_interesting(source):
            raise ValueError("Input source program does not satisfy the interestingness predicate!")

        # Step 1: Remove comments and empty lines if interestingness holds
        raw_lines = source.splitlines()
        clean_lines = [
            line for line in raw_lines
            if line.strip() and not line.strip().startswith("//")
        ]
        if clean_lines and self.is_interesting("\n".join(clean_lines) + "\n"):
            active_lines = clean_lines
        else:
            active_lines = raw_lines

        # Step 2: Delta debugging line minimization
        minimized_lines = delta_debug_lines(active_lines, self.is_interesting)
        reduced_source = "\n".join(minimized_lines) + "\n"

        elapsed = time.monotonic() - start_time
        reduced_lines = len(minimized_lines)
        reduced_bytes = len(reduced_source.encode("utf-8"))
        pct = ((original_bytes - reduced_bytes) / original_bytes * 100.0) if original_bytes > 0 else 0.0

        return ReductionResult(
            original_lines=original_lines,
            reduced_lines=reduced_lines,
            original_bytes=original_bytes,
            reduced_bytes=reduced_bytes,
            reduction_pct=pct,
            elapsed_seconds=elapsed,
            reduced_source=reduced_source,
            reproduction_command="gcc -O0 --coverage test.c && ./a.out && gcov -b test.c",
        )
