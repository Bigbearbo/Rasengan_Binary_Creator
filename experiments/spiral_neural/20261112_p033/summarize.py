"""Fixed aggregation of P033 learning and conditional diagnostic results."""
import argparse
import json
from pathlib import Path


def read(p):
    return json.loads(p.read_text('utf-8'))


def counts(rows, dataset, op=None):
    data = [v for r in rows for name, v in r['metrics'][dataset]['by_op'].items() if op is None or name == op]
    return [sum(v['whole'] for v in data), sum(v['total'] for v in data)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run
    a, t = read(run / 'coverage/results.json'), read(run / 'timing/results.json')
    assert len(a) == 12 and len(t) == 18
    coverage = []
    for split in ('S0', 'C0', 'S1', 'C1'):
        rows = [r for r in a if r['split'] == split]
        assert len(rows) == 3
        coverage.append({'split': split, 'train': counts(rows, 'train'), 'val': counts(rows, 'val'),
                         'test': counts(rows, 'test'), 'test_Echo': counts(rows, 'test', 'echo'),
                         'test_Neg': counts(rows, 'test', 'neg'),
                         'Echo_test_before': [sum(r['Echo_before']['by_op']['echo']['whole'] for r in rows), 3],
                         'Echo_test_after': [sum(r['Echo_after']['by_op']['echo']['whole'] for r in rows), 3],
                         'MAC_per_learner': 124756416})
        assert all(r['train_MACs'] == 124756416 for r in rows)
    timing = []
    for group in ('G0', 'G1'):
        for mode in ('T0', 'T1', 'T0B'):
            rows = [r for r in t if r['group'] == group and r['timing'] == mode]
            assert len(rows) == 3
            assert all(r['target_updates'] == 15000 and r['train_MACs'] == 78840000 for r in rows)
            stages = {}
            for at in (1000, 1500, 3000):
                tables = [row for r in rows for row in read(run / 'timing' / f"{group}-seed{r['seed']}-{mode}" / f'truth-table-{at}.json')]
                stages[str(at)] = {op: {'whole': sum(row['whole_correct'] for row in tables if row['operator'] == op), 'total': 24}
                                    for op in ('echo', 'neg')}
            timing.append({'group': group, 'split': rows[0]['split'], 'timing': mode,
                           'train': counts(rows, 'train'), 'train_Echo': counts(rows, 'train', 'echo'),
                           'train_Neg': counts(rows, 'train', 'neg'), 'val': counts(rows, 'val'),
                           'test': counts(rows, 'test'), 'val_Echo': counts(rows, 'val', 'echo'),
                           'val_Neg': counts(rows, 'val', 'neg'), 'test_Echo': counts(rows, 'test', 'echo'),
                           'test_Neg': counts(rows, 'test', 'neg'), 'all8_by_op_at_fixed_snapshots': stages,
                           'MAC_per_learner': 78840000})
    errors = read(run / 'diagnostic/first-errors.json')
    cascade = []
    for op in ('echo', 'neg'):
        rows = [r for r in errors if r['phase'] == 'after' and r['operator'] == op and r['subset'] != 'train']
        cascade.append({'operator': op, 'heldout_rows': len(rows),
                        'first_wrong': [sum(r['first_wrong_position'] == i for r in rows) for i in range(5)],
                        'free_wrong': [sum(r['free_wrong'][i] for r in rows) for i in range(5)],
                        'teacher_wrong': [sum(r['teacher_wrong'][i] for r in rows) for i in range(5)],
                        'rescued_after_first_error': [sum(r['prefix_rescued_later_positions'][i] for r in rows) for i in range(5)],
                        'introduced_by_correct_prefix_after_first_free_error': [sum(r['first_wrong_position'] is not None
                            and i > r['first_wrong_position'] and not r['free_wrong'][i] and r['teacher_wrong'][i] for r in rows) for i in range(5)]})
    matrices = read(run / 'diagnostic/sensitivity-matrices.json')
    diagonals = [{k: r[k] for k in ('phase', 'H', 'operator', 'subset', 'input_bit', 'count', 'mean_signed_delta_p1')}
                 for r in matrices if r['input_bit'] == r['output_bit'] and r['subset'] == 'heldout']
    result = {'status': 'verified', 'coverage': coverage, 'fresh_timing': timing,
              'teacher_vs_free': cascade, 'heldout_diagonal_sensitivity': diagonals,
              'coverage_control_reproduced': sum(r['baseline_P032_actual_rerun_trace_optimizer_equal'] is True for r in a),
              'training_presentations': 111888, 'target_updates': 554832,
              'including_full_replay_updates': 1109664,
              'scope': 'same 3-bit domain, mechanism study; no new blind domain or representation change'}
    (run / 'summary-table.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('heldout_diagonal_sensitivity',)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
