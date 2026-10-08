from pathlib import Path

from ..parsers.gcov import parse_gcov
from ..process import CommandRunner, StageError


def run_gcc(source: Path, directory: Path, tools: dict, expected: dict) -> dict:
    directory.mkdir()
    runner = CommandRunner(directory)
    runner.run("compile", [tools["gcc"]["path"], "-std=c11", "-O0", "-g", "--coverage",
                           "-Wall", "-Wextra", "-c", str(source), "-o", "case.o"], 30)
    runner.run("link", [tools["gcc"]["path"], "-O0", "--coverage", "case.o", "-o", "case"], 30)
    output = runner.run("execute", [str(directory / "case")], 2,
                        expected_exit=expected["exit_code"])
    if output != expected["stdout"]:
        raise StageError("functional_output", "GCC output does not match the fixture oracle")
    runner.run("extract", [tools["gcov"]["path"], "-j", "-b", "-c", "-o", str(directory), str(source)], 15)
    paths = list(directory.glob("*.gcov.json.gz"))
    if len(paths) != 1:
        raise StageError("extract", f"Expected one gcov JSON report; found {len(paths)}")
    return parse_gcov(paths[0], source)
