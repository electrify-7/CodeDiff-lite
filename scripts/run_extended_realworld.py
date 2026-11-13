#!/usr/bin/env python3
"""Extended Real-World Open-Source Evaluation Benchmark.

Evaluates GCC 11 vs Clang 14 across three production C projects:
1. zlib: compress.c (Standard compression library)
2. cJSON: cJSON.c (Ultra-lightweight JSON parser)
3. SQLite: sqlite3.c (240,000+ line database engine)

Measures:
- Total instrumented lines (GCC vs LLVM)
- Percentage coverage reported
- Macro divergence %
- Micro asymmetric line counts (L_gcc_only, L_llvm_only)
- CI Gate threshold conflicts (where PR passes GCC but fails Clang)
"""

import gzip
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from covdiff_lite.parsers.gcov import parse_gcov
from covdiff_lite.parsers.llvm import parse_llvm
from covdiff_lite.realworld import compare_realworld_reports
from covdiff_lite.io import write_json


def benchmark_zlib(exp_dir: Path) -> dict:
    print("\n" + "-" * 60)
    print("RUNNING EXTENDED BENCHMARK 1: zlib (compress.c)")
    print("-" * 60)
    zlib_candidates = ["/zlib", "/home/mahoraga/Software/zlib-test"]
    zlib_dir = next((Path(p).resolve() for p in zlib_candidates if (Path(p) / "compress.c").exists()), None)
    if not zlib_dir:
        return {"error": "zlib not found"}

    z_gcc_dir = exp_dir / "zlib_gcc"
    z_llvm_dir = exp_dir / "zlib_llvm"
    z_gcc_dir.mkdir(parents=True, exist_ok=True)
    z_llvm_dir.mkdir(parents=True, exist_ok=True)
    compress_c = zlib_dir / "compress.c"

    # GCC
    subprocess.run(
        f"cd {zlib_dir} && rm -f *.gc* *.o example_gcc && "
        f"gcc-11 -O0 --coverage -I. -c compress.c -o compress.o && "
        f"gcc-11 -O0 --coverage -I. compress.o adler32.c crc32.c deflate.c infback.c inffast.c inflate.c inftrees.c trees.c uncompr.c zutil.c gz*.c test/example.c -o example_gcc && "
        f"./example_gcc && gcov-11 -j -b compress.c && cp compress.gcov.json.gz {z_gcc_dir}/",
        shell=True, check=True
    )

    # Clang
    subprocess.run(
        f"cd {zlib_dir} && rm -f *.prof* example_clang && "
        f"clang-14 -O0 -g -fprofile-instr-generate -fcoverage-mapping -I. *.c test/example.c -o example_clang && "
        f"LLVM_PROFILE_FILE=example.profraw ./example_clang && "
        f"llvm-profdata-14 merge -sparse example.profraw -o example.profdata && "
        f"llvm-cov-14 export ./example_clang -instr-profile=example.profdata compress.c > {z_llvm_dir}/compress.llvm.json",
        shell=True, check=True
    )

    parsed_gcc = parse_gcov(z_gcc_dir / "compress.gcov.json.gz", compress_c)
    parsed_llvm = parse_llvm(z_llvm_dir / "compress.llvm.json", compress_c)
    cmp_res = compare_realworld_reports("zlib:compress.c", len(compress_c.read_text().splitlines()),
                                        parsed_gcc, parsed_llvm, ci_thresholds=[70, 75, 76, 80, 85])
    return cmp_res.to_dict()


def benchmark_cjson(exp_dir: Path) -> dict:
    print("\n" + "-" * 60)
    print("RUNNING EXTENDED BENCHMARK 2: cJSON (cJSON.c)")
    print("-" * 60)
    cjson_candidates = ["/cjson", "/home/mahoraga/Software/cjson"]
    cjson_dir = next((Path(p).resolve() for p in cjson_candidates if (Path(p) / "cJSON.c").exists()), None)
    if not cjson_dir:
        return {"error": "cJSON not found"}

    c_gcc_dir = exp_dir / "cjson_gcc"
    c_llvm_dir = exp_dir / "cjson_llvm"
    c_gcc_dir.mkdir(parents=True, exist_ok=True)
    c_llvm_dir.mkdir(parents=True, exist_ok=True)
    cjson_c = cjson_dir / "cJSON.c"

    # GCC
    subprocess.run(
        f"cd {cjson_dir} && rm -f *.gc* *.o test_gcc && "
        f"gcc-11 -O0 --coverage -I. -c cJSON.c -o cJSON.o && "
        f"gcc-11 -O0 --coverage -I. cJSON.o test.c -o test_gcc && "
        f"./test_gcc > /dev/null && gcov-11 -j -b cJSON.c && cp cJSON.gcov.json.gz {c_gcc_dir}/",
        shell=True, check=True
    )

    # Clang
    subprocess.run(
        f"cd {cjson_dir} && rm -f *.prof* test_clang && "
        f"clang-14 -O0 -g -fprofile-instr-generate -fcoverage-mapping -I. cJSON.c test.c -o test_clang && "
        f"LLVM_PROFILE_FILE=cjson.profraw ./test_clang > /dev/null && "
        f"llvm-profdata-14 merge -sparse cjson.profraw -o cjson.profdata && "
        f"llvm-cov-14 export ./test_clang -instr-profile=cjson.profdata cJSON.c > {c_llvm_dir}/cjson.llvm.json",
        shell=True, check=True
    )

    parsed_gcc = parse_gcov(c_gcc_dir / "cJSON.gcov.json.gz", cjson_c)
    parsed_llvm = parse_llvm(c_llvm_dir / "cjson.llvm.json", cjson_c)
    cmp_res = compare_realworld_reports("cJSON:cJSON.c", len(cjson_c.read_text().splitlines()),
                                        parsed_gcc, parsed_llvm, ci_thresholds=[20, 22, 24, 25, 26, 30])
    return cmp_res.to_dict()


def benchmark_sqlite(exp_dir: Path) -> dict:
    print("\n" + "-" * 60)
    print("RUNNING EXTENDED BENCHMARK 3: SQLite (sqlite3.c)")
    print("-" * 60)
    sqlite_candidates = ["/sqlite", "/home/mahoraga/Software/sqlite/sqlite-amalgamation-3450300"]
    sqlite_dir = next((Path(p).resolve() for p in sqlite_candidates if (Path(p) / "sqlite3.c").exists()), None)
    if not sqlite_dir:
        return {"error": "sqlite not found"}

    s_gcc_dir = exp_dir / "sqlite_gcc"
    s_llvm_dir = exp_dir / "sqlite_llvm"
    s_gcc_dir.mkdir(parents=True, exist_ok=True)
    s_llvm_dir.mkdir(parents=True, exist_ok=True)
    sqlite_c = sqlite_dir / "sqlite3.c"

    # GCC
    subprocess.run(
        f"cd {sqlite_dir} && rm -f *.gc* *.o sqlite3_gcc && "
        f"gcc-11 -O0 --coverage -DSQLITE_THREADSAFE=0 -c sqlite3.c -o sqlite3.o && "
        f"gcc-11 -O0 --coverage -DSQLITE_THREADSAFE=0 sqlite3.o shell.c -ldl -o sqlite3_gcc && "
        f"./sqlite3_gcc :memory: 'CREATE TABLE t(x); INSERT INTO t VALUES(1),(2),(3); SELECT sum(x) FROM t;' && "
        f"gcov-11 -j -b sqlite3.c && cp sqlite3.gcov.json.gz {s_gcc_dir}/",
        shell=True, check=True
    )

    # Clang
    subprocess.run(
        f"cd {sqlite_dir} && rm -f *.prof* sqlite3_clang && "
        f"clang-14 -O0 -g -fprofile-instr-generate -fcoverage-mapping -DSQLITE_THREADSAFE=0 sqlite3.c shell.c -ldl -o sqlite3_clang && "
        f"LLVM_PROFILE_FILE=sqlite.profraw ./sqlite3_clang :memory: 'CREATE TABLE t(x); INSERT INTO t VALUES(1),(2),(3); SELECT sum(x) FROM t;' && "
        f"llvm-profdata-14 merge -sparse sqlite.profraw -o sqlite.profdata && "
        f"llvm-cov-14 export ./sqlite3_clang -instr-profile=sqlite.profdata sqlite3.c > {s_llvm_dir}/sqlite3.llvm.json",
        shell=True, check=True
    )

    parsed_gcc = parse_gcov(s_gcc_dir / "sqlite3.gcov.json.gz", sqlite_c)
    parsed_llvm = parse_llvm(s_llvm_dir / "sqlite3.llvm.json", sqlite_c)
    cmp_res = compare_realworld_reports("sqlite:sqlite3.c", len(sqlite_c.read_text().splitlines()),
                                        parsed_gcc, parsed_llvm, ci_thresholds=[18, 19, 20, 21, 22, 25])
    return cmp_res.to_dict()


def main():
    print("=" * 70)
    print("STARTING EXTENDED REAL-WORLD BENCHMARK SUITE (zlib, cJSON, SQLite)")
    print("=" * 70)
    start_time = time.monotonic()
    out_dir = (project_root / "runs" / "extended_realworld").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    r_zlib = benchmark_zlib(out_dir)
    r_cjson = benchmark_cjson(out_dir)
    r_sqlite = benchmark_sqlite(out_dir)

    elapsed = time.monotonic() - start_time
    suite_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(elapsed, 2),
        "benchmarks": {
            "zlib": r_zlib,
            "cjson": r_cjson,
            "sqlite": r_sqlite,
        }
    }

    write_json(out_dir / "extended_realworld_summary.json", suite_summary)

    print("\n" + "=" * 70)
    print("EXTENDED REAL-WORLD BENCHMARK SUITE COMPLETE!")
    print(f"Total Elapsed Time: {elapsed:.2f} seconds")
    print(f"Report: {out_dir / 'extended_realworld_summary.json'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
