#!/usr/bin/env python3
"""Batch 2 Empirical Execution Orchestrator: Scaled Synthesis, Advanced Constructs,
Optimization Sweeps, and Automated Test-Case Reduction.

Executes:
1. Experiment 1: Advanced Constructs Differential Campaign (500 programs across 4 new families)
2. Experiment 2: Advanced Constructs Multi-Optimization Sweep (-O0, -Og, -O1, -O2)
3. Experiment 3: Automated Delta Debugging Minimization (ddmin) on Discrepancies
4. Experiment 4: 5,000+ Deterministic Corpus Scale & Uniqueness Benchmark
"""

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
from covdiff_lite.synthesis import (
    EXPANDED_FAMILIES,
    generate_large_scale_corpus,
    generate_synthesized_case,
)
from covdiff_lite.runners.gcc import run_gcc
from covdiff_lite.runners.llvm import run_llvm
from covdiff_lite.optimization import run_optimization_sweep
from covdiff_lite.reduce import ProgramReducer, default_predicate
from covdiff_lite.io import write_json


def run_experiment_1_advanced_campaign(output_dir: Path, tools: dict, sample_size: int = 500) -> dict:
    print("\n" + "=" * 65)
    print(f"STARTING EXPERIMENT 1: Advanced Constructs Campaign ({sample_size} cases)")
    print("=" * 65)
    exp1_dir = (output_dir / "synthesis_campaign").resolve()
    exp1_dir.mkdir(parents=True, exist_ok=True)

    print(f"Synthesizing {sample_size} diverse cases across {EXPANDED_FAMILIES}...")
    corpus = generate_large_scale_corpus(target_count=sample_size, seed=20261113)
    print(f"Generated {len(corpus)} unique programs. Running differential execution...")

    family_stats = {
        fam: {
            "tested": 0, "functional_pass": 0, "agreements": 0, "discrepancies": 0,
            "gcc_total_lines": 0, "llvm_total_lines": 0
        }
        for fam in EXPANDED_FAMILIES
    }

    discrepant_cases = []
    total_passed = 0

    for idx, (src, man) in enumerate(corpus):
        family = man["family"]
        case_id = man["case_id"]
        family_stats[family]["tested"] += 1

        case_dir = (exp1_dir / f"case_{idx}_{family}").resolve()
        case_dir.mkdir(parents=True, exist_ok=True)
        src_path = (case_dir / "case.c").resolve()
        src_path.write_text(src)

        reports = {}
        try:
            reports["gcov"] = run_gcc(src_path, case_dir / "gcc", tools, man["expected_output"])
            reports["llvm-cov"] = run_llvm(src_path, case_dir / "llvm", tools, man["expected_output"])
            family_stats[family]["functional_pass"] += 1
            total_passed += 1
        except Exception as exc:
            print(f"  [Case {idx} - {family}] Execution failed: {exc}")
            continue

        g_lines = reports.get("gcov", {}).get("lines", {})
        l_lines = reports.get("llvm-cov", {}).get("lines", {})

        family_stats[family]["gcc_total_lines"] += len(g_lines)
        family_stats[family]["llvm_total_lines"] += len(l_lines)

        # Check line agreement
        g_covered = {l for l, d in g_lines.items() if d.get("covered", False)}
        l_covered = {l for l, d in l_lines.items() if d.get("covered", False)}

        if g_covered == l_covered and len(g_lines) == len(l_lines):
            family_stats[family]["agreements"] += 1
        else:
            family_stats[family]["discrepancies"] += 1
            discrepant_cases.append({
                "case_idx": idx,
                "case_id": case_id,
                "family": family,
                "source_path": str(src_path),
                "expected_output": man["expected_output"],
                "gcc_lines": len(g_lines),
                "llvm_lines": len(l_lines),
                "gcc_covered": len(g_covered),
                "llvm_covered": len(l_covered),
                "gcc_only_lines": sorted(list(g_covered - l_covered)),
                "llvm_only_lines": sorted(list(l_covered - g_covered)),
            })

    total_tested = len(corpus)
    total_agreements = sum(s["agreements"] for s in family_stats.values())
    total_discrepancies = sum(s["discrepancies"] for s in family_stats.values())
    overall_agreement_rate = (total_agreements / total_passed * 100.0) if total_passed > 0 else 0.0

    res = {
        "total_cases_tested": total_tested,
        "functional_passed": total_passed,
        "functional_pass_rate_pct": round(total_passed / total_tested * 100.0, 2),
        "total_agreements": total_agreements,
        "total_discrepancies": total_discrepancies,
        "overall_agreement_rate_pct": round(overall_agreement_rate, 2),
        "discrepancy_rate_pct": round(100.0 - overall_agreement_rate, 2),
        "family_breakdown": family_stats,
        "sample_discrepant_cases": discrepant_cases[:10],
    }
    write_json(exp1_dir / "summary.json", res)
    print(f"Experiment 1 complete: {total_passed}/{total_tested} passed ({overall_agreement_rate:.2f}% agreement, {total_discrepancies} discrepancies)")
    return res, discrepant_cases


def run_experiment_2_advanced_optimization(output_dir: Path, tools: dict) -> dict:
    print("\n" + "=" * 65)
    print("STARTING EXPERIMENT 2: Advanced Construct Multi-Optimization Sweep")
    print("=" * 65)
    exp2_dir = (output_dir / "optimization_sweep").resolve()
    exp2_dir.mkdir(parents=True, exist_ok=True)

    levels = ["-O0", "-Og", "-O1", "-O2"]
    sweep_corpus = []
    for fam in EXPANDED_FAMILIES:
        sample = generate_large_scale_corpus(target_count=200, seed=20261113)
        fam_cases = [(s, m) for s, m in sample if m["family"] == fam][:5]  # 5 per family = 20 cases
        sweep_corpus.extend(fam_cases)

    print(f"Sweeping {len(sweep_corpus)} advanced cases across {levels}...")
    fidelity_by_opt = {"gcov": {lvl: [] for lvl in levels}, "llvm-cov": {lvl: [] for lvl in levels}}
    ghost_by_opt = {"gcov": {lvl: 0 for lvl in levels}, "llvm-cov": {lvl: 0 for lvl in levels}}
    dropped_by_opt = {"gcov": {lvl: 0 for lvl in levels}, "llvm-cov": {lvl: 0 for lvl in levels}}

    for idx, (src, man) in enumerate(sweep_corpus):
        case_dir = (exp2_dir / f"case_{idx}_{man['family']}").resolve()
        case_dir.mkdir(parents=True, exist_ok=True)
        src_path = (case_dir / "case.c").resolve()
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

    avg_fidelity = {
        tool: {lvl: round(sum(scores) / len(scores), 2) if scores else 0.0 for lvl, scores in lvl_map.items()}
        for tool, lvl_map in fidelity_by_opt.items()
    }

    res = {
        "cases_tested": len(sweep_corpus),
        "optimization_levels": levels,
        "average_fidelity_gradient": avg_fidelity,
        "cumulative_ghost_lines": ghost_by_opt,
        "cumulative_dropped_lines": dropped_by_opt,
    }
    write_json(exp2_dir / "summary.json", res)
    print(f"Experiment 2 complete: Fidelity Gradient: {avg_fidelity}")
    return res


def run_experiment_3_reduction(output_dir: Path, discrepant_cases: list) -> dict:
    print("\n" + "=" * 65)
    print("STARTING EXPERIMENT 3: Automated Delta Debugging Minimization (ddmin)")
    print("=" * 65)
    exp3_dir = (output_dir / "reductions").resolve()
    exp3_dir.mkdir(parents=True, exist_ok=True)

    reduction_records = []
    cases_to_reduce = discrepant_cases[:5]  # Minimize first 5 discrepancies

    if not cases_to_reduce:
        # Provide a synthetic candidate if no raw discrepancy occurred
        print("No raw discrepancies to reduce. Validating reducer on sample program...")
        sample_code = """#include <stdio.h>
int main(void) {
    int a = 1;
    int b = 2;
    int c = 3;
    printf("%d\\n", a + b);
    return 0;
}
"""
        reducer = ProgramReducer(lambda s: default_predicate(s, "3\n", 0))
        result = reducer.reduce(sample_code)
        rec = result.to_dict()
        rec["reduced_source"] = result.reduced_source
        reduction_records.append(rec)
    else:
        for idx, item in enumerate(cases_to_reduce):
            src_file = Path(item["source_path"])
            src_text = src_file.read_text()
            exp_stdout = item["expected_output"]["stdout"]
            exp_exit = item["expected_output"]["exit_code"]

            print(f"Reducing case {idx} ({item['case_id']}) with original {len(src_text.splitlines())} lines...")
            try:
                reducer = ProgramReducer(lambda s: default_predicate(s, exp_stdout, exp_exit))
                result = reducer.reduce(src_text)
                rec = result.to_dict()
                rec["case_id"] = item["case_id"]
                rec["family"] = item["family"]
                rec["reduced_source"] = result.reduced_source
                reduction_records.append(rec)
                (exp3_dir / f"reduced_{item['case_id']}.c").write_text(result.reduced_source)
                print(f"  Reduced from {result.original_lines} to {result.reduced_lines} lines ({result.reduction_pct:.1f}% reduction in {result.elapsed_seconds:.2f}s)")
            except Exception as exc:
                print(f"  Reduction failed: {exc}")

    avg_reduction_pct = sum(r["reduction_pct"] for r in reduction_records) / len(reduction_records) if reduction_records else 0.0
    res = {
        "cases_minimized": len(reduction_records),
        "average_reduction_pct": round(avg_reduction_pct, 2),
        "records": reduction_records,
    }
    write_json(exp3_dir / "summary.json", res)
    print(f"Experiment 3 complete: Minimized {len(reduction_records)} programs ({avg_reduction_pct:.2f}% avg reduction)")
    return res


def run_experiment_4_scale_benchmark(output_dir: Path) -> dict:
    print("\n" + "=" * 65)
    print("STARTING EXPERIMENT 4: 5,000+ Corpus Scale & Uniqueness Benchmark")
    print("=" * 65)
    exp4_dir = (output_dir / "scale_benchmark").resolve()
    exp4_dir.mkdir(parents=True, exist_ok=True)

    start_t = time.monotonic()
    target_count = 5000
    corpus = generate_large_scale_corpus(target_count=target_count, seed=20261113)
    duration = time.monotonic() - start_t

    hashes = [man["source_sha256"] for _, man in corpus]
    unique_hashes = set(hashes)
    collision_count = len(hashes) - len(unique_hashes)
    family_distribution = {}
    for _, man in corpus:
        fam = man["family"]
        family_distribution[fam] = family_distribution.get(fam, 0) + 1

    throughput = round(len(corpus) / duration, 2) if duration > 0 else 0.0

    res = {
        "corpus_target": target_count,
        "corpus_generated": len(corpus),
        "generation_time_seconds": round(duration, 3),
        "synthesis_throughput_cases_per_sec": throughput,
        "unique_sha256_count": len(unique_hashes),
        "hash_collisions": collision_count,
        "uniqueness_rate_pct": 100.0 if collision_count == 0 else round(len(unique_hashes) / len(hashes) * 100.0, 2),
        "family_distribution": family_distribution,
    }
    write_json(exp4_dir / "summary.json", res)
    print(f"Experiment 4 complete: {len(corpus)} cases synthesized in {duration:.3f}s ({throughput} cases/s, {collision_count} collisions)")
    return res


def main():
    start_total = time.monotonic()
    out_dir = (project_root / "runs" / "batch2").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    env = inspect_environment()
    if not env["ready"]:
        print("Environment not ready: " + "; ".join(env["errors"]))
        sys.exit(1)

    tools = env["tools"]
    print("Environment verified. Running Batch 2 Campaigns...")

    res1, discrepant_cases = run_experiment_1_advanced_campaign(out_dir, tools, sample_size=500)
    res2 = run_experiment_2_advanced_optimization(out_dir, tools)
    res3 = run_experiment_3_reduction(out_dir, discrepant_cases)
    res4 = run_experiment_4_scale_benchmark(out_dir)

    elapsed_total = time.monotonic() - start_total
    final_summary = {
        "batch": "Batch 2",
        "elapsed_seconds": round(elapsed_total, 2),
        "experiment_1_advanced_campaign": res1,
        "experiment_2_advanced_optimization": res2,
        "experiment_3_reduction": res3,
        "experiment_4_scale_benchmark": res4,
    }
    write_json(out_dir / "batch2_final_report.json", final_summary)

    print("\n" + "=" * 65)
    print("BATCH 2 EXECUTION COMPLETE!")
    print(f"Total Elapsed Time: {elapsed_total:.2f} seconds")
    print(f"Final Report Saved: {out_dir / 'batch2_final_report.json'}")
    print("=" * 65)


if __name__ == "__main__":
    main()
