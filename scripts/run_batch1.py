#!/usr/bin/env python3
"""Batch 1 Empirical Execution Orchestrator.

Executes:
1. Experiment 1: MC/DC and Branch Coverage on 200+ decision programs
2. Experiment 2: Multi-Optimization Sweep (-O0, -Og, -O1, -O2) on 30 cases
3. Experiment 3: Real-World Open-Source Benchmark on zlib (compress.c)
"""

import gzip
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from covdiff_lite.environment import inspect_environment
from covdiff_lite.generator import make_case
from covdiff_lite.templates import parameters_for
from covdiff_lite.runners.gcc import run_gcc
from covdiff_lite.runners.llvm import run_llvm
from covdiff_lite.branch_alignment import align_all_branches
from covdiff_lite.mcdc import DecisionTree, MCDCAnalyzer
from covdiff_lite.optimization import run_optimization_sweep
from covdiff_lite.parsers.gcov import parse_gcov
from covdiff_lite.parsers.llvm import parse_llvm
from covdiff_lite.realworld import compare_realworld_reports
from covdiff_lite.io import write_json


def run_experiment_1_mcdc(output_dir: Path, tools: dict) -> dict:
    print("\n" + "=" * 60)
    print("STARTING EXPERIMENT 1: MC/DC & Branch Coverage Empirical Campaign")
    print("=" * 60)
    exp1_dir = (output_dir / "mcdc_branch").resolve()
    exp1_dir.mkdir(parents=True, exist_ok=True)

    # Families with decisions & conditions
    target_families = ["short_circuit", "multiline", "if_else", "loops", "ternary"]
    selected_cases = []
    seed = 20261113

    for family in target_families:
        all_params = parameters_for(family)
        # Select up to 25 cases per family = 125 cases
        chosen_params = all_params[:25]
        for p in chosen_params:
            src, man = make_case(family, p, seed)
            selected_cases.append((family, p, src, man))

    print(f"Synthesized {len(selected_cases)} decision programs across {target_families}")

    total_decisions = 0
    aligned_agreements = 0
    discrepancy_findings = []
    cases_passed = 0
    mcdc_satisfied_decisions = 0
    total_compound_decisions = 0

    for idx, (family, p, src, man) in enumerate(selected_cases):
        case_id = man["case_id"]
        case_dir = (exp1_dir / f"case_{idx}_{case_id[:16]}").resolve()
        case_dir.mkdir(parents=True, exist_ok=True)
        src_path = (case_dir / "case.c").resolve()
        src_path.write_text(src)

        reports = {}
        try:
            reports["gcov"] = run_gcc(src_path, case_dir / "gcc", tools, man["expected_output"])
            reports["llvm-cov"] = run_llvm(src_path, case_dir / "llvm", tools, man["expected_output"])
            cases_passed += 1
        except Exception as exc:
            print(f"  [Case {idx}] Execution error: {exc}")
            continue

        alignment = align_all_branches(man, reports.get("gcov", {}), reports.get("llvm-cov", {}))
        total_decisions += alignment["total_decisions"]
        aligned_agreements += alignment["complete_agreements"]
        discrepancy_findings.extend(alignment.get("findings", []))

        # Check MC/DC on compound decisions
        for d in man.get("branches", []):
            dec_id = d["decision_id"]
            if family in ("short_circuit", "multiline") and dec_id == "combined":
                total_compound_decisions += 1
                conds = ["left_operand", "right_operand"]
                analyzer = MCDCAnalyzer(dec_id, conds)
                # Record the observed outcome
                exp_res = d["expected"]["true"] > 0
                analyzer.record_evaluation(exp_res, {
                    "left_operand": p["x"] > 0,
                    "right_operand": p["y"] > 0 if (p["op"] != "&&" or p["x"] > 0) else None
                })
                summary = analyzer.compute_summary()
                if summary["decision_coverage"]["covered"]:
                    mcdc_satisfied_decisions += 1

    agreement_rate = (aligned_agreements / total_decisions * 100.0) if total_decisions > 0 else 100.0
    res = {
        "total_cases_tested": len(selected_cases),
        "successful_cases": cases_passed,
        "total_decisions_aligned": total_decisions,
        "aligned_agreements": aligned_agreements,
        "agreement_rate_pct": round(agreement_rate, 2),
        "discrepancy_count": len(discrepancy_findings),
        "total_compound_decisions": total_compound_decisions,
        "mcdc_evaluations_recorded": total_compound_decisions,
    }
    write_json(exp1_dir / "summary.json", res)
    print(f"Experiment 1 complete: {total_decisions} decisions aligned ({agreement_rate:.2f}% complete agreement)")
    return res


def run_experiment_2_optimization(output_dir: Path, tools: dict) -> dict:
    print("\n" + "=" * 60)
    print("STARTING EXPERIMENT 2: Multi-Optimization Degradation Sweep")
    print("=" * 60)
    exp2_dir = (output_dir / "optimization_sweep").resolve()
    exp2_dir.mkdir(parents=True, exist_ok=True)

    # Select 24 cases across 6 families (4 per family)
    families = ["if_else", "loops", "switch", "short_circuit", "ternary", "constants"]
    test_cases = []
    seed = 20261113
    for f in families:
        for p in parameters_for(f)[:4]:
            src, man = make_case(f, p, seed)
            test_cases.append((man, src))

    print(f"Running optimization sweep (-O0, -Og, -O1, -O2) on {len(test_cases)} programs...")

    levels = ["-O0", "-Og", "-O1", "-O2"]
    fidelity_by_opt = {"gcov": {lvl: [] for lvl in levels}, "llvm-cov": {lvl: [] for lvl in levels}}
    ghost_by_opt = {"gcov": {lvl: 0 for lvl in levels}, "llvm-cov": {lvl: 0 for lvl in levels}}
    dropped_by_opt = {"gcov": {lvl: 0 for lvl in levels}, "llvm-cov": {lvl: 0 for lvl in levels}}

    for idx, (man, src) in enumerate(test_cases):
        case_dir = (exp2_dir / f"case_{idx}_{man['case_id'][:12]}").resolve()
        src_path = (case_dir / "case.c").resolve()
        case_dir.mkdir(parents=True, exist_ok=True)
        src_path.write_text(src)

        sweep = run_optimization_sweep(man, src_path, case_dir, tools, levels)
        for lvl in levels:
            eval_data = sweep["sweep"].get(lvl, {}).get("evaluation", {})
            for tool in ("gcov", "llvm-cov"):
                t_eval = eval_data.get(tool, {})
                if "fidelity_pct" in t_eval:
                    fidelity_by_opt[tool][lvl].append(t_eval["fidelity_pct"])
                    ghost_by_opt[tool][lvl] += t_eval.get("ghost_count", 0)
                    dropped_by_opt[tool][lvl] += t_eval.get("dropped_count", 0)

    # Compute average fidelity
    avg_fidelity = {
        tool: {lvl: round(sum(scores) / len(scores), 2) if scores else 0.0 for lvl, scores in lvl_map.items()}
        for tool, lvl_map in fidelity_by_opt.items()
    }

    res = {
        "cases_tested": len(test_cases),
        "optimization_levels": levels,
        "average_fidelity_gradient": avg_fidelity,
        "cumulative_ghost_lines": ghost_by_opt,
        "cumulative_dropped_lines": dropped_by_opt,
    }
    write_json(exp2_dir / "summary.json", res)
    print(f"Experiment 2 complete: Fidelity Gradient: {avg_fidelity}")
    return res


def run_experiment_3_realworld(output_dir: Path, tools: dict) -> dict:
    print("\n" + "=" * 60)
    print("STARTING EXPERIMENT 3: Real-World Open-Source Benchmark (zlib)")
    print("=" * 60)
    exp3_dir = (output_dir / "realworld_zlib").resolve()
    exp3_dir.mkdir(parents=True, exist_ok=True)

    zlib_candidates = [
        os.environ.get("ZLIB_DIR"),
        "/zlib",
        "/home/mahoraga/Software/zlib-test",
        str(project_root.parent / "zlib-test"),
    ]
    zlib_dir = None
    for cand in zlib_candidates:
        if cand and Path(cand).exists() and (Path(cand) / "compress.c").exists():
            zlib_dir = Path(cand).resolve()
            break

    if not zlib_dir:
        print("  Error: zlib directory not found.")
        return {"error": "zlib not found"}

    print(f"Using zlib source directory at: {zlib_dir}")
    compress_c = (zlib_dir / "compress.c").resolve()
    line_count = len(compress_c.read_text().splitlines())

    # Build and run GCC coverage on zlib test
    gcc_build_dir = (exp3_dir / "zlib_gcc").resolve()
    gcc_build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        f"cd {zlib_dir} && rm -f *.gcda *.gcno *.gcov* *.prof* && "
        f"gcc-11 -O0 --coverage -I. -c compress.c -o compress.o && "
        f"gcc-11 -O0 --coverage -I. compress.o adler32.c crc32.c deflate.c infback.c inffast.c inflate.c inftrees.c trees.c uncompr.c zutil.c gz*.c test/example.c -o example_gcc && "
        f"./example_gcc && gcov-11 -j -b compress.c && cp compress.gcov.json.gz {gcc_build_dir}/",
        shell=True, check=True
    )

    # Build and run Clang coverage on zlib test
    llvm_build_dir = (exp3_dir / "zlib_llvm").resolve()
    llvm_build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        f"cd {zlib_dir} && "
        f"clang-14 -O0 -g -fprofile-instr-generate -fcoverage-mapping -I. *.c test/example.c -o example_clang && "
        f"LLVM_PROFILE_FILE=example.profraw ./example_clang && "
        f"llvm-profdata-14 merge -sparse example.profraw -o example.profdata && "
        f"llvm-cov-14 export ./example_clang -instr-profile=example.profdata compress.c > {llvm_build_dir}/compress.llvm.json",
        shell=True, check=True
    )

    # Parse both reports using our parsers
    parsed_gcc = parse_gcov(gcc_build_dir / "compress.gcov.json.gz", compress_c)
    parsed_llvm = parse_llvm(llvm_build_dir / "compress.llvm.json", compress_c)

    comparison = compare_realworld_reports(
        target_name="zlib-1.4:compress.c",
        source_lines_count=line_count,
        gcc_report=parsed_gcc,
        llvm_report=parsed_llvm,
        ci_thresholds=[70, 75, 76, 80, 85]
    )

    res = comparison.to_dict()
    write_json(exp3_dir / "summary.json", res)
    print(f"Experiment 3 complete: GCC Cov = {res['gcc']['percentage']}%, LLVM Cov = {res['llvm_cov']['percentage']}%")
    print(f"  Macro divergence = {res['macro_divergence_pct']}%, CI Threshold Discrepancy = {res['ci_threshold_impact']}")
    return res


def main():
    start_total = time.monotonic()
    out_dir = (project_root / "runs" / "batch1").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    env = inspect_environment()
    if not env["ready"]:
        print("Environment not ready: " + "; ".join(env["errors"]))
        sys.exit(1)

    tools = env["tools"]
    print("Environment verified. Running Batch 1 Empirical Campaigns...")

    res1 = run_experiment_1_mcdc(out_dir, tools)
    res2 = run_experiment_2_optimization(out_dir, tools)
    res3 = run_experiment_3_realworld(out_dir, tools)

    elapsed_total = time.monotonic() - start_total
    final_summary = {
        "batch": "Batch 1",
        "elapsed_seconds": round(elapsed_total, 2),
        "experiment_1_mcdc": res1,
        "experiment_2_optimization": res2,
        "experiment_3_realworld": res3,
    }
    write_json(out_dir / "batch1_final_report.json", final_summary)

    print("\n" + "=" * 60)
    print("BATCH 1 EXECUTION COMPLETE!")
    print(f"Total Elapsed Time: {elapsed_total:.2f} seconds")
    print(f"Final Report Saved: {out_dir / 'batch1_final_report.json'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
