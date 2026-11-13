"""Fixed P032 aggregation and split-coverage audit, without any training."""
import argparse
import itertools
import json
import statistics
from collections import Counter
from pathlib import Path


def read(p):
    return json.loads(p.read_text('utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    base = args.run
    manifest = read(base / 'manifest.json')
    results = read(base / 'training/results.json')
    assert len(results) == 24
    groups = []
    for hidden, ratio in itertools.product((72, 128), (70, 50)):
        rows = [r for r in results if r['H'] == hidden and r['new_percent'] == ratio]
        assert len(rows) == 6
        train_correct = val_correct = 0
        for r in rows:
            path = base / 'training' / f"{r['split']}-seed{r['seed']}-H{hidden}" / f'neg{ratio}'
            final = read(path / 'curve.json')[-1]
            train_correct += sum(v['whole'] for v in final['train']['by_op'].values())
            val_correct += sum(v['whole'] for v in final['validation']['by_op'].values())
            assert r['Neg']['target_updates'] == 15000
            assert sum(w['target_updates'] for w in r['warm']) == 8736
            assert r['total_train_dense_MACs'] == 23736 * 73 * hidden
            expected_new = 3000 * ratio // 100
            assert sum(n for op_value, n in r['Neg']['exposure'].items() if op_value.startswith('1:')) == expected_new
        test = [sum(v['whole'] for v in r['final_test']['by_op'].values()) for r in rows]
        groups.append({'H': hidden, 'new_percent': ratio, 'learners': 6,
                       'train': [train_correct, 72], 'validation': [val_correct, 12],
                       'test': [sum(test), 12], 'test_median_of_2': statistics.median(test),
                       'test_worst_of_2': min(test), 'both_test_correct_learners': sum(n == 2 for n in test),
                       'confirmed_train_val_learners': sum(r['Neg']['first_three_consecutive_passes'] is not None for r in rows),
                       'test_echo_before': sum(r['preNeg_test_echo']['by_op']['echo']['whole'] for r in rows),
                       'test_echo_after': sum(r['postNeg_test_echo']['by_op']['echo']['whole'] for r in rows),
                       'logical_train_MACs_per_learner': 23736 * 73 * hidden})
    coverage = {}
    for name, split in manifest['splits'].items():
        missing = []
        values = [format(v, '03b') for v in split['train']]
        for i, j in itertools.combinations(range(3), 2):
            present = {v[i] + v[j] for v in values}
            absent = sorted({'00', '01', '10', '11'} - present)
            if absent:
                missing.append({'information_bit_positions_msb_first': [i, j], 'absent_pairs': absent})
        coverage[name] = {'train_values': split['train'], 'heldout': split['val'] + split['test'],
                          'missing_pairwise_bit_combinations_in_train': missing,
                          'interpretation': 'valid preregistered splits; structured missing combinations limit broader conclusions'}
    cost = []
    for ratio in (70, 50):
        for label, at in [('same_Neg_MAC', 1687), ('same_total_train_MAC', 923)]:
            small = [r for r in results if r['H'] == 72 and r['new_percent'] == ratio]
            large = [r for r in results if r['H'] == 128 and r['new_percent'] == ratio]
            cost.append({'new_percent': ratio, 'comparison': label, 'H72_Neg_presentations': 3000,
                         'H128_Neg_presentations': at,
                         'H72_test': [sum(v['whole'] for r in small for v in r['final_test']['by_op'].values()), 12],
                         'H128_test': [sum(v['whole'] for r in large for v in r['cost_snapshots'][str(at)]['metrics']['by_op'].values()), 12],
                         'cost_H72': (23736 if label == 'same_total_train_MAC' else 15000) * 73 * 72,
                         'cost_H128': ((8736 if label == 'same_total_train_MAC' else 0) + at * 5) * 73 * 128})
    diag = read(base / 'diagnostic/truth-tables.json')
    paired = []
    for seed in (101, 202, 303):
        rows = [r for r in diag if r['checkpoint'].startswith(f'dynamic-{seed}/') and r['operator'] == 'echo' and r['value'] == 5]
        pre = next(r for r in rows if r['profile'] == '2a_echo_op2')
        post = next(r for r in rows if r['profile'] == '2b_add_neg')
        assert pre['Q'] == post['Q']
        paired.append({'seed': seed, 'Q': pre['Q'], 'before': pre['generated'], 'after': post['generated'],
                       'same_input_shape': True})
    truth = []
    for p in (base / 'training').glob('*/neg*/final-truth-table.json'):
        rows = read(p)
        root = p.parent.parent.name
        split_name = root.split('-')[0]
        test_value = manifest['splits'][split_name]['test'][0]
        truth.extend([r for r in rows if r['value'] == test_value])
    assert len(truth) == 48
    summary = {'status': 'verified', 'groups': groups, 'equal_MAC': cost, 'split_pair_coverage': coverage,
               'P030_same_Q_echo_reproduced': paired,
               'test_STOP_position_correct': [sum(r['STOP_position_correct'] for r in truth), 48],
               'test_bit_correct': [sum(r['bit_correct'][i] for r in truth) for i in range(4)],
               'physical_train_presentations_without_replay': 93888,
               'logical_total_presentations': 115776,
               'physical_target_updates_without_replay': 464832,
               'logical_target_updates': 569664,
               'physical_target_updates_including_replay': 929664,
               'B_growth': 'not executed: A does not support larger capacity as the present remedy'}
    (base / 'summary-table.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
