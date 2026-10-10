"""Run a frozen generation/analysis configuration and measure local resource use."""

import hashlib
import json
import math
import os
import resource
import time
from pathlib import Path

from .analysis import run_analysis
from .generator import generate_dataset
from .io import write_json


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text())
    fields = {'schema_version', 'experiment_kind', 'per_family', 'seed', 'control_fraction', 'workers'}
    if set(config) != fields or config['schema_version'] != 1:
        raise ValueError('Unsupported experiment configuration')
    if config['experiment_kind'] not in ('pilot', 'main'):
        raise ValueError('Experiment kind must be pilot or main')
    if type(config['workers']) is not int or config['workers'] != 1:
        raise ValueError('Only sequential execution is implemented')
    if type(config['per_family']) is not int or not 1 <= config['per_family'] <= 64:
        raise ValueError('Per-family count must lie between 1 and 64')
    if type(config['seed']) is not int or not 0 <= config['seed'] < 2 ** 64:
        raise ValueError('Seed must be an unsigned 64-bit integer')
    fraction = config['control_fraction']
    if type(fraction) not in (int, float) or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('Invalid control fraction')
    return config


def cgroup_value(name: str):
    try:
        return (Path('/sys/fs/cgroup') / name).read_text().strip()
    except OSError:
        return None


def run_experiment(config_path: Path, output: Path) -> dict:
    config = load_config(config_path)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'config.json', config)
    started = time.monotonic()
    load_start = os.getloadavg()
    dataset = generate_dataset(output / 'dataset', config['per_family'], config['seed'])
    generation_seconds = time.monotonic() - started
    analysis = run_analysis(output / 'dataset/cases', output / 'analysis',
                            control_fraction=config['control_fraction'])
    elapsed = time.monotonic() - started
    files = [path for path in output.rglob('*') if path.is_file()]
    summary = {
        'schema_version': 1, 'config': config,
        'config_sha256': hashlib.sha256((output / 'config.json').read_bytes()).hexdigest(),
        'dataset_sha256': dataset['dataset_sha256'], 'programs': dataset['programs'],
        'generation_seconds': generation_seconds, 'elapsed_seconds': elapsed,
        'analysis_seconds': analysis['elapsed_seconds'],
        'maximum_individual_child_rss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'cgroup_memory_peak_bytes': cgroup_value('memory.peak'),
        'cgroup_memory_limit_bytes': cgroup_value('memory.max'),
        'cgroup_cpu_quota': cgroup_value('cpu.max'),
        'host_load_average_start': load_start, 'host_load_average_end': os.getloadavg(),
        'artifact_files_before_summary': len(files),
        'artifact_logical_bytes_before_summary': sum(path.stat().st_size for path in files),
        'artifact_allocated_bytes_before_summary': sum(path.stat().st_blocks * 512 for path in files),
        'classification_counts': analysis['classification_counts'],
        'valid_first_pass_cases': analysis['valid_first_pass_cases'],
        'oracle_mismatches': analysis['oracle_mismatches'],
        'coverage_collections': analysis['coverage_collections'],
        'comparable_lines': analysis['comparable_lines'],
        'branches': analysis['branches'],
    }
    write_json(output / 'experiment.json', summary)
    return summary
