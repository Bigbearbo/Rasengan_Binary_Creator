"""Read-only fixed aggregation for P034 E900 and B0/B1; never trains a model."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

SEEDS = (101, 202, 303)
GROUPS = {'G0': 'S0', 'G1': 'C1'}
OPS = ('echo', 'neg')
SPLITS = {
    'S0': {'train': [0, 1, 2, 3, 5, 7], 'val': [4], 'test': [6]},
    'C0': {'train': [0, 1, 2, 3, 4, 7], 'val': [5], 'test': [6]},
    'S1': {'train': [0, 1, 2, 3, 4, 6], 'val': [5], 'test': [7]},
    'C1': {'train': [0, 1, 2, 3, 5, 6], 'val': [4], 'test': [7]},
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def first_error(actual, target):
    return next((i for i in range(max(len(actual), len(target)))
                 if (actual[i] if i < len(actual) else None) != (target[i] if i < len(target) else None)), None)


def truth_score(rows, values, op):
    selected = [row for row in rows if row['operator'] == op and row['value'] in values]
    assert len(selected) == len(values)
    first = Counter(str(first_error(row['generated'], row['target'])) for row in selected)
    teacher_first = Counter(str(first_error(''.join(t['prediction'] for t in row['teacher_forcing']), row['target'])) for row in selected)
    return {
        'whole': sum(row['whole_correct'] for row in selected), 'total': len(selected),
        'stop': sum(row['STOP_position_correct'] for row in selected),
        'bit_correct': [sum(row['bit_correct'][i] for row in selected) for i in range(4)],
        'teacher_correct': sum(t['prediction'] == t['target'] for row in selected for t in row['teacher_forcing']),
        'teacher_targets': 5 * len(selected),
        'teacher_whole': sum(all(t['prediction'] == t['target'] for t in row['teacher_forcing']) for row in selected),
        'teacher_STOP_correct': sum(row['teacher_forcing'][-1]['prediction'] == 'S' for row in selected),
        'first_wrong_position_free': dict(sorted(first.items())),
        'first_wrong_position_teacher': dict(sorted(teacher_first.items())),
        'records': [{'value': row['value'], 'target': row['target'], 'generated': row['generated'],
                     'whole_correct': row['whole_correct'],
                     'teacher_generated_under_correct_prefix': ''.join(t['prediction'] for t in row['teacher_forcing']),
                     'first_wrong_position_free': first_error(row['generated'], row['target']),
                     'first_wrong_position_teacher': first_error(''.join(t['prediction'] for t in row['teacher_forcing']), row['target'])}
                    for row in selected],
    }


def grade(rows, split):
    return {subset: {op: truth_score(rows, split[subset], op) for op in OPS}
            for subset in ('train', 'val', 'test')}


def verify_standard_metrics(scores, metrics):
    for subset in ('train', 'val', 'test'):
        for op in OPS:
            actual, expected = scores[subset][op], metrics[subset]['by_op'][op]
            for key in ('whole', 'total', 'stop', 'bit_correct', 'teacher_correct', 'teacher_targets'):
                assert actual[key] == expected[key], (subset, op, key)


def sum_scores(rows, arm, subset, op=None, teacher=False):
    scores = [r[arm][subset][name] for r in rows for name in (OPS if op is None else (op,))]
    return [sum(s['teacher_whole'] if teacher else s['whole'] for s in scores), sum(s['total'] for s in scores)]


def e900_summary(root, run):
    source = run / 'e900'
    compact = read(source / 'compact.json')
    results = read(source / 'results.json')
    manifest = read(source / 'manifest.json')
    assert compact['status'] == 'passed' and len(results) == 12
    assert compact['sources_SHA256_unchanged'] and compact['all12_trace_curve_logits_Adam_RNG_replay_equal']
    assert manifest['registered_before_new_training']
    assert sha(source / 'manifest.json') == compact['source_manifest_sha256']
    assert {(r['split'], r['seed']) for r in results} == {(s, seed) for s in SPLITS for seed in SEEDS}
    curves = []
    for result in results:
        folder = source / f"{result['split']}-seed{result['seed']}"
        curve = read(folder / 'curve.json')
        assert [point['echo_presentations'] for point in curve] == list(range(0, 901, 100))
        assert curve[0]['metrics'] == result['initial_metrics']
        assert curve[-1]['metrics'] == result['final_metrics']
        assert result['target_updates'] == 4500 and result['train_dense_MACs'] == 23652000
        assert result['historical_controls']['Neg70']['target_updates'] == 15000
        assert result['historical_controls']['E3000']['target_updates'] == 15000
        assert result['verification']['every_noop_full_state_and_counters_equal']
        curves.append(curve)
    curve_counts = []
    for i, at in enumerate(range(0, 901, 100)):
        curve_counts.append({
            'echo_presentations': at,
            **{subset: [sum(c[i]['metrics'][subset]['whole'] for c in curves),
                        sum(c[i]['metrics'][subset]['total'] for c in curves)] for subset in ('train', 'val', 'test')},
            'val_originally_correct_cohort': [sum(c[i]['metrics']['val']['whole'] for c in curves if c[0]['metrics']['val']['whole']),
                                              sum(bool(c[0]['metrics']['val']['whole']) for c in curves)],
            'val_originally_wrong_cohort': [sum(c[i]['metrics']['val']['whole'] for c in curves if not c[0]['metrics']['val']['whole']),
                                            sum(not bool(c[0]['metrics']['val']['whole']) for c in curves)],
        })
    return {
        'status': 'execution_and_replay_passed', 'new_training_learners': 12,
        'primary': compact['primary'], 'comparisons_by_split': compact['comparisons_by_split'],
        'per_split_seed': compact['per_split_seed'], 'curve_counts': curve_counts,
        'cost_per_learner': compact['fixed_cost_per_learner'],
        'source_manifest_sha256': sha(source / 'manifest.json'),
        'source_results_sha256': sha(source / 'results.json'),
        'source_audit_SHA_unchanged': compact['sources_SHA256_unchanged'],
        'historical_controls_retrained': False,
        'initially_wrong_validation_cases_are_not_forgetting': True,
        'wall_seconds_including_source_checks_and_replay': compact['wall_seconds_with_source_checks_and_replay'],
        'limitations': compact['limitations'],
    }


def attention_summary(root, run):
    baseline = read(run / 'baseline/compact.json')
    compact = read(run / 'b1/compact.json')
    results = read(run / 'b1/results.json')
    assert baseline['status'] == compact['status'] == 'passed'
    assert baseline['new_B0_training'] is False and baseline['read_only_Qs'] == 96
    assert len(results) == 6 and results == compact['results']
    assert {(r['group'], r['seed']) for r in results} == {(g, seed) for g in GROUPS for seed in SEEDS}
    paired = []
    for group, split_name in GROUPS.items():
        split = SPLITS[split_name]
        for seed in SEEDS:
            row = next(r for r in results if (r['group'], r['seed']) == (group, seed))
            before = next(r for r in baseline['rows'] if (r['group'], r['seed']) == (group, seed))
            b1_folder = run / 'b1' / f'{group}-seed{seed}'
            b0_folder = root / 'work/sle-p033/trial-20261112/timing' / f'{group}-seed{seed}-T1'
            truth0 = read(b0_folder / 'truth-table-3000.json')
            truth1 = read(b1_folder / 'truth-table-3000.json')
            assert len(truth0) == len(truth1) == 16
            grade0, grade1 = grade(truth0, split), grade(truth1, split)
            verify_standard_metrics(grade0, before['metrics'])
            verify_standard_metrics(grade1, row['metrics'])
            assert row['baseline']['metrics'] == before['metrics']
            assert (row['parameters'], before['parameters']) == (2596, 2595)
            assert row['target_updates'] == 15000 and row['presentations'] == 3000
            assert row['train_MACs'] == 1208880000
            assert row['all15000_update_full_state_digests_equal']
            assert row['replay_predictions_losses_curves_snapshot_arrays_final_optimizer_RNG_exact']
            assert row['strong_success_this_learner'] == all(t['whole_correct'] for t in truth1)
            course = next(c for c in baseline['courses'] if (c['group'], c['seed']) == (group, seed))
            assert row['course_sha256'] == course['sha256']
            curve = read(b1_folder / 'curve.json')
            assert len(curve) == 31 and [p['presentations'] for p in curve] == list(range(0, 3001, 100))
            assert curve[-1]['metrics'] == row['metrics']
            baseline_result = read(b0_folder / 'result.json')
            assert baseline_result['metrics'] == before['metrics']
            assert baseline_result['train_MACs'] == 78840000
            paired.append({
                'group': group, 'split': split_name, 'seed': seed,
                'B0': grade0, 'B1': grade1,
                'B0_whole': {subset: sum(s['whole'] for s in grade0[subset].values()) for subset in ('train', 'val', 'test')},
                'B1_whole': row['whole_correct'],
                'strong_success_this_learner': row['strong_success_this_learner'],
                'baseline_kind': 'historical P033 T1 training; only read-only inference this session',
                'new_B0_training': False,
                'B0_checkpoint_sha256': before['source_checkpoint_sha256'],
                'B1_checkpoint_sha256': sha(b1_folder / 'state-3000.npz'),
                'B1_curve_sha256': sha(b1_folder / 'curve.json'),
                'course_sha256': row['course_sha256'],
                'cost': {'B0_parameters': 2595, 'B1_parameters': 2596,
                         'B0_target_updates': 15000, 'B1_target_updates': 15000,
                         'B0_train_matrix_MACs': 78840000, 'B1_train_matrix_MACs': row['train_MACs'],
                         'B1_to_B0_MAC_ratio': row['train_MACs'] / 78840000,
                         'B0_persistent_array_bytes': baseline_result['parameter_optimizer_array_bytes'],
                         'B1_persistent_array_bytes': row['array_bytes'],
                         'B1_other_workload_counters': row['costs'],
                         'B1_seconds_training_updates': row['seconds_training_updates'],
                         'B1_seconds_primary_loop_probes_and_state_hashes': row['seconds_primary_loop_training_probes_state_fingerprints'],
                         'B1_seconds_replay': row['seconds_replay_loop'],
                         'B0_historical_seconds_training_and_probes': baseline_result['seconds_training_and_probes'],
                         'wall_times_have_different_instrumentation': True},
            })
    aggregate = {}
    for arm in ('B0', 'B1'):
        aggregate[arm] = {
            subset: {**{op: {'free': sum_scores(paired, arm, subset, op),
                             'teacher': sum_scores(paired, arm, subset, op, True)} for op in OPS},
                     'all_ops_free': sum_scores(paired, arm, subset),
                     'all_ops_teacher': sum_scores(paired, arm, subset, teacher=True)}
            for subset in ('train', 'val', 'test')}
    strong = all(r['strong_success_this_learner'] for r in paired)
    assert strong == compact['strong_success']
    for subset in ('train', 'val', 'test'):
        assert aggregate['B1'][subset]['all_ops_free'] == [compact['totals_whole_correct'][subset], compact['denominators'][subset]]
    differences = []
    for row in paired:
        b0 = row['B0_whole']['val'] + row['B0_whole']['test']
        b1 = row['B1_whole']['val'] + row['B1_whole']['test']
        differences.append({'group': row['group'], 'split': row['split'], 'seed': row['seed'],
                            'B0_heldout': [b0, 4], 'B1_heldout': [b1, 4], 'difference': b1-b0,
                            'outcome': 'improved' if b1 > b0 else 'worse' if b1 < b0 else 'tied'})
    return {
        'status': 'execution_and_replay_passed', 'new_B1_training_learners': 6,
        'B0_training_kind': 'historical P033 T1, no new B0 training;96 truth rows re-evaluated this session',
        'strong_success': strong, 'strong_success_learners': sum(r['strong_success_this_learner'] for r in paired),
        'strong_success_required': 'all six learners each12/12 train plus4/4 heldout exact free-run including STOP',
        'aggregate': aggregate, 'paired_heldout_differences': differences,
        'paired_improved': sum(r['outcome'] == 'improved' for r in differences),
        'paired_tied': sum(r['outcome'] == 'tied' for r in differences),
        'paired_worse': sum(r['outcome'] == 'worse' for r in differences),
        'per_split_seed': paired,
        'parameters': {'B0': 2595, 'B1': 2596, 'difference': 1, 'relative_difference_percent': 100 / 2595},
        'cost_per_learner': {'B0_matrix_MACs': 78840000, 'B1_matrix_MACs': 1208880000,
                             'B1_to_B0_ratio': 1208880000 / 78840000, 'equal_MACs': False,
                             'target_updates_both': 15000,
                             'scope': 'executed dense matmuls include masked cells; excludes LN/softmax/optimizer elementwise work, probes and replay; workload counters reported separately;array bytes are persistent arrays, not peak process memory'},
        'source_compact_sha256': sha(run / 'b1/compact.json'),
        'source_manifest_sha256': sha(run / 'b1/manifest.json'),
        'source_baseline_sha256': sha(run / 'baseline/compact.json'),
        'seconds_with_replay_and_evidence': compact['seconds_with_replay_and_evidence'],
        'limits': compact['limits'],
    }


def final_error_analysis(run):
    paths = sorted((run / 'b1').glob('G*-seed*/truth-table-3000.json'))
    assert len(paths) == 6
    rows = [row for path in paths for row in read(path)]
    assert len(rows) == 96
    result = {'scope': 'all six fixed final truth tables; no new inference or training',
              'sources': {path.relative_to(run).as_posix(): sha(path) for path in paths},
              'first_wrong_order': ['bit0', 'bit1', 'bit2', 'syntax_tail', 'STOP', 'whole_correct'],
              'sets': {}}
    for subset in ('train', 'heldout'):
        selected = [row for row in rows if (row['split'] == 'train') == (subset == 'train')]
        first = Counter(first_error(row['generated'], row['target']) for row in selected)
        teacher_first = Counter(first_error(''.join(t['prediction'] for t in row['teacher_forcing']), row['target']) for row in selected)
        free = [sum(row['bit_correct'][i] for row in selected) for i in range(4)]
        teacher = [sum(row['teacher_forcing'][i]['target'] == row['teacher_forcing'][i]['prediction'] for row in selected)
                   for i in range(5)]
        result['sets'][subset] = {
            'rows': len(selected), 'free_whole': sum(row['whole_correct'] for row in selected),
            'teacher_whole': sum(all(t['target'] == t['prediction'] for t in row['teacher_forcing']) for row in selected),
            'first_wrong_free': [first[i] for i in range(5)] + [first[None]],
            'first_wrong_teacher': [teacher_first[i] for i in range(5)] + [teacher_first[None]],
            'free_information_bits': free[:3], 'teacher_information_bits': teacher[:3],
            'free_syntax_tail': free[3], 'teacher_syntax_tail': teacher[3],
            'free_STOP_position': sum(row['STOP_position_correct'] for row in selected), 'teacher_STOP': teacher[4],
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--e900-only', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    run = root / 'work/sle-p034'
    out = args.out.resolve() if args.out else run / 'publication'
    out.mkdir(parents=True, exist_ok=True)
    result = {'id': 'P034-fixed-result-aggregation',
              'aggregation_source_sha256': sha(Path(__file__).resolve()),
              'scope': 'read-only results aggregation; no model calls or new training',
              'E900': e900_summary(root, run)}
    if not args.e900_only:
        result['B1'] = attention_summary(root, run)
        error_analysis = final_error_analysis(run)
        dump(out / 'b1-error-analysis.json', error_analysis)
        result['B1']['all_six_final_error_analysis'] = error_analysis['sets']
    dump(out / 'summary-table.json', result)
    compact = {'status': 'passed', 'scope': result['scope'],
               'E900': {key: result['E900'][key] for key in ('primary', 'comparisons_by_split', 'cost_per_learner')},
               'summary_table_sha256': sha(out / 'summary-table.json'),
               'source_aggregation_sha256': result['aggregation_source_sha256'],
               'new_blind_test': False}
    if 'B1' in result:
        compact['B1'] = {key: result['B1'][key] for key in ('strong_success', 'strong_success_learners', 'strong_success_required',
                                                        'aggregate', 'paired_heldout_differences', 'paired_improved', 'paired_tied', 'paired_worse',
                                                        'parameters', 'cost_per_learner', 'B0_training_kind')}
    else:
        compact['B1'] = {'status': 'not_aggregated_waiting_for_complete_six_learner_result'}
    dump(out / 'compact.json', compact)
    print(json.dumps({'status': 'passed', 'E900_test': [result['E900']['primary']['E900_test_correct'], 12],
                      'B1_aggregated': 'B1' in result,
                      'summary_table': str(out / 'summary-table.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
