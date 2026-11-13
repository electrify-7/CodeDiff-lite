from pathlib import Path

from ..parsers.gcov import parse_gcov
from ..process import CommandRunner, StageError


def run_gcc(source: Path, directory: Path, tools: dict, expected: dict, opt_level: str = "-O0") -> dict:
    source = source.resolve()
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    runner = CommandRunner(directory)
    runner.run("compile", [tools["gcc"]["path"], "-std=c11", opt_level, "-g", "--coverage",
                           "-Wall", "-Wextra", "-c", str(source), "-o", "case.o"], 30)
    runner.run("link", [tools["gcc"]["path"], opt_level, "--coverage", "case.o", "-o", "case"], 30)
    output = runner.run("execute", [str(directory / "case")], 2,
                        expected_exit=expected["exit_code"])
    if output != expected["stdout"]:
        raise StageError("functional_output", "GCC output does not match the fixture oracle")
    runner.run("extract", [tools["gcov"]["path"], "-j", "-b", "-c", "-o", str(directory), str(source)], 15)
    paths = list(directory.glob("*.gcov.json.gz"))
    if len(paths) != 1:
        raise StageError("extract", f"Expected one gcov JSON report; found {len(paths)}")
    return parse_gcov(paths[0], source)
