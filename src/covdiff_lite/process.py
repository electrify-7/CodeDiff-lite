"""Run subprocesses with stage evidence and terminate their groups on timeout."""

import os
import signal
import subprocess
import time
from pathlib import Path

from .io import write_json


class StageError(RuntimeError):
    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(message)


class CommandRunner:
    def __init__(self, directory: Path):
        self.directory = directory
        self.records = []

    def run(self, stage: str, argv: list[str], timeout: float,
            env: dict | None = None, expected_exit: int = 0) -> str:
        record = {
            "stage": stage, "argv": argv, "cwd": str(self.directory),
            "env_overrides": env or {}, "timeout_seconds": timeout,
            "expected_exit": expected_exit,
        }
        started = time.monotonic()
        stdout = stderr = ""
        try:
            process = subprocess.Popen(
                argv, cwd=self.directory, env={**os.environ, **(env or {})},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                record["timed_out"] = False
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                record["timed_out"] = True
            record["exit_code"] = process.returncode
        except OSError as exc:
            record["error"] = str(exc)
            record["exit_code"] = None
            record["timed_out"] = False
        finally:
            record["duration_seconds"] = time.monotonic() - started
            record["stdout_file"] = stage + ".stdout"
            record["stderr_file"] = stage + ".stderr"
            (self.directory / record["stdout_file"]).write_text(stdout)
            (self.directory / record["stderr_file"]).write_text(stderr)
            self.records.append(record)
            write_json(self.directory / "commands.json", self.records)
        if record["timed_out"]:
            raise StageError(stage, f"{stage} exceeded {timeout}s")
        if record["exit_code"] != expected_exit:
            raise StageError(stage, f"{stage} exited {record['exit_code']}; expected {expected_exit}. See {self.directory}")
        return stdout
