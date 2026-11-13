"""Saved P033 timing curves and explicitly conditional sensitivity figures."""
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
                     'svg.hashsalt': 'P033'})
fig, axes = plt.subplots(2, 3, figsize=(13, 7), layout='constrained')
for ri, group in enumerate(('G0', 'G1')):
    for ci, mode in enumerate(('T0', 'T1', 'T0B')):
        ax = axes[ri, ci]
        curves = [json.loads(p.read_text()) for p in args.run.glob(f'timing/{group}-*-{mode}/curve.json')]
        assert len(curves) == 3
        x = [r['presentations'] for r in curves[0]]
        for op, color in [('echo', '#1565c0'), ('neg', '#b65013')]:
            y = np.array([[r['metrics_all_values']['by_op'][op]['whole'] / 8 for r in c] for c in curves])
            ax.plot(x, y.mean(axis=0), color=color, lw=2, label=op)
            ax.fill_between(x, y.min(axis=0), y.max(axis=0), color=color, alpha=.1)
        ax.axhline(.75, color='grey', ls=':', lw=1)
        if mode != 'T1':
            ax.axvline(1500 if mode == 'T0' else 1000, color='grey', ls='--', lw=1)
        ax.set(title=f'{group} {mode}', ylim=(-.03, 1.04), xlim=(0, 3000),
               xlabel='Presentations', ylabel='All-eight-value accuracy')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(alpha=.2)
fig.suptitle('P033 fresh timing: three seeds per panel, equal 1500 Echo + 1500 Neg\nDotted .75 may mean only the six trained values work; see split scores', fontsize=13)
for ext in ('png', 'svg'):
    fig.savefig(args.out / f'P033-timing-curves.{ext}', dpi=150, metadata={'Date': None} if ext == 'svg' else None)
plt.close(fig)

summary = json.loads((args.run / 'summary-table.json').read_text())
matrices = json.loads((args.run / 'diagnostic/sensitivity-matrices.json').read_text())
fig, ax = plt.subplot_mosaic([['A', 'A', 'B', 'B', 'C', 'C'], ['D', 'D', 'D', 'E', 'E', 'E']],
                            figsize=(12, 8), layout='constrained')
for label, phase, op, title in [('A', 'before', 'echo', 'Echo before Neg'), ('B', 'after', 'echo', 'Echo after Neg'),
                                ('C', 'after', 'neg', 'Neg after learning')]:
    values = np.zeros((3, 3))
    for r in matrices:
        if r['H'] == 72 and r['subset'] == 'heldout' and r['phase'] == phase and r['operator'] == op:
            values[r['input_bit'], r['output_bit']] = r['mean_signed_delta_p1']
    image = ax[label].imshow(values, cmap='coolwarm', vmin=-1, vmax=1)
    for i in range(3):
        for j in range(3):
            ax[label].text(j, i, f'{values[i,j]:.2f}', ha='center', va='center',
                           color='white' if abs(values[i,j]) > .7 else 'black')
    ax[label].set(title=title, xlabel='Output information bit', ylabel='Flipped Q information bit',
                  xticks=range(3), yticks=range(3))
fig.colorbar(image, ax=[ax[k] for k in ('A', 'B', 'C')], label='Mean signed change in p(next bit=1)', shrink=.8)
for label, r in zip(('D', 'E'), summary['teacher_vs_free']):
    values = np.array([r['free_wrong'], r['teacher_wrong'], r['rescued_after_first_error'],
                       r['introduced_by_correct_prefix_after_first_free_error']])
    im = ax[label].imshow(values, cmap='Blues', vmin=0, vmax=48, aspect='auto')
    for i in range(4):
        for j in range(5):
            ax[label].text(j, i, str(values[i,j]), ha='center', va='center', color='white' if values[i,j] > 26 else 'black')
    ax[label].set(title=f"{r['operator'].capitalize()}: 48 P032 heldout rows", xticks=range(5),
                  xticklabels=['bit0', 'bit1', 'bit2', 'tail', 'STOP'], yticks=range(4),
                  yticklabels=['Free errors', 'Teacher errors', 'Rescued later', 'New TF later'])
fig.suptitle('P033 frozen H72 probes: Q input 0-to-1, original answer prefix fixed\nDiagonal prefixes are consistent; upper-right cells are conditional inconsistent-prefix probes', fontsize=12)
for ext in ('png', 'svg'):
    fig.savefig(args.out / f'P033-probes.{ext}', dpi=150, metadata={'Date': None} if ext == 'svg' else None)
plt.close(fig)
print(json.dumps({'figures': 2, 'matplotlib': matplotlib.__version__, 'numpy_plot_only': np.__version__}))
