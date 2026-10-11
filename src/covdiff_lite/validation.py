"""Validate model execution using separately instrumented C trace twins."""

from pathlib import Path

from .calibration import load_fixture
from .environment import inspect_environment
from .io import write_json
from .process import CommandRunner, StageError
from .render import Renderer
from .templates import build_program


def validate_oracles(fixtures: Path, output: Path) -> dict:
    environment = inspect_environment()
    if not environment['ready']:
        raise ValueError('Environment is not ready: ' + '; '.join(environment['errors']))
    loaded = [load_fixture(path) for path in sorted(fixtures.glob('*.json'))]
    if not loaded or any(m['origin'] != 'generated' for m, _ in loaded):
        raise ValueError('Oracle validation requires generated manifests')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'environment.json', environment)
    results = []
    for manifest, _ in loaded:
        directory = output / manifest['case_id']
        directory.mkdir()
        renderer = Renderer(manifest['family'], manifest['parameters'], trace=True)
        twin = renderer.render(build_program(manifest['family'], manifest['parameters']))
        if 'layout_control' in manifest:
            from .layout import transform_braces
            twin, _, _ = transform_braces(twin, renderer.roles)
        source = directory / 'trace.c'
        source.write_text(twin)
        checks = []
        for name in ('gcc', 'clang'):
            tool_directory = directory / name
            tool_directory.mkdir()
            runner = CommandRunner(tool_directory)
            error = None
            try:
                runner.run('compile', [environment['tools'][name]['path'], '-std=c11', '-O0',
                                      str(source), '-o', 'trace'], 30)
                stdout = runner.run('execute', [str(tool_directory / 'trace')], 2)
                actual_events = (tool_directory / 'execute.stderr').read_text().splitlines()
                if stdout != manifest['expected_output']['stdout'] or actual_events != manifest['oracle']['trace_events']:
                    error = 'C execution trace or output contradicts the model oracle'
            except (StageError, OSError) as exc:
                error = str(exc)
            checks.append({'tool': name, 'passed': error is None, 'error': error})
        results.append({'case_id': manifest['case_id'], 'passed': all(c['passed'] for c in checks), 'checks': checks})
        write_json(directory / 'validation.json', results[-1])
    summary = {'schema_version': 1, 'purpose': 'oracle_trace_validation', 'cases': len(results),
               'passed': sum(r['passed'] for r in results), 'compiler_executions': len(results) * 2,
               'coverage_collected': False, 'results': results}
    write_json(output / 'summary.json', summary)
    return summary
