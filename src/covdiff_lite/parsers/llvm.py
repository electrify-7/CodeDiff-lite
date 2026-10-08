"""LLVM 14 line normalization, validated against llvm-cov show.

The segment sweep follows the semantics of LLVM's LineCoverageStats:
https://github.com/llvm/llvm-project/blob/llvmorg-14.0.0/llvm/lib/ProfileData/Coverage/CoverageMapping.cpp
Only non-gap region entries and the segment carried into a line contribute.
"""

import json
from pathlib import Path


def segment_lines(segments: list, source_line_count: int) -> dict:
    previous_position = (0, 0)
    by_line = {}
    for segment in segments:
        if len(segment) != 6:
            raise ValueError("Expected LLVM 14 six-field coverage segments")
        line, column, count, has_count, entry, gap = segment
        if any(type(value) is not int for value in (line, column, count)) or min(line, column) < 1 or count < 0:
            raise ValueError("Invalid LLVM segment location or count")
        if any(type(value) is not bool for value in (has_count, entry, gap)):
            raise ValueError("Invalid LLVM segment flags")
        position = (line, column)
        if position < previous_position:
            raise ValueError("Unsorted LLVM segments")
        previous_position = position
        by_line.setdefault(line, []).append(segment)
    lines = {}
    carried = None
    last_line = min(source_line_count, max(by_line, default=0))
    for number in range(1, last_line + 1):
        current = by_line.get(number, [])
        entries = [item for item in current if item[3] and item[4] and not item[5]]
        starts_skipped = bool(current and not current[0][3] and current[0][4])
        mapped = not starts_skipped and bool(entries or (carried and carried[3]))
        if mapped:
            counts = [item[2] for item in entries]
            if carried is not None:
                counts.append(carried[2])
            count = max(counts)
            lines[str(number)] = {"state": "reported", "count": count,
                                  "covered": count > 0, "multiple_regions": len(entries) > 1}
        if current:
            carried = current[-1]
    return lines


def parse_llvm(path: Path, source: Path) -> dict:
    report = json.loads(path.read_text())
    if report.get("type") != "llvm.coverage.json.export" or report.get("version") != "2.0.1":
        raise ValueError(f"Unsupported LLVM export schema: {report.get('type')} / {report.get('version')}")
    files = [item for data in report["data"] for item in data["files"]
             if Path(item["filename"]).resolve() == source.resolve()]
    if len(files) != 1:
        raise ValueError(f"Expected one LLVM file record for {source}; found {len(files)}")
    item = files[0]
    return {
        "format_version": report["version"],
        "lines": segment_lines(item["segments"], len(source.read_text().splitlines())),
        "branches": item.get("branches", []), "expansions": item.get("expansions", []),
        "summary": item["summary"],
    }
