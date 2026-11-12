"""Plot saved P034 scores only, using an existing local Matplotlib dependency."""
import argparse
import json
import os
from pathlib import Path
import sys


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--plot-deps', type=Path)
    parser.add_argument('--e900-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    run = root / 'work/sle-p034'
    out = args.out.resolve() if args.out else run / 'publication'
    out.mkdir(parents=True, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = str(out / 'mpl-cache')
    dependencies = args.plot_deps or root / 'work/sle-research-review/plot-deps'
    if not dependencies.is_dir():
        raise FileNotFoundError('Existing plot dependencies required; this script never installs packages')
    sys.path.insert(0, str(dependencies))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    summary = read(out / 'summary-table.json')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titleweight': 'bold', 'svg.hashsalt': 'P034-v1'})
    colors = {'train': '#2665a7', 'val': '#b45b14', 'test': '#087f7f'}
    outputs = []

    def save(fig, name):
        for extension in ('png', 'svg'):
            path = out / f'{name}.{extension}'
            fig.savefig(path, dpi=160, facecolor='white',
                        metadata={'Date': None, 'Creator': 'P034 saved-results plotting'} if extension == 'svg' else None)
            outputs.append(path.name)
        plt.close(fig)

    e900 = summary['E900']
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 7.8), gridspec_kw={'width_ratios': [1.2, 1]})
    fig.subplots_adjust(left=.12, right=.97, bottom=.19, top=.82, wspace=.33)
    paired = e900['per_split_seed']
    matrix = [[r['warm']['test'][0], r['E900']['test'][0],
               r['historical_Neg70']['test'][0], r['historical_E3000']['test'][0]] for r in paired]
    axes[0].imshow(matrix, cmap=ListedColormap(['#eedbd8', '#117e82']), vmin=0, vmax=1, aspect='auto')
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            axes[0].text(j, i, str(value), ha='center', va='center', color='white' if value else '#893c32', fontsize=10)
    axes[0].set(xticks=range(4), xticklabels=['Warm\n12/12', 'E900 (new)\n12/12', 'Neg70 (hist.)\n1/12', 'E3000 (hist.)\n12/12'],
                yticks=range(12), yticklabels=[f"{r['split']} / {r['seed']}" for r in paired],
                title='Paired Echo test: exact sequence + STOP')
    axes[0].tick_params(length=0, axis='both', pad=8)
    for boundary in (2.5, 5.5, 8.5):
        axes[0].axhline(boundary, color='white', linewidth=2)
    axes[0].legend(handles=[Patch(facecolor='#117e82', label='Correct'), Patch(facecolor='#eedbd8', label='Wrong')],
                   loc='lower center', bbox_to_anchor=(.5, -.15), ncol=2, frameon=False)
    curve = e900['curve_counts']
    x = [r['echo_presentations'] for r in curve]
    for subset in ('test', 'val'):
        y = [r[subset][0] / r[subset][1] for r in curve]
        axes[1].plot(x, y, color=colors[subset], linewidth=2.5, marker='o', markersize=4,
                     label=f"{subset}: {curve[-1][subset][0]}/{curve[-1][subset][1]}")
    axes[1].set(title='E900: fixed measurement curve', xlabel='Executed Echo lessons', ylabel='Exact free-run fraction',
                ylim=(-.05, 1.08), xlim=(-15, 915), xticks=[0, 100, 300, 500, 700, 900], yticks=[0, .25, .5, .75, 1])
    axes[1].grid(alpha=.18)
    axes[1].legend(loc='center right', bbox_to_anchor=(1, .72), frameon=False)
    train_counts = [tuple(r['train']) for r in curve]
    assert len(set(train_counts)) == 1
    axes[1].text(.04, .08, f"Train: {train_counts[0][0]}/{train_counts[0][1]} at all 10 points\n"
                  'Val: 6 initially correct retained; 6 initially wrong remain wrong',
                  transform=axes[1].transAxes, fontsize=9, linespacing=1.7)
    fig.suptitle('P034 E900: all 12 previously correct Echo tests retained', fontsize=17, weight='bold', y=.965)
    fig.text(.5, .89, 'Actual Neg70 Echo subsequence, unchanged order: 900 Echo, each trained value 150 times',
             ha='center', fontsize=11)
    fig.text(.08, .065, 'Matched Echo exposure only. E900: 4,500 updates / 23.652M dense MACs; Neg70: 15,000 / 78.840M.', fontsize=10)
    fig.text(.08, .035, 'Neg70 and E3000 are verified historical controls, not retrained. Previously viewed 3-bit domain; no new blind test.', fontsize=9, color='#555555')
    save(fig, 'P034-E900-paired')

    if not args.e900_only:
        attention = summary['B1']
        fig, axes = plt.subplots(3, 2, figsize=(14, 11.5), sharex=True, sharey=True)
        fig.subplots_adjust(left=.075, right=.98, bottom=.14, top=.86, hspace=.56, wspace=.15)
        for col, group in enumerate(('G0', 'G1')):
            for row_index, seed in enumerate((101, 202, 303)):
                ax = axes[row_index, col]
                pair = next(r for r in attention['per_split_seed'] if (r['group'], r['seed']) == (group, seed))
                curve = read(run / 'b1' / f'{group}-seed{seed}' / 'curve.json')
                for subset in ('train', 'val', 'test'):
                    values = [sum(s['whole'] for s in p['metrics'][subset]['by_op'].values()) /
                              sum(s['total'] for s in p['metrics'][subset]['by_op'].values()) for p in curve]
                    final = pair['B1_whole'][subset]
                    denominator = 12 if subset == 'train' else 2
                    ax.plot([p['presentations'] for p in curve], values, color=colors[subset],
                            label=f'{subset}: {final}/{denominator}', linewidth=1.8,
                            linestyle='-' if subset == 'train' else '--' if subset == 'val' else ':',
                            marker='o' if subset == 'test' else None, markersize=3, markevery=5)
                free_heldout = pair['B1_whole']['val'] + pair['B1_whole']['test']
                tf_heldout = sum(pair['B1'][subset][op]['teacher_whole'] for subset in ('val', 'test') for op in ('echo', 'neg'))
                tf_train = sum(pair['B1']['train'][op]['teacher_whole'] for op in ('echo', 'neg'))
                baseline_heldout = pair['B0_whole']['val'] + pair['B0_whole']['test']
                ax.set(title=f"{group} / {pair['split']} / seed {seed}", ylim=(-.05, 1.06), xlim=(0, 3000),
                       xticks=[0, 1000, 2000, 3000], yticks=[0, .25, .5, .75, 1])
                ax.text(0, 1.14, f"Final free / teacher: train {pair['B1_whole']['train']}/12 / {tf_train}/12; "
                        f'heldout {free_heldout}/4 / {tf_heldout}/4', transform=ax.transAxes, fontsize=9, color='#444444')
                ax.text(.02, .08, f'Historical B0 final heldout: {baseline_heldout}/4', transform=ax.transAxes, fontsize=8.5,
                        bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': .85})
                ax.grid(alpha=.17)
                ax.legend(loc='upper right', fontsize=8, frameon=False)
                if col == 0:
                    ax.set_ylabel('Exact free-run fraction')
                if row_index == 2:
                    ax.set_xlabel('Executed mixed lessons')
        score = attention['aggregate']['B1']
        headline = 'Strong criterion met' if attention['strong_success'] else 'Strong criterion not met'
        fig.suptitle(f'P034 B1: {headline}', fontsize=18, weight='bold', y=.975)
        fig.text(.5, .935, f"Final B1 free-run: train {score['train']['all_ops_free'][0]}/72, "
                 f"val {score['val']['all_ops_free'][0]}/12, test {score['test']['all_ops_free'][0]}/12. "
                 'All six fixed runs included.', ha='center', fontsize=11)
        fig.text(.5, .905, 'B0: 2,595 parameters; B1: 2,596. Equal 15,000 target updates; B1 uses 15.333x training matrix MACs.',
                 ha='center', fontsize=10)
        fig.text(.075, .065, 'Strong criterion: each of six learners must answer all 12 taught + all 4 heldout operator-value pairs, including STOP.', fontsize=10)
        fig.text(.075, .035, 'Teacher = predictions under the correct answer prefix. B0 training is historical; this session only re-evaluated its fixed models.', fontsize=9, color='#555555')
        save(fig, 'P034-attention-paired')
    report = {'status': 'passed', 'figures': outputs, 'matplotlib': matplotlib.__version__,
              'scope': 'saved-result plotting only; no scientific training or inference', 'MPLCONFIGDIR': 'publication/mpl-cache (local only)'}
    (out / 'plot-checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
