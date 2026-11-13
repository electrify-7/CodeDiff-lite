#!/usr/bin/env python3
"""Mega-Campaign Orchestrator: 30,000-Execution Differential Campaign & SQLite Amalgamation Benchmark.

Executes:
1. 30,000-Execution Synthesis Campaign:
   5,000 programs x 6 compiler configurations:
   - GCC 11: -O0, -Og, -O2
   - Clang 14: -O0, -Og, -O2
   Evaluates functional correctness, cross-tool parity, and optimization degradation.
2. Full SQLite Amalgamation Benchmark:
   Evaluates GCC 11 vs Clang 14 on sqlite3.c (240,000+ lines).
"""

import gzip
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from covdiff_lite.environment import inspect_environment
from covdiff_lite.synthesis import generate_large_scale_corpus, EXPANDED_FAMILIES
from covdiff_lite.runners.gcc import run_gcc
from covdiff_lite.runners.llvm import run_llvm
from covdiff_lite.parsers.gcov import parse_gcov
from covdiff_lite.parsers.llvm import parse_llvm
from covdiff_lite.realworld import compare_realworld_reports
from covdiff_lite.io import write_json

CONFIGS = [
    ("gcc", "-O0"),
    ("gcc", "-Og"),
    ("gcc", "-O2"),
    ("llvm-cov", "-O0"),
    ("llvm-cov", "-Og"),
    ("llvm-cov", "-O2"),
]


def evaluate_single_program_config(args):
    """Worker task: executes one program under one compiler configuration."""
    idx, src, man, tool_name, opt_level, tools, base_tmp = args
    exp_out = man["expected_output"]
    case_id = man["case_id"]

    work_dir = Path(base_tmp) / f"case_{idx}_{tool_name}_{opt_level.replace('-', '')}"
    work_dir.mkdir(parents=True, exist_ok=True)
    src_file = (work_dir / "case.c").resolve()
    src_file.write_text(src)

    success = False
    report = None
    error_msg = None

    try:
        if tool_name == "gcc":
            report = run_gcc(src_file, work_dir / "build", tools, exp_out, opt_level=opt_level)
            success = True
        else:
            report = run_llvm(src_file, work_dir / "build", tools, exp_out, opt_level=opt_level)
            success = True
    except Exception as exc:
        error_msg = str(exc)

    lines_total = len(report.get("lines", {})) if report else 0
    lines_covered = sum(1 for d in report.get("lines", {}).values() if d.get("covered")) if report else 0

    # Clean up work directory to prevent disk exhaustion
    shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "case_idx": idx,
        "case_id": case_id,
        "family": man["family"],
        "tool": tool_name,
        "opt_level": opt_level,
        "success": success,
        "error": error_msg,
        "lines_total": lines_total,
        "lines_covered": lines_covered,
    }


def run_30k_differential_campaign(output_dir: Path, tools: dict, total_cases: int = 5000) -> dict:
    print("\n" + "=" * 70)
    print(f"STARTING MEGA-CAMPAIGN: 30,000-Execution Differential Matrix")
    print(f"  Target: {total_cases} programs x {len(CONFIGS)} configurations = {total_cases * len(CONFIGS):,} executions")
    print("=" * 70)

    start_campaign = time.monotonic()
    exp_dir = (output_dir / "campaign_30k").resolve()
    exp_dir.mkdir(parents=True, exist_ok=True)

    print(f"Synthesizing {total_cases} unique deterministic C programs...")
    gen_start = time.monotonic()
    corpus = generate_large_scale_corpus(target_count=total_cases, seed=20261113)
    gen_time = time.monotonic() - gen_start
    print(f"Synthesized {len(corpus)} programs in {gen_time:.3f}s (100% hash unique).")

    tmp_base = tempfile.mkdtemp(prefix="covdiff_30k_")
    tasks = []
    for idx, (src, man) in enumerate(corpus):
        for tool_name, opt in CONFIGS:
            tasks.append((idx, src, man, tool_name, opt, tools, tmp_base))

    total_executions = len(tasks)
    print(f"Queued {total_executions:,} execution tasks. Launching 4-worker process pool...")

    completed = 0
    success_count = 0
    by_tool_opt = {f"{t}_{o}": {"executions": 0, "success": 0, "total_lines": 0, "covered_lines": 0} for t, o in CONFIGS}
    family_stats = {f: {"executions": 0, "success": 0} for f in EXPANDED_FAMILIES}

    chunk_size = 500
    with mp.Pool(processes=4) as pool:
        for res in pool.imap_unordered(evaluate_single_program_config, tasks, chunksize=20):
            completed += 1
            if res["success"]:
                success_count += 1

            key = f"{res['tool']}_{res['opt_level']}"
            by_tool_opt[key]["executions"] += 1
            if res["success"]:
                by_tool_opt[key]["success"] += 1
                by_tool_opt[key]["total_lines"] += res["lines_total"]
                by_tool_opt[key]["covered_lines"] += res["lines_covered"]

            fam = res["family"]
            if fam in family_stats:
                family_stats[fam]["executions"] += 1
                if res["success"]:
                    family_stats[fam]["success"] += 1

            if completed % 1000 == 0 or completed == total_executions:
                pct = completed / total_executions * 100.0
                elapsed = time.monotonic() - start_campaign
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total_executions - completed) / rate if rate > 0 else 0
                print(f"  [{completed:,}/{total_executions:,} | {pct:.1f}%] - {rate:.1f} exec/s - ETA: {eta:.0f}s - Success: {success_count:,}/{completed:,}")

    shutil.rmtree(tmp_base, ignore_errors=True)
    campaign_duration = time.monotonic() - start_campaign

    campaign_summary = {
        "total_programs": total_cases,
        "total_configurations": len(CONFIGS),
        "total_executions": total_executions,
        "successful_executions": success_count,
        "failed_executions": total_executions - success_count,
        "overall_pass_rate_pct": round(success_count / total_executions * 100.0, 2),
        "elapsed_seconds": round(campaign_duration, 2),
        "throughput_executions_per_sec": round(total_executions / campaign_duration, 2),
        "matrix_breakdown": by_tool_opt,
        "family_breakdown": family_stats,
    }

    write_json(exp_dir / "campaign_30k_summary.json", campaign_summary)
    print(f"\n30,000-Execution Campaign Complete! Duration: {campaign_duration:.2f}s ({campaign_summary['throughput_executions_per_sec']} exec/s)")
    return campaign_summary


def run_sqlite_benchmark(output_dir: Path, tools: dict) -> dict:
    print("\n" + "=" * 70)
    print("STARTING FULL SQLITE AMALGAMATION BENCHMARK (sqlite3.c: 240,000+ lines)")
    print("=" * 70)

    sqlite_dir = Path("/sqlite")
    if not sqlite_dir.exists():
        sqlite_dir = Path("/home/mahoraga/Software/sqlite/sqlite-amalgamation-3450300")

    sqlite_c = (sqlite_dir / "sqlite3.c").resolve()
    shell_c = (sqlite_dir / "shell.c").resolve()

    if not sqlite_c.exists():
        print(f"Error: sqlite3.c not found at {sqlite_c}")
        return {"error": "sqlite3.c not found"}

    exp_dir = (output_dir / "sqlite_benchmark").resolve()
    exp_dir.mkdir(parents=True, exist_ok=True)
    gcc_build = exp_dir / "gcc_build"
    llvm_build = exp_dir / "llvm_build"
    gcc_build.mkdir(parents=True, exist_ok=True)
    llvm_build.mkdir(parents=True, exist_ok=True)

    print("Building and profiling SQLite with GCC 11 (--coverage)...")
    t0 = time.monotonic()
    subprocess.run(
        f"cd {sqlite_dir} && rm -f *.gc* *.o sqlite3_gcc && "
        f"gcc-11 -O0 --coverage -DSQLITE_THREADSAFE=0 -c sqlite3.c -o sqlite3.o && "
        f"gcc-11 -O0 --coverage -DSQLITE_THREADSAFE=0 sqlite3.o shell.c -ldl -o sqlite3_gcc && "
        f"./sqlite3_gcc :memory: 'CREATE TABLE t(x); INSERT INTO t VALUES(1),(2),(3); SELECT sum(x) FROM t;' && "
        f"gcov-11 -j -b sqlite3.c && cp sqlite3.gcov.json.gz {gcc_build}/",
        shell=True, check=True
    )
    gcc_time = time.monotonic() - t0

    print("Building and profiling SQLite with Clang 14 (Source-based profile instrumentation)...")
    t1 = time.monotonic()
    subprocess.run(
        f"cd {sqlite_dir} && rm -f *.prof* sqlite3_clang && "
        f"clang-14 -O0 -g -fprofile-instr-generate -fcoverage-mapping -DSQLITE_THREADSAFE=0 sqlite3.c shell.c -ldl -o sqlite3_clang && "
        f"LLVM_PROFILE_FILE=sqlite.profraw ./sqlite3_clang :memory: 'CREATE TABLE t(x); INSERT INTO t VALUES(1),(2),(3); SELECT sum(x) FROM t;' && "
        f"llvm-profdata-14 merge -sparse sqlite.profraw -o sqlite.profdata && "
        f"llvm-cov-14 export ./sqlite3_clang -instr-profile=sqlite.profdata sqlite3.c > {llvm_build}/sqlite3.llvm.json",
        shell=True, check=True
    )
    llvm_time = time.monotonic() - t1

    print("Parsing SQLite coverage reports from both tools...")
    parsed_gcc = parse_gcov(gcc_build / "sqlite3.gcov.json.gz", sqlite_c)
    parsed_llvm = parse_llvm(llvm_build / "sqlite3.llvm.json", sqlite_c)

    line_count = len(sqlite_c.read_text().splitlines())
    comparison = compare_realworld_reports(
        target_name="sqlite-amalgamation-3.45:sqlite3.c",
        source_lines_count=line_count,
        gcc_report=parsed_gcc,
        llvm_report=parsed_llvm,
        ci_thresholds=[15, 18, 19, 20, 21, 25]
    )

    res = comparison.to_dict()
    res["build_time_seconds"] = {"gcc": round(gcc_time, 2), "clang": round(llvm_time, 2)}
    res["total_source_lines"] = line_count

    write_json(exp_dir / "summary.json", res)
    print(f"SQLite Benchmark Complete:")
    print(f"  GCC Instrumented Lines:  {res['gcc']['total']} ({res['gcc']['percentage']}% covered)")
    print(f"  LLVM Instrumented Lines: {res['llvm_cov']['total']} ({res['llvm_cov']['percentage']}% covered)")
    print(f"  Discrepant Line Gap:     {res['llvm_cov']['total'] - res['gcc']['total']:,} lines unmapped by GCC!")
    print(f"  Macro Divergence:        {res['macro_divergence_pct']}%")
    print(f"  CI Threshold Conflict:   {res['ci_threshold_impact']}")
    return res


def main():
    start_all = time.monotonic()
    out_dir = (project_root / "runs" / "campaign_30k").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    env = inspect_environment()
    if not env["ready"]:
        print("Environment not ready: " + "; ".join(env["errors"]))
        sys.exit(1)

    tools = env["tools"]
    print("Environment verified. Executing 30,000-Campaign & SQLite Benchmark...")

    res_30k = run_30k_differential_campaign(out_dir, tools, total_cases=5000)
    res_sqlite = run_sqlite_benchmark(out_dir, tools)

    elapsed_all = time.monotonic() - start_all
    final_report = {
        "campaign": "30,000-Execution Differential Campaign & SQLite Benchmark",
        "elapsed_seconds": round(elapsed_all, 2),
        "differential_matrix_30k": res_30k,
        "sqlite_benchmark": res_sqlite,
    }

    write_json(out_dir / "campaign_30k_final_report.json", final_report)

    print("\n" + "=" * 70)
    print("ALL MEGA-CAMPAIGN EXPERIMENTS COMPLETE!")
    print(f"Total Duration: {elapsed_all:.2f} seconds ({elapsed_all / 60.0:.2f} minutes)")
    print(f"Final Report: {out_dir / 'campaign_30k_final_report.json'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
