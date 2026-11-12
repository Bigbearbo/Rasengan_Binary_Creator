"""Plot saved P032 observations only; optional isolated matplotlib directory."""
import argparse
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('run', type=Path)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--plot-deps', type=Path)
args = parser.parse_args()
os.environ['MPLCONFIGDIR'] = str(args.run.parent / 'plot-cache')
if args.plot_deps:
    sys.path.insert(0, str(args.plot_deps))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.hashsalt': 'P032-fixed'})
fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout='constrained')
for ri, ratio in enumerate((70, 50)):
    for ci, hidden in enumerate((72, 128)):
        ax = axes[ri, ci]
        curves = [json.loads(p.read_text()) for p in args.run.glob(f'training/*-H{hidden}/neg{ratio}/curve.json')]
        assert len(curves) == 6
        x = [r['presentations'] for r in curves[0]]
        assert all([r['presentations'] for r in curve] == x for curve in curves)
        for op, color in [('echo', '#1565c0'), ('neg', '#b65013')]:
            for group, style in [('train', '-'), ('validation', '--')]:
                y = np.array([[r[group]['by_op'][op]['whole'] / r[group]['by_op'][op]['total']
                               for r in curve] for curve in curves])
                ax.plot(x, y.mean(axis=0), style, color=color, lw=2,
                        label=f'{op.capitalize()} {group}')
        ax.set(title=f'H={hidden}; new Neg : old Echo = {ratio}:{100-ratio}',
               xlabel='Neg-stage presentations', ylabel='Whole-answer accuracy',
               ylim=(-.04, 1.06), xlim=(0, 3000))
        ax.grid(alpha=.2)
        ax.legend(fontsize=8, loc='center right')
fig.suptitle('P032: six learners per panel; observed checkpoint means\nEach learner has only one validation value per operator', fontsize=13)
fig.savefig(str(args.out) + '.png', dpi=150)
fig.savefig(str(args.out) + '.svg', metadata={'Date': None})
plt.close(fig)
print(json.dumps({'matplotlib': matplotlib.__version__, 'numpy_plot_only': np.__version__, 'panels': 4}))
