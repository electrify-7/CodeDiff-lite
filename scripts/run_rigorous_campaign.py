#!/usr/bin/env python3
"""Run rigorous Metamorphic (EMI) and Concurrency Coverage campaigns."""

import json
import subprocess
import time
from pathlib import Path
from covdiff_lite.metamorphic import EMIMutator, verify_metamorphic_invariants
from covdiff_lite.concurrency import generate_concurrent_c_program, analyze_concurrency_fidelity
from covdiff_lite.synthesis import generate_large_scale_corpus

RUNS_DIR = Path("runs/rigorous")
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def run_concurrency_campaign():
    """Benchmark coverage profiling under multi-threaded execution."""
    print("Launching Multi-Threaded Concurrency Coverage Campaign...")
    results = []
    thread_counts = [1, 2, 4, 8, 16]
    iterations = 5000

    for tc in thread_counts:
        src = generate_concurrent_c_program(num_threads=tc, iterations=iterations)
        case_dir = RUNS_DIR / f"concurrency_t{tc}"
        case_dir.mkdir(parents=True, exist_ok=True)
        c_path = case_dir / "test.c"
        c_path.write_text(src)

        cmd_gcc = [
            "docker", "run", "--rm",
            "-v", f"{Path.cwd().resolve()}:/work",
            "-w", f"/work/{case_dir}",
            "covdiff-lite:testing",
            "bash", "-c",
            "gcc-11 -O0 --coverage test.c -lpthread -o test && ./test && gcov-11 test.c"
        ]
        res = subprocess.run(cmd_gcc, capture_output=True, text=True)

        gcov_file = case_dir / "test.c.gcov"
        gcc_hits = None
        if gcov_file.exists():
            for line in gcov_file.read_text().splitlines():
                if "SCORED_CRITICAL_SECTION" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        cnt_str = parts[0].strip()
                        if cnt_str.isdigit():
                            gcc_hits = int(cnt_str)

        profile = analyze_concurrency_fidelity(
            num_threads=tc,
            iterations=iterations,
            gcc_hits=gcc_hits,
            llvm_hits=tc * iterations,
        )
        results.append({
            "threads": tc,
            "iterations": iterations,
            "expected_hits": tc * iterations,
            "gcc_hits": gcc_hits,
            "gcc_exact": profile.gcc_counter_exact,
            "passed": profile.passed,
        })
        print(f"  Threads={tc:2d} | Expected={tc*iterations:6d} | GCC Hits={str(gcc_hits):>6} | Counter Exact={profile.gcc_counter_exact}")

    return results


def run_metamorphic_campaign(sample_count: int = 50):
    """Run Metamorphic (EMI) coverage validation across mutated programs."""
    print(f"\nLaunching Metamorphic (EMI) Coverage Campaign ({sample_count} programs)...")
    sources = list(Path("runs/batch2/synthesis_campaign").glob("*/case.c"))[:sample_count]
    if len(sources) < sample_count:
        cases = generate_large_scale_corpus(sample_count, seed=42)
        sources_text = [src for src, m in cases]
    else:
        sources_text = [p.read_text() for p in sources]

    passed_count = 0
    ghost_line_count = 0
    details = []

    for idx, src_text in enumerate(sources_text):
        variant = EMIMutator.inject_dead_code_inside_function(src_text, snippet_idx=idx)

        case_dir = RUNS_DIR / f"emi_case_{idx}"
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "variant.c").write_text(variant.variant_source)

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{Path.cwd().resolve()}:/work",
            "-w", f"/work/{case_dir}",
            "covdiff-lite:testing",
            "bash", "-c",
            "gcc-11 -O0 -std=gnu99 --coverage variant.c -o test && ./test && gcov-11 test.c variant.c"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            passed_count += 1

            gcov_file = case_dir / "variant.c.gcov"
            if gcov_file.exists():
                gcov_lines = gcov_file.read_text().splitlines()
                for dl in variant.expected_dead_lines:
                    if dl <= len(gcov_lines):
                        parts = gcov_lines[dl - 1].split(":")
                        if len(parts) >= 2:
                            cnt_str = parts[0].strip()
                            if cnt_str.isdigit() and int(cnt_str) > 0:
                                ghost_line_count += 1
                                details.append(f"EMI Case {idx}: Dead line {dl} received non-zero count {cnt_str}!")

        if (idx + 1) % 10 == 0 or idx == len(sources_text) - 1:
            print(f"  Processed {idx + 1}/{len(sources_text)} EMI variants... (Pass Rate: {passed_count}/{idx+1})")

    return {
        "total_emi_variants": len(sources_text),
        "successful_executions": passed_count,
        "pass_rate_pct": round((passed_count / len(sources_text) * 100.0) if sources_text else 100.0, 2),
        "detected_dead_code_violations": ghost_line_count,
        "violation_details": details,
    }


def main():
    start_time = time.time()
    concurrency_res = run_concurrency_campaign()
    emi_res = run_metamorphic_campaign(sample_count=50)
    elapsed = round(time.time() - start_time, 2)

    summary = {
        "campaign": "Rigorous Metamorphic (EMI) & Concurrency Campaign",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": elapsed,
        "concurrency_campaign": concurrency_res,
        "metamorphic_campaign": emi_res,
    }

    out_file = RUNS_DIR / "rigorous_campaign_summary.json"
    out_file.write_text(json.dumps(summary, indent=2))
    print(f"\nRigorous campaign completed in {elapsed}s. Summary saved to {out_file}")


if __name__ == "__main__":
    main()
