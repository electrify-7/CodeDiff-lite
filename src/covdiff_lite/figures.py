"""Publication figures drawn exclusively from retained CSV plotting inputs."""

import csv
import os
import tempfile
from pathlib import Path


CLASSIFICATIONS = (
    'complete_agreement', 'known_convention_difference', 'unresolved_disagreement',
    'probable_incorrect_coverage_report', 'unstable_or_non_reproducible', 'pipeline_failure',
)
LABELS = ('Agreement', 'Known convention', 'Unresolved', 'Probable incorrect', 'Unstable', 'Pipeline failure')
COLORS = ('#278267', '#8e71b4', '#d5a044', '#bd4c54', '#5981aa', '#743f46')


def require_matplotlib():
    os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / f'covdiff-matplotlib-{os.getuid()}'))
    try:
        import matplotlib
    except ImportError as error:
        raise ValueError('Figure generation requires Matplotlib. Use bash scripts/env.sh build-reporting '
                         'and the reporting image, or install the figures optional dependency.') from error
    return matplotlib


def read_table(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def plot_tables(tables: Path, output: Path):
    matplotlib = require_matplotlib()
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none', 'svg.hashsalt': 'covdiff-lite'})
    files = []

    def save(fig, name):
        fig.tight_layout()
        for extension in ('svg', 'png'):
            path = output / (name + '.' + extension)
            metadata = {'Date': None} if extension == 'svg' else {'Software': 'CovDiff-Lite / Matplotlib'}
            fig.savefig(path, dpi=180, metadata=metadata, facecolor='white', bbox_inches='tight')
            files.append(path.name)
        plt.close(fig)

    classifications = read_table(tables / 'classifications.csv')
    fig, ax = plt.subplots(figsize=(9, 3.8))
    values = [int(row['cases']) for row in classifications]
    ax.barh(list(reversed(LABELS)), list(reversed(values)), color=list(reversed(COLORS)))
    for i, value in enumerate(reversed(values)):
        ax.text(value + max(values + [1]) * .015, i, str(value), va='center')
    ax.set_xlim(0, max(values + [1]) * 1.16)
    ax.set_xlabel('Programs (mutually exclusive saved classification)')
    ax.set_title('Primary dataset: case classifications', loc='left', weight='bold')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    save(fig, 'classifications')

    families = read_table(tables / 'families.csv')
    names = [row['family'].replace('_', ' ') for row in families]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    left = [0] * len(families)
    for classification, label, color in zip(CLASSIFICATIONS, LABELS, COLORS):
        values = [int(row[classification]) for row in families]
        if any(values):
            ax.barh(names, values, left=left, label=label, color=color)
            left = [a+b for a, b in zip(left, values)]
    ax.invert_yaxis()
    ax.set_xlabel('Programs; each program counted once')
    ax.set_title('Primary dataset: classification by construct', loc='left', weight='bold')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.17), ncol=3, frameon=False)
    save(fig, 'families')

    fig, ax = plt.subplots(figsize=(10, 4.8))
    left = [0] * len(families)
    for field, label, color in [('comparable_lines', 'Scored, mutually reported', '#278267'),
                               ('unmapped_oracle_lines', 'Scored, missing mapping', '#d5a044'),
                               ('unscored_lines', 'Unscored source', '#c9d4d6')]:
        values = [int(row[field]) for row in families]
        ax.barh(names, values, left=left, label=label, color=color)
        left = [a+b for a, b in zip(left, values)]
    ax.invert_yaxis()
    ax.set_xlabel('First-pass source locations; one location per source line')
    ax.set_title('Primary dataset: coverage denominators', loc='left', weight='bold')
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.17), ncol=3, frameon=False)
    save(fig, 'denominators')

    timings = read_table(tables / 'timing.csv')
    valid = [row for row in timings if row['valid_first_pass'] == 'True']
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, field, title in zip(axes, ('first_pass_seconds', 'repeat_seconds'),
                              ('First paired coverage collection', 'Confirmation collections per case')):
        values = [float(row[field]) for row in valid]
        if values:
            ax.hist(values, bins=min(20, max(1, len(values) // 10)), color='#5981aa', edgecolor='white')
        else:
            ax.text(.5, .5, 'No valid timing observations', ha='center', transform=ax.transAxes)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel('Seconds (single machine, sequential execution)')
        ax.set_ylabel('Programs with a valid first pass')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    save(fig, 'runtime')
    return {'backend': 'Matplotlib / Agg', 'matplotlib_version': matplotlib.__version__,
            'files': files, 'input_directory': 'tables', 'runtime_scope': 'valid_first_pass_cases'}
