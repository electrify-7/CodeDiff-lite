import argparse
import json
import sys
from pathlib import Path

from .calibration import run_calibration
from .environment import inspect_environment
from .io import write_json
from .generator import generate_dataset
from .validation import validate_oracles


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CovDiff-Lite deterministic generation and coverage testing")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Check matching tool versions and record environment")
    doctor.add_argument("--output", type=Path)
    calibration = commands.add_parser("calibrate", help="Run reviewed fixtures through both coverage tools")
    calibration.add_argument("--fixtures", type=Path, default=Path("fixtures/calibration"))
    calibration.add_argument("--output", type=Path, required=True, help="New directory; existing paths are refused")
    generation = commands.add_parser('generate', help='Generate balanced C programs and independent coverage oracles')
    generation.add_argument('--output', type=Path, required=True)
    generation.add_argument('--per-family', type=int, default=40)
    generation.add_argument('--seed', type=int, default=20261010)
    validation = commands.add_parser('validate-oracle', help='Check generated oracles against GCC and Clang execution traces')
    validation.add_argument('--fixtures', type=Path, required=True)
    validation.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            environment = inspect_environment()
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                write_json(args.output, environment)
            print(json.dumps(environment, indent=2))
            return 0 if environment["ready"] else 1
        if args.command == 'generate':
            summary = generate_dataset(args.output, args.per_family, args.seed)
            print(f"Generated {summary['programs']} unique programs in {args.output / 'cases'}")
            print(f"Dataset SHA-256: {summary['dataset_sha256']}")
            return 0
        if args.command == 'validate-oracle':
            summary = validate_oracles(args.fixtures, args.output)
            print(f"{summary['passed']}/{summary['cases']} oracles matched both C execution traces")
            return 0 if summary['passed'] == summary['cases'] else 1
        summary = run_calibration(args.fixtures, args.output)
        print(f"{summary['passed']}/{summary['cases']} passed; {summary['comparable_lines']} comparable lines")
        print(f"Artifacts: {args.output}")
        return 0 if summary["passed"] == summary["cases"] else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
