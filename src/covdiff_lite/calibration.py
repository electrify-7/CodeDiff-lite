"""Run reviewed fixtures and validate normalization, without bug attribution."""

import hashlib
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from .environment import inspect_environment
from .io import write_json
from .process import StageError
from .runners.gcc import run_gcc
from .runners.llvm import run_llvm


MISSING = {"state": "not_reported", "count": None, "covered": None}


def load_fixture(path: Path) -> tuple[dict, Path]:
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError(f"Unsupported fixture schema in {path}")
    case_id = manifest["case_id"]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", case_id):
        raise ValueError("Invalid case ID")
    source = (path.parent / manifest["source"]).resolve()
    if source.parent != path.parent.resolve() or source.suffix != ".c":
        raise ValueError("Fixture source must be a sibling C file")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != manifest["source_sha256"]:
        raise ValueError(f"Stale oracle/source hash: {case_id}")
    expected = manifest["expected_output"]
    if not isinstance(expected["stdout"], str) or type(expected["exit_code"]) is not int:
        raise ValueError("Invalid functional oracle")
    line_count = len(source.read_text().splitlines())
    for number, entry in manifest["lines"].items():
        if not number.isdecimal() or not 1 <= int(number) <= line_count:
            raise ValueError("Oracle line outside source")
        if type(entry["count"]) is not int or entry["count"] < 0:
            raise ValueError("Invalid oracle count")
        if entry.get("allow_elided", False) and entry["count"] != 0:
            raise ValueError("Only unreachable constant bodies may allow elision")
    return manifest, source


def compare_lines(manifest: dict, reports: dict) -> dict:
    lines = {}
    mismatches = []
    comparable = 0
    for number, expectation in manifest["lines"].items():
        row = {"expected": expectation}
        for name in ("gcov", "llvm-cov"):
            observed = reports.get(name, {}).get("lines", {}).get(number, MISSING)
            row[name] = observed.copy()
            # A failed tool is a pipeline failure, not a coverage finding.
            if name not in reports:
                row[name]["state"] = "unsupported"
                continue
            if observed["state"] == "not_reported":
                if not expectation.get("allow_elided", False):
                    mismatches.append({"tool": name, "line": int(number), "kind": "missing_mapping"})
            elif observed["count"] != expectation["count"]:
                mismatches.append({"tool": name, "line": int(number), "kind": "oracle_count",
                                   "expected": expectation["count"], "actual": observed["count"]})
        if all(row[name]["state"] == "reported" for name in ("gcov", "llvm-cov")):
            comparable += 1
        lines[number] = row
    return {"schema_version": 1, "lines": lines, "mismatches": mismatches,
            "comparable_lines": comparable,
            "branches": {"mapping_status": "not_implemented", "raw_preserved": True}}


def validate_llvm_display(report: dict, display: str) -> dict:
    """Use the primary file view; fixture counts are small and unrounded."""
    rendered = {}
    for text in display.splitlines():
        match = re.match(r"^\s*(\d+)\|([^|]*)\|", text)
        if match:
            number, count = match.groups()
            if count.strip():
                if not count.strip().isdecimal():
                    raise ValueError("Rounded LLVM display count cannot validate exact normalization")
                rendered[str(int(number))] = int(count.strip())
    normalized = {line: item["count"] for line, item in report["lines"].items()}
    summary = report["summary"]["lines"]
    errors = []
    if rendered != normalized:
        errors.append("LLVM JSON line normalization differs from llvm-cov show")
    # LLVM summaries aggregate function views, whereas the file view can also
    # display macro definition lines. Comparing these totals is only valid
    # without expansions. All line counts still undergo the display check.
    summary_scope = "function_views_with_expansions" if report["expansions"] else "file_view"
    if summary_scope == "file_view":
        if len(normalized) != summary["count"]:
            errors.append("LLVM normalized mapped-line total differs from JSON summary")
        if sum(count > 0 for count in normalized.values()) != summary["covered"]:
            errors.append("LLVM normalized covered-line total differs from JSON summary")
    return {"matched": not errors, "errors": errors,
            "mapped_lines": len(normalized), "display_mapped_lines": len(rendered),
            "summary_scope": summary_scope, "summary_counts": summary}


def run_calibration(fixtures: Path, output: Path) -> dict:
    environment = inspect_environment()
    if not environment["ready"]:
        raise ValueError("Environment is not ready: " + "; ".join(environment["errors"]))
    paths = sorted(fixtures.glob("*.json"))
    if not paths:
        raise ValueError(f"No fixture manifests in {fixtures}")
    loaded = [load_fixture(path) for path in paths]
    identifiers = [manifest["case_id"] for manifest, _ in loaded]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate fixture case IDs")
    # Never overwrite an existing run or accumulate profile data.
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "environment.json", environment)
    write_json(output / "config.json", {
        "schema_version": 1, "suite": str(fixtures.resolve()), "case_ids": identifiers,
        "started_utc": datetime.now(timezone.utc).isoformat(), "optimization": "-O0",
        "workers": 1, "purpose": "handwritten_calibration",
    })
    results = []
    started = time.monotonic()
    for manifest, original in loaded:
        case_started = time.monotonic()
        directory = output / "cases" / manifest["case_id"]
        directory.mkdir(parents=True)
        source = directory / "case.c"
        shutil.copyfile(original, source)
        write_json(directory / "manifest.json", manifest)
        reports = {}
        errors = []
        for name, runner in (("gcov", run_gcc), ("llvm-cov", run_llvm)):
            try:
                reports[name] = runner(source, directory / name, environment["tools"], manifest["expected_output"])
            except (StageError, ValueError, OSError, KeyError, TypeError) as exc:
                errors.append({"tool": name, "stage": getattr(exc, "stage", "parse"), "message": str(exc)})
        display_check = None
        if "llvm-cov" in reports:
            try:
                display_check = validate_llvm_display(reports["llvm-cov"], (directory / "llvm-cov/show.stdout").read_text())
                if not display_check["matched"]:
                    errors.append({"tool": "llvm-cov", "stage": "normalization_validation", "message": "; ".join(display_check["errors"])})
            except ValueError as exc:
                errors.append({"tool": "llvm-cov", "stage": "normalization_validation", "message": str(exc)})
        comparison = compare_lines(manifest, reports)
        write_json(directory / "normalized.json", {"schema_version": 1, "tools": reports, "oracle_comparison": comparison})
        result = {
            "case_id": manifest["case_id"], "family": manifest["family"],
            "status": "pipeline_failure" if errors else "oracle_mismatch" if comparison["mismatches"] else "calibration_pass",
            "errors": errors, "mismatches": comparison["mismatches"],
            "comparable_lines": comparison["comparable_lines"],
            "llvm_display_check": display_check,
            "duration_seconds": time.monotonic() - case_started,
        }
        write_json(directory / "result.json", result)
        results.append(result)
        print(f"{result['case_id']}: {result['status']} ({result['comparable_lines']} comparable lines)", flush=True)
        for error in errors:
            print(f"  {error['tool']} {error['stage']}: {error['message']}", flush=True)
        for mismatch in result["mismatches"]:
            print(f"  {mismatch}", flush=True)
    (output / "results.jsonl").write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in results))
    summary = {
        "schema_version": 1, "purpose": "handwritten_calibration", "cases": len(results),
        "passed": sum(item["status"] == "calibration_pass" for item in results),
        "pipeline_failures": sum(item["status"] == "pipeline_failure" for item in results),
        "oracle_mismatch_cases": sum(item["status"] == "oracle_mismatch" for item in results),
        "comparable_lines": sum(item["comparable_lines"] for item in results),
        "elapsed_seconds": time.monotonic() - started,
        "branches": "raw records retained; semantic mapping not implemented",
        "results": results,
    }
    write_json(output / "summary.json", summary)
    return summary
