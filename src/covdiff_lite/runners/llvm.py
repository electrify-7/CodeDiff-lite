from pathlib import Path

from ..parsers.llvm import parse_llvm
from ..process import CommandRunner, StageError


def run_llvm(source: Path, directory: Path, tools: dict, expected: dict) -> dict:
    directory.mkdir()
    runner = CommandRunner(directory)
    runner.run("compile", [tools["clang"]["path"], "-std=c11", "-O0", "-g",
                           "-fprofile-instr-generate", "-fcoverage-mapping",
                           "-Wall", "-Wextra", str(source), "-o", "case"], 30)
    output = runner.run("execute", [str(directory / "case")], 2,
                        env={"LLVM_PROFILE_FILE": str(directory / "case.profraw")},
                        expected_exit=expected["exit_code"])
    if output != expected["stdout"]:
        raise StageError("functional_output", "Clang output does not match the fixture oracle")
    runner.run("merge", [tools["llvm_profdata"]["path"], "merge", "-sparse", "case.profraw", "-o", "case.profdata"], 15)
    args = [tools["llvm_cov"]["path"], "export", "./case", "-instr-profile=case.profdata", str(source)]
    export = runner.run("export", args, 15)
    path = directory / "coverage.json"
    path.write_text(export)
    # Human-readable calibration evidence uses the same file's primary view.
    runner.run("show", [tools["llvm_cov"]["path"], "show", "./case", "-instr-profile=case.profdata",
                        "-show-line-counts", "-show-expansions=false", "-use-color=false", str(source)], 15)
    return parse_llvm(path, source)
