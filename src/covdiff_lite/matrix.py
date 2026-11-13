"""Modern Compiler Matrix & Upstream Bug Reporting Engine.

Orchestrates multi-version differential campaigns across GCC (11, 12, 13, 14)
and Clang/LLVM (14, 15, 16, 17, 18, 19).

Detects:
1. Historical Regressions: Passed in older compiler, broke in modern version
2. Resolved Flaws: Bug in older compiler, fixed in modern version
3. Persistent Bugs: Reproducible across multiple compiler generations

Generates formal upstream bug reports with minimized reproducers.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from .reduce import ProgramReducer


@dataclass
class BugReport:
    issue_id: str
    target_tool: str
    affected_versions: List[str]
    fixed_versions: List[str]
    minimal_source: str
    expected_behavior: str
    actual_behavior: str
    reproduction_script: str

    def to_markdown(self) -> str:
        affected = ", ".join(self.affected_versions) if self.affected_versions else "Unknown"
        fixed = ", ".join(self.fixed_versions) if self.fixed_versions else "None reported"
        return f"""# Upstream Bug Report: {self.issue_id}

## Environment & Affected Versions
* **Target Tool:** {self.target_tool}
* **Affected Versions:** {affected}
* **Resolved In:** {fixed}

## Summary of Discrepancy
{self.actual_behavior}

## Ground-Truth Oracle Expectation
{self.expected_behavior}

## Minimal Standalone Reproducer (Reduced)
```c
{self.minimal_source}
```

## Reproduction Steps
```bash
{self.reproduction_script}
```
"""


class CompilerMatrix:
    """Manages multi-version compiler configurations."""

    def __init__(self, toolchains: Optional[List[dict]] = None):
        self.toolchains = toolchains or [
            {"name": "gcc-11", "family": "gcc", "version": "11.4.0", "path": "gcc-11"},
            {"name": "gcc-12", "family": "gcc", "version": "12.3.0", "path": "gcc-12"},
            {"name": "gcc-13", "family": "gcc", "version": "13.2.0", "path": "gcc-13"},
            {"name": "clang-14", "family": "llvm", "version": "14.0.0", "path": "clang-14"},
            {"name": "clang-16", "family": "llvm", "version": "16.0.0", "path": "clang-16"},
            {"name": "clang-18", "family": "llvm", "version": "18.1.0", "path": "clang-18"},
        ]

    def categorize_version_evolution(
        self,
        observations_by_version: Dict[str, bool],
    ) -> str:
        """Classify how an issue behaves across compiler version progression."""
        # observations_by_version: {version: is_buggy}
        versions = list(observations_by_version.keys())
        if not versions:
            return "unknown"

        buggy_versions = [v for v, buggy in observations_by_version.items() if buggy]
        clean_versions = [v for v, buggy in observations_by_version.items() if not buggy]

        if len(buggy_versions) == len(versions):
            return "persistent_bug"
        if not buggy_versions:
            return "clean_across_matrix"

        # Check if older versions buggy and newer versions clean (fixed)
        if buggy_versions and clean_versions:
            if buggy_versions[0] < clean_versions[-1]:
                return "upstream_fixed_in_modern"
            return "regression_in_modern"

        return "unresolved_evolution"

    def generate_upstream_dossier(
        self,
        issue_id: str,
        tool: str,
        affected: List[str],
        fixed: List[str],
        source: str,
        expected_desc: str,
        actual_desc: str,
    ) -> BugReport:
        """Generate a formal upstream bug report dossier."""
        repro_sh = f"""#!/usr/bin/env bash
set -e
cat << 'EOF' > test_repro.c
{source.strip()}
EOF

echo "Compiling and running coverage with {tool}..."
if [[ "{tool}" == *"gcc"* || "{tool}" == *"gcov"* ]]; then
    gcc -O0 --coverage test_repro.c -o test_repro
    ./test_repro
    gcov -j -b test_repro.c
    cat test_repro.c.gcov
else
    clang -O0 -fprofile-instr-generate -fcoverage-mapping test_repro.c -o test_repro
    LLVM_PROFILE_FILE=test.profraw ./test_repro
    llvm-profdata merge -sparse test.profraw -o test.profdata
    llvm-cov show ./test_repro -instr-profile=test.profdata test_repro.c
fi
"""
        return BugReport(
            issue_id=issue_id,
            target_tool=tool,
            affected_versions=affected,
            fixed_versions=fixed,
            minimal_source=source,
            expected_behavior=expected_desc,
            actual_behavior=actual_desc,
            reproduction_script=repro_sh,
        )
