"""Two paired P035 figures from completed fixed JSON results; no inference."""
import argparse
import json
import os
from pathlib import Path
import sys


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[2] / 'work/sle-p035/publication')
    parser.add_argument('--plot-deps', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    summary = read(out / 'summary-table.json')
    assert summary['status'] == 'passed' and len(summary['students']) == 12
    assert summary['all_primary_and_replay_completed']
    os.environ['MPLCONFIGDIR'] = str(out / 'mpl-cache')
    deps = args.plot_deps or Path(__file__).resolve().parents[2] / 'work/sle-research-review/plot-deps'
    assert deps.is_dir(), 'Existing plot dependencies required; no package installation'
    sys.path.insert(0, str(deps))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False, 'axes.titleweight': 'bold'})
    students = summary['students']
    seeds = (101, 202, 303)
    arms = ('SF', 'SG', 'HF', 'HG')
    own = {(r['codec'], r['policy'], r['seed']): r for r in students}
    interactions = summary['primary']['per_seed_interactions']
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5), gridspec_kw={'width_ratios': [1.5, 1]})
    fig.subplots_adjust(left=.1, right=.95, bottom=.24, top=.78, wspace=.35)
    matrix = [[own[(arm[0], arm[1], seed)]['primary']['score'] for arm in arms] for seed in seeds]
    axes[0].imshow(matrix, aspect='auto', vmin=0, vmax=4,
                   cmap=ListedColormap(['#edf1f4', '#c4dce7', '#82b8cf', '#397fa9', '#164d72']))
    for i, row in enumerate(matrix):
        for j, score in enumerate(row):
            axes[0].text(j, i, str(score), va='center', ha='center', fontsize=22, weight='bold',
                         color='white' if score >= 3 else '#17334b')
    axes[0].set(xticks=range(4), xticklabels=['S / Fixed', 'S / Growth', 'H / Fixed', 'H / Growth'],
                yticks=range(3), yticklabels=[f'seed {seed}' for seed in seeds], title='All 12 final paired milestone scores (0..4)')
    axes[0].tick_params(length=0, pad=12)
    axes[0].axvline(1.5, color='white', linewidth=3)
    for i, row in enumerate(interactions):
        x = row['interaction']
        axes[1].plot([0, x], [i, i], color='#557f95', linewidth=3)
        axes[1].plot(x, i, 'o', color='#164d72', markersize=9)
        axes[1].annotate(f'{x:+d}', (x, i), xytext=(8 if x >= 0 else -8, 10), textcoords='offset points',
                         ha='left' if x >= 0 else 'right', weight='bold')
    axes[1].axvline(0, color='#777777', linewidth=1)
    axes[1].set(yticks=range(3), yticklabels=[f'seed {seed}' for seed in seeds], ylim=(2.6, -.6),
                xlim=(-8.8, 8.8), xticks=[-8, -4, 0, 4, 8],
                xlabel='(S-Growth - S-Fixed) - (H-Growth - H-Fixed)', title='Predeclared per-seed interaction')
    axes[1].grid(axis='x', alpha=.16)
    fig.suptitle('P035: input codec by capacity timing, fixed budget', y=.95, fontsize=17, weight='bold')
    fig.text(.5, .86, 'S = SLE-Original; H = compact unary hierarchy. Every score uses final op2/data3 raw format + STOP.', ha='center', fontsize=10)
    fig.text(.07, .13, 'Milestones are nested: Echo 0..1, Echo 0..3, Echo 0..7, Echo + Neg 0..7. They are not four independent skills.', fontsize=10)
    fig.text(.07, .08, 'All three seeds and all failures included. Interaction is descriptive; SG-best alone does not establish a growth-specific SLE benefit.', fontsize=9, color='#555555')
    fig.text(.07, .04, 'Shared response grammar controls output-side learning. This is not a shortest-native-output or full system-cost benchmark.', fontsize=9, color='#555555')
    fig.savefig(out / 'P035-paired-milestones.png', dpi=160, facecolor='white')
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(15, 9), sharex=True, sharey=True)
    fig.subplots_adjust(left=.065, right=.98, bottom=.17, top=.81, wspace=.15, hspace=.34)
    colors = {'S': '#246798', 'H': '#ae6020'}
    stage_labels = ('Echo d1', 'Echo d2', 'Echo d3', 'op2', '+Neg')
    stage_names = ('s0_echo_d1', 's1_echo_d2', 's2_echo_d3', 's3_op2', 's4_neg')
    for ri, policy in enumerate(('F', 'G')):
        for ci, seed in enumerate(seeds):
            ax = axes[ri, ci]
            reference = own[('S', policy, seed)]
            starts, cumulative = [], 0
            for stage in reference['stages']:
                starts.append(cumulative)
                cumulative += stage['budget']['executed_train_MACs']
            for codec in ('S', 'H'):
                student = own[(codec, policy, seed)]
                train_x, train_y, held_x, held_y = [], [], [], []
                for index, stage in enumerate(student['stages']):
                    curve = read(args.run / f'{codec}-{policy}-seed{seed}' / stage_names[index] / 'curve.json')
                    for point in curve:
                        train_x.append(point['cumulative_train_MACs'] / 1e6)
                        train = point['metrics']['train']
                        train_y.append(train['whole'] / train['total'])
                    if index < 2:
                        continue  # Exhaustive d1/d2 have no heldout denominator.
                    for snapshot in stage['snapshots']:
                        metrics = snapshot['metrics']
                        total = metrics['val']['total'] + metrics['test']['total']
                        assert total > 0
                        held_x.append((starts[index] + snapshot['stage_train_MACs']) / 1e6)
                        held_y.append((metrics['val']['whole'] + metrics['test']['whole']) / total)
                ax.plot(train_x, train_y, color=colors[codec], linewidth=1.7, label=f'{codec} train')
                ax.plot(held_x, held_y, color=colors[codec], linestyle='--', marker='o', markersize=3,
                        linewidth=1.25, label=f'{codec} val+test (quarters)')
            boundaries = starts + [cumulative]
            for index, label in enumerate(stage_labels):
                left, right = boundaries[index]/1e6, boundaries[index+1]/1e6
                if index % 2 == 0:
                    ax.axvspan(left, right, color='#eeeeee', alpha=.35, zorder=-1)
                if index:
                    ax.axvline(left, color='#aaaaaa', linewidth=.7, linestyle=':')
                ax.text((left+right)/2, 1.065, label, ha='center', fontsize=7.5)
            ax.set(title=f"{'Fixed' if policy == 'F' else 'Growth'} / seed {seed}",
                   ylim=(-.04, 1.12), xlim=(0, 280), xticks=[0, 50, 100, 150, 200, 250], yticks=[0, .25, .5, .75, 1])
            ax.grid(axis='y', alpha=.17)
            if ci == 0:
                ax.set_ylabel('Current-stage exact free-run fraction')
            if ri == 1:
                ax.set_xlabel('Cumulative executed training matrix MACs (millions)')
    fig.suptitle('P035 lifecycle: current-format scores at the fixed stage clock', fontsize=17, weight='bold', y=.965)
    fig.text(.5, .925, 'Solid: train at each100 lessons + endpoint. Dashed: all val+test at fixed MAC quarters. No d1/d2 holdouts.', ha='center', fontsize=10)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, .895), ncol=4, frameon=False, fontsize=9)
    fig.text(.065, .1, 'Question domains and formats change at stage boundaries; a curve jump alone is not a forgetting estimate. Paired prior-correct cohorts are in the table.', fontsize=10)
    fig.text(.065, .06, 'Equal MAC caps allow Growth more lessons. Whole-lesson flooring: Fixed 277.794M, Growth 277.772868M actual training MACs per student.', fontsize=9, color='#555555')
    fig.text(.065, .025, 'Inference, growth probes, engineering and replay are counted separately. No outcome controls promotion, budget or checkpoint selection.', fontsize=9, color='#555555')
    fig.savefig(out / 'P035-stage-curves.png', dpi=160, facecolor='white')
    plt.close(fig)
    result = {'status': 'passed', 'figures': ['P035-paired-milestones.png', 'P035-stage-curves.png'],
              'students': 12, 'all_fixed_endpoints_included': True, 'matplotlib': matplotlib.__version__,
              'scope': 'stored-result plotting only; no training or inference', 'MPLCONFIGDIR': 'publication/mpl-cache (local only)'}
    (out / 'plot-checks.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
