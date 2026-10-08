import argparse
import json
import sys
from pathlib import Path

from .calibration import run_calibration
from .environment import inspect_environment
from .io import write_json


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CovDiff-Lite handwritten coverage calibration")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check matching tool versions and record environment")
    doctor.add_argument("--output", type=Path)
    calibration = commands.add_parser("calibrate", help="Run reviewed fixtures through both coverage tools")
    calibration.add_argument("--fixtures", type=Path, default=Path("fixtures/calibration"))
    calibration.add_argument("--output", type=Path, required=True, help="New directory; existing paths are refused")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            environment = inspect_environment()
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                write_json(args.output, environment)
            print(json.dumps(environment, indent=2))
            return 0 if environment["ready"] else 1
        summary = run_calibration(args.fixtures, args.output)
        print(f"{summary['passed']}/{summary['cases']} passed; {summary['comparable_lines']} comparable lines")
        print(f"Artifacts: {args.output}")
        return 0 if summary["passed"] == summary["cases"] else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
