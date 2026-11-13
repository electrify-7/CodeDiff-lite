import argparse
import json
import sys
from pathlib import Path

from .calibration import run_calibration
from .environment import inspect_environment
from .io import write_json
from .generator import generate_dataset
from .validation import validate_oracles
from .analysis import run_analysis
from .issues import reproduce_issues
from .experiment import run_experiment
from .controls import run_layout_controls
from .review import review_analysis
from .report import generate_report
from .empirical import generate_empirical
from .figures import plot_tables
from .pipeline import run_pipeline
from .synthesis import generate_large_scale_corpus
from .reduce import ProgramReducer, default_predicate
from .optimization import run_optimization_sweep
from .matrix import CompilerMatrix
from .realworld import compare_realworld_reports
from .downstream import evaluate_sbfl_impact
from .audit import audit_coverage_gate
from .cert import generate_mcdc_certificate
from .dashboard import generate_dashboard_html, start_dashboard_server


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
    analysis = commands.add_parser('analyze', help='Compare coverage with the oracle and confirm discrepancies in clean runs')
    inputs = analysis.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--fixtures', type=Path)
    inputs.add_argument('--case', type=Path, help='One saved manifest to reproduce')
    analysis.add_argument('--output', type=Path, required=True)
    analysis.add_argument('--control-fraction', type=float, default=0.1)
    issues = commands.add_parser('reproduce-issues', help='Confirm documented symptoms and negative controls')
    issues.add_argument('--fixtures', type=Path, default=Path('fixtures/issues'))
    issues.add_argument('--output', type=Path, required=True)
    experiment = commands.add_parser('experiment', help='Generate and analyze a frozen experiment configuration')
    experiment.add_argument('--config', type=Path, required=True)
    experiment.add_argument('--output', type=Path, required=True)
    layout = commands.add_parser('layout-controls', help='Run 16 source-layout pairs from a frozen dataset')
    layout.add_argument('--dataset', type=Path, required=True)
    layout.add_argument('--output', type=Path, required=True)
    review = commands.add_parser('review', help='Audit raw evidence and group unresolved source mappings')
    review.add_argument('--analysis', type=Path, required=True)
    review.add_argument('--output', type=Path, required=True, help='New JSON file in an existing directory')
    report = commands.add_parser('report', help='Bundle saved coverage evidence into an offline HTML dashboard')
    report.add_argument('--analysis', type=Path, required=True)
    report.add_argument('--output', type=Path, required=True, help='New directory; measurements are read only')
    report.add_argument('--review', type=Path, help='Matching saved review overlay')
    report.add_argument('--documented-issues', type=Path, help='Separate documented-issue analysis directory')
    report.add_argument('--layout-controls', type=Path, help='Separate paired-layout experiment directory')
    report.add_argument('--layout-review', type=Path, help='Matching layout review overlay')
    report.add_argument('--empirical', type=Path, help='Matching empirical tables and figures to bundle')
    empirical = commands.add_parser('empirical', help='Derive empirical tables, analysis and figures from saved evidence')
    empirical.add_argument('--analysis', type=Path, required=True)
    empirical.add_argument('--output', type=Path, required=True)
    empirical.add_argument('--review', type=Path)
    empirical.add_argument('--documented-issues', type=Path)
    empirical.add_argument('--layout-controls', type=Path)
    empirical.add_argument('--layout-review', type=Path)
    plots = commands.add_parser('plots', help='Regenerate publication figures from retained CSV inputs')
    plots.add_argument('--tables', type=Path, required=True)
    plots.add_argument('--output', type=Path, required=True)
    pipeline = commands.add_parser('pipeline', help='Run the complete experiment, issue/control checks, audits and publication')
    pipeline.add_argument('--config', type=Path, default=Path('configs/main.json'))
    pipeline.add_argument('--output', type=Path, required=True)
    pipeline.add_argument('--issue-fixtures', type=Path, default=Path('fixtures/issues'))
    synth = commands.add_parser('synthesize', help='Synthesize scaled corpus of diverse deterministic programs')
    synth.add_argument('--output', type=Path, required=True)
    synth.add_argument('--target-count', type=int, default=5000)
    synth.add_argument('--seed', type=int, default=20261113)
    red = commands.add_parser('reduce', help='Minimize candidate bug program using delta debugging')
    red.add_argument('--source', type=Path, required=True)
    red.add_argument('--expected-stdout', type=str, default='0\n')
    red.add_argument('--expected-exit', type=int, default=0)
    red.add_argument('--output', type=Path, required=True)
    audit = commands.add_parser('audit', help='Audit PR or codebase for cross-compiler CI coverage gate flip risks')
    audit.add_argument('--target', type=str, default='target.c')
    audit.add_argument('--source', type=Path, required=True)
    audit.add_argument('--gcc-report', type=Path, required=True)
    audit.add_argument('--llvm-report', type=Path, required=True)
    audit.add_argument('--threshold', type=float, default=75.0)
    audit.add_argument('--output', type=Path)
    dash = commands.add_parser('dashboard', help='Generate standalone interactive visual coverage dashboard')
    dash.add_argument('--output', type=Path, default=Path('runs/dashboard/index.html'))
    dash.add_argument('--serve', action='store_true', help='Start web server to host dashboard')
    dash.add_argument('--port', type=int, default=8080, help='Port to bind the server (default: 8080)')
    cert_p = commands.add_parser('cert', help='Generate formal DO-178C Level A / ISO 26262 ASIL-D MC/DC compliance certificate')
    cert_p.add_argument('--software-name', type=str, default='SafetyCriticalModule')
    cert_p.add_argument('--decisions-file', type=Path, required=True, help='JSON file containing decision structures and conditions')
    cert_p.add_argument('--vectors-file', type=Path, required=True, help='JSON file containing dynamic test execution vectors')
    cert_p.add_argument('--output', type=Path, help='Output path for certificate (.json or .md)')
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
        if args.command == 'review':
            report = review_analysis(args.analysis, args.output)
            print(json.dumps({k: v for k, v in report.items() if k not in ('reviews', 'raw_count_disagreements')}, indent=2))
            return 1 if report['cases_requiring_further_inspection'] else 0
        if args.command == 'report':
            result = generate_report(args.analysis, args.output, args.review, args.documented_issues,
                                     args.layout_controls, args.layout_review, args.empirical)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == 'empirical':
            result = generate_empirical(args.analysis, args.output, args.review, args.documented_issues,
                                        args.layout_controls, args.layout_review)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == 'plots':
            print(json.dumps(plot_tables(args.tables, args.output), indent=2))
            return 0
        if args.command == 'pipeline':
            result = run_pipeline(args.config, args.output, args.issue_fixtures)
            print(json.dumps(result, indent=2))
            return 0 if result['checks_passed'] else 1
        if args.command == 'layout-controls':
            report = run_layout_controls(args.dataset, args.output)
            print(json.dumps({k: v for k, v in report.items() if k != 'results'}, indent=2))
            return 0 if report['pairs_passed'] == report['pairs'] else 1
        if args.command == 'experiment':
            summary = run_experiment(args.config, args.output)
            print(json.dumps(summary, indent=2))
            failed = any(summary['classification_counts'].get(label, 0)
                         for label in ('pipeline_failure', 'unstable_or_non_reproducible'))
            return 1 if failed else 0
        if args.command == 'reproduce-issues':
            summary = reproduce_issues(args.fixtures, args.output)
            print(json.dumps(summary, indent=2))
            return 0 if summary['all_checks_passed'] else 1
        if args.command == 'analyze':
            summary = run_analysis(args.fixtures, args.output, args.case, args.control_fraction)
            print(json.dumps({k: v for k, v in summary.items() if k not in ('results', 'families')}, indent=2))
            failed = any(r['classification'] in ('pipeline_failure', 'unstable_or_non_reproducible') for r in summary['results'])
            return 1 if failed else 0
        if args.command == 'synthesize':
            cases = generate_large_scale_corpus(args.target_count, args.seed)
            args.output.mkdir(parents=True, exist_ok=True)
            for source, manifest in cases:
                (args.output / manifest['source']).write_text(source)
                write_json(args.output / f"{manifest['case_id']}.json", manifest)
            print(f"Synthesized {len(cases)} verified programs in {args.output}")
            return 0
        if args.command == 'reduce':
            source_text = args.source.read_text()
            pred = lambda s: default_predicate(s, args.expected_stdout, args.expected_exit)
            reducer = ProgramReducer(pred)
            result = reducer.reduce(source_text)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result.reduced_source)
            print(json.dumps(result.to_dict(), indent=2))
            return 0
        if args.command == 'audit':
            verdict = audit_coverage_gate(args.target, args.source, args.gcc_report, args.llvm_report, args.threshold)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                write_json(args.output, verdict.to_dict())
            print(verdict.markdown_report)
            return 1 if verdict.verdict == "FLIP_RISK" else 0
        if args.command == 'dashboard':
            out = generate_dashboard_html(args.output)
            print(f"Generated standalone interactive dashboard at {out}")
            if getattr(args, 'serve', False):
                start_dashboard_server(out, args.port)
            return 0
        if args.command == 'cert':
            decisions = json.loads(args.decisions_file.read_text())
            vectors = json.loads(args.vectors_file.read_text())
            cert = generate_mcdc_certificate(args.software_name, decisions, vectors)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                if str(args.output).endswith('.json'):
                    write_json(args.output, cert.to_dict())
                else:
                    args.output.write_text(cert.to_markdown())
            print(cert.to_markdown())
            return 0 if cert.all_decisions_satisfied else 1
        summary = run_calibration(args.fixtures, args.output)
        print(f"{summary['passed']}/{summary['cases']} passed; {summary['comparable_lines']} comparable lines")
        print(f"Artifacts: {args.output}")
        return 0 if summary["passed"] == summary["cases"] else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
