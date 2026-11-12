"""Fixed read-only P035 aggregation; rejects incomplete12-student experiments."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import codec_course as course

ARM_ORDER = ('SF', 'SG', 'HF', 'HG')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def metric(rows, stage):
    result = {}
    for subset in ('train', 'val', 'test', 'all'):
        selected = [r for r in rows if subset == 'all' or r['subset'] == subset]
        ops = {}
        for op in stage.ops:
            own = [r for r in selected if r['operator'] == op]
            teacher_targets = sum(len(r['teacher_forcing']) for r in own)
            ops[course.OP_NAMES[op]] = {
                'whole': sum(r['whole_correct'] for r in own), 'total': len(own),
                'STOP_position_correct': sum(r['STOP_position_correct'] for r in own),
                'overflow': sum(r['overflow'] for r in own), 'malformed': sum(r['malformed'] for r in own),
                'information_bit_correct': [sum(r['information_bit_correct'][i] for r in own) for i in range(stage.n_data)],
                'syntax_tail_correct': sum(r['syntax_tail_correct'] for r in own),
                'teacher_correct': sum(t['target'] == t['prediction'] for r in own for t in r['teacher_forcing']),
                'teacher_targets': teacher_targets,
                'teacher_whole': sum(all(t['target'] == t['prediction'] for t in r['teacher_forcing']) for r in own),
                'CE_mean': sum(t['target_CE'] for r in own for t in r['teacher_forcing']) / teacher_targets if teacher_targets else None,
            }
        result[subset] = {'by_op': ops, 'whole': sum(r['whole_correct'] for r in selected), 'total': len(selected)}
    return result


def verify_truth(rows, codec, stage):
    expected = {(op, value) for op in stage.ops for value in range(2 ** stage.n_data)}
    assert {(r['operator'], r['value']) for r in rows} == expected and len(rows) == len(expected)
    for row in rows:
        op, value = row['operator'], row['value']
        target = course.answer(stage, op, value) + 'S'
        assert row['Q'] == course.encode(codec, stage, op, value) and row['target'] == target
        assert row['whole_correct'] == (row['generated'] == target and not row['overflow'])
        assert row['subset'] == next(name for name in ('train', 'val', 'test') if value in getattr(stage, name))
        assert len(row['teacher_forcing']) == stage.targets_per_lesson
        assert ''.join(t['target'] for t in row['teacher_forcing']) == target
    return metric(rows, stage)


def error_summary(rows, n_data):
    result = {}
    for subset in ('train', 'heldout', 'all'):
        selected = [r for r in rows if subset == 'all' or (r['subset'] == 'train') == (subset == 'train')]
        first = Counter(str(r['first_error_position_zero_based']) for r in selected)
        result[subset] = {
            'rows': len(selected), 'whole_free': sum(r['whole_correct'] for r in selected),
            'whole_teacher': sum(all(t['target'] == t['prediction'] for t in r['teacher_forcing']) for r in selected),
            'information_bits_free': [sum(r['information_bit_correct'][i] for r in selected) for i in range(n_data)],
            'information_bits_teacher': [sum(r['teacher_forcing'][i]['target'] == r['teacher_forcing'][i]['prediction'] for r in selected) for i in range(n_data)],
            'syntax_tail_free': sum(r['syntax_tail_correct'] for r in selected),
            'STOP_free': sum(r['STOP_position_correct'] for r in selected),
            'STOP_teacher': sum(r['teacher_forcing'][-1]['prediction'] == 'S' for r in selected),
            'first_error_free': dict(sorted(first.items())),
        }
    return result


def retention(previous_truth, quarter_truth, summary, stage):
    if previous_truth is None:
        return {'status': 'initial_stage_no_prior_semantic_cohort'}
    prior = {(r['operator'], r['value']): r['whole_correct'] for r in previous_truth}
    cohort = {key for key, correct in prior.items() if correct}
    observations = []
    for snapshot, rows in zip(summary['snapshots'], quarter_truth, strict=True):
        current = {(r['operator'], r['value']): r['whole_correct'] for r in rows}
        assert set(prior) <= set(current)
        observations.append({
            'fraction_percent': snapshot['fraction_percent'], 'lessons': snapshot['lesson'],
            'stage_train_MACs': snapshot['stage_train_MACs'],
            'previously_correct_retained': sum(current[key] for key in cohort), 'previously_correct_total': len(cohort),
            'all_prior_semantics_correct': sum(current[key] for key in prior), 'all_prior_semantics_total': len(prior),
        })
    lost_at_entry = len(cohort) - observations[0]['previously_correct_retained']
    recovery = next((point for point in observations if point['previously_correct_retained'] == len(cohort)), None) if cohort else None
    first_loss_index = next((i for i, point in enumerate(observations)
                             if point['previously_correct_retained'] < len(cohort)), None) if cohort else None
    recovery_after_loss = next((point for point in observations[first_loss_index + 1:]
                               if point['previously_correct_retained'] == len(cohort)), None) if first_loss_index is not None else None
    return {'status': 'current_format_semantic_retention',
            'prior_format_correct': [len(cohort), len(prior)],
            'prior_wrong_not_counted_as_forgetting': len(prior)-len(cohort),
            'lost_at_format_or_semantic_stage_entry': lost_at_entry,
            'lost_at_stage_end': len(cohort) - observations[-1]['previously_correct_retained'],
            'first_observed_loss': observations[first_loss_index] if first_loss_index is not None else None,
            'first_observed_recovery_after_observed_loss': recovery_after_loss,
            'entry_before_training': observations[0], 'observations_at_fixed_MAC_quarters': observations,
            'first_observed_full_retention_or_recovery': recovery,
            'resolution': 'Only stored0/25/50/75/100percent full-truth snapshots; no invented exact recovery update.',
            'is_same_raw_growth_invariance': False}


def aggregate(run, out):
    compact, results, manifest = read(run / 'compact.json'), read(run / 'results.json'), read(run / 'manifest.json')
    assert compact['status'] == 'passed' and compact['new_students'] == 12
    assert compact['all_students_retained'] and compact['all_targets_states_snapshots_curves_Adam_birth_rng_replayed_exact']
    assert len(results) == 12 and compact['results'] == results
    keys = {(c, p, s) for c in course.CODECS for p in ('F', 'G') for s in course.SEEDS}
    assert {(r['codec'], r['policy'], r['seed']) for r in results} == keys
    assert manifest['no_holdout_driven_decisions']
    for name, expected in manifest['source_sha256'].items():
        assert sha(Path(__file__).parent / name) == expected, ('frozen source changed', name)
    students = []
    for codec, policy, seed in sorted(keys, key=lambda x: (ARM_ORDER.index(x[0]+x[1]), x[2])):
        result = next(r for r in results if (r['codec'], r['policy'], r['seed']) == (codec, policy, seed))
        folder = run / f'{codec}-{policy}-seed{seed}'
        assert read(folder / 'result.json') == result
        assert result['all_targets_losses_states_snapshots_curves_optimizer_rng_replayed_exact']
        assert len(result['stages']) == len(course.STAGES)
        previous, stage_rows = None, []
        interface = read(folder / 'interface-exposure.json')
        for stage, summary in zip(course.STAGES, result['stages'], strict=True):
            stage_folder = folder / stage.name
            assert read(stage_folder / 'summary.json') == summary
            budget = course.lesson_budget(stage, policy)
            assert summary['budget'] == budget
            assert summary['target_updates'] == budget['target_updates']
            assert summary['train_dense_MACs'] == budget['executed_train_MACs']
            assert summary['train_forward_dense_MACs'] + summary['train_backward_dense_MACs'] == summary['train_dense_MACs']
            assert summary['trace_targets'] == summary['target_updates']
            assert sha(stage_folder / 'token-trace.jsonl.gz') == summary['trace_sha256']
            lessons = read(run / 'courses' / f'{policy}-seed{seed}' / f'{stage.name}.json')
            assert [tuple(pair) for pair in lessons] == course.semantic_course(stage, seed, budget['lessons'])
            quarter_truth = []
            for fraction, snapshot in zip((0, 25, 50, 75, 100), summary['snapshots'], strict=True):
                assert snapshot['fraction_percent'] == fraction
                rows = read(stage_folder / f'truth-{fraction}.json')
                actual_metrics = verify_truth(rows, codec, stage)
                assert actual_metrics == snapshot['metrics']
                assert snapshot['stage_train_MACs'] <= snapshot['MAC_threshold']
                quarter_truth.append(rows)
            assert summary['metrics_entry'] == metric(quarter_truth[0], stage)
            assert summary['metrics_final'] == metric(quarter_truth[-1], stage)
            curves = read(stage_folder / 'curve.json')
            assert curves[0]['lessons'] == 0 and curves[-1]['lessons'] == budget['lessons']
            assert curves[0]['metrics'] == summary['metrics_entry'] and curves[-1]['metrics'] == summary['metrics_final']
            assert summary['growth']['old_arrays_moments_birth_and_step_exact']
            assert summary['growth']['max_same_raw_logit_difference'] < 2e-6
            exposure = [r for r in interface if r['stage'] == stage.name]
            stage_rows.append({
                'stage': stage.name, 'transition': stage.transition, 'budget': budget,
                'entry': summary['metrics_entry'], 'final': summary['metrics_final'],
                'snapshots': summary['snapshots'],
                'first_observed_three_consecutive_fit_passes': summary['first_observed_three_consecutive_fit_passes'],
                'same_raw_growth_check': summary['growth'],
                'current_format_retention': retention(previous, quarter_truth, summary, stage),
                'old_block_drift': summary['drift_old_overlapping_blocks'],
                'prior_raw_prefix_target_conflicts': {
                    'unique_AST_target_positions': sum(len(row['prefix_labels']) for row in exposure),
                    'positions_with_different_prior_stage_target': sum(item['prior_different_target_seen'] for row in exposure for item in row['prefix_labels']),
                    'lesson_weighted_conflict_target_positions': sum(row['presentations'] * sum(item['prior_different_target_seen'] for item in row['prefix_labels']) for row in exposure),
                    'interpretation': 'Exact raw prefix/teacher-history diagnostic; not by itself a causal explanation of scores.'},
                'final_error_summary': error_summary(quarter_truth[-1], stage.n_data),
                'curve_sha256': sha(stage_folder / 'curve.json'), 'trace_sha256_local_only': summary['trace_sha256'],
            })
            previous = quarter_truth[-1]
        final_truth = read(folder / 'final-truth.json')
        assert final_truth == previous
        primary = course.milestone_score({(r['operator'], r['value']): r['whole_correct'] for r in final_truth})
        assert primary == result['primary']
        assert read(folder / 'final-failures.json') == [r for r in final_truth if not r['whole_correct']]
        assert result['final_parameters'] == 2073
        planned = [course.semantic_course(stage, seed, course.lesson_budget(stage, policy)['lessons']) for stage in course.STAGES]
        assert read(folder / 'exposure-ledger.json') == course.exposure_ledger(planned)
        students.append({
            'codec': codec, 'codec_name': result['codec_name'], 'policy': policy, 'seed': seed,
            'primary': primary, 'final_metrics': stage_rows[-1]['final'], 'stages': stage_rows,
            'target_updates': result['target_updates'], 'training_dense_MAC_cap': result['training_dense_MAC_cap'],
            'executed_training_dense_MACs': result['executed_training_dense_MACs'],
            'unused_training_MACs_not_carried': result['unused_training_MACs_not_carried'],
            'inference_dense_MACs_including_initialization_and_growth': result['inference_dense_MACs_including_initialization_and_growth'],
            'array_bytes': result['array_bytes'], 'primary_seconds': result['primary_seconds'], 'replay_seconds': result['replay_seconds'],
            'initial_state_sha256': result['initial_state_sha256'], 'final_state_sha256': result['final_state_sha256'],
            'result_sha256': sha(folder / 'result.json'), 'all_full_replay_checks_passed': True,
        })
    interactions = []
    for seed in course.SEEDS:
        scores = {row['codec']+row['policy']: row['primary']['score'] for row in students if row['seed'] == seed}
        for policy in ('F', 'G'):
            own = [row for row in students if row['seed'] == seed and row['policy'] == policy]
            assert own[0]['initial_state_sha256'] == own[1]['initial_state_sha256']
        interactions.append({'seed': seed, 'scores': scores,
                             'S_growth_minus_fixed': scores['SG']-scores['SF'],
                             'H_growth_minus_fixed': scores['HG']-scores['HF'],
                             'interaction': (scores['SG']-scores['SF'])-(scores['HG']-scores['HF'])})
    assert interactions == compact['per_seed_interactions']
    per_arm = []
    for arm in ARM_ORDER:
        own = [r for r in students if r['codec']+r['policy'] == arm]
        per_arm.append({'arm': arm, 'scores_by_seed': {str(r['seed']): r['primary']['score'] for r in own},
                        'mean_ordinal_score_descriptive_only': sum(r['primary']['score'] for r in own)/3,
                        'final_by_subset': {subset: [sum(r['final_metrics'][subset]['whole'] for r in own), sum(r['final_metrics'][subset]['total'] for r in own)] for subset in ('train', 'val', 'test', 'all')},
                        'milestone_pass_counts': [sum(r['primary']['blocks'][i]['passed'] for r in own) for i in range(4)]})
    result = {'id': 'P035-fixed-result-aggregation', 'status': 'passed', 'students': students,
              'all_primary_and_replay_completed': True, 'new_students': 12, 'all_failures_retained': True,
              'primary': {'scale': 'highest consecutive cumulative milestone0..4, exact free-run+STOP in final current format',
                          'nested_milestones_are_independent_skills': False, 'per_arm': per_arm, 'per_seed_interactions': interactions},
              'primary_target_updates': compact['primary_target_updates'],
              'primary_training_dense_MACs': compact['primary_training_dense_MACs'],
              'additional_replay_training_dense_MACs': compact['additional_replay_training_dense_MACs'],
              'primary_inference_dense_MACs': compact['primary_inference_dense_MACs'],
              'wall_seconds_primary_replay_evidence': compact['wall_seconds_primary_replay_evidence'],
              'scope': 'read-only fixed aggregation; no new model inference, training, seed/checkpoint selection',
              'source_compact_sha256': sha(run / 'compact.json'), 'source_manifest_sha256': sha(run / 'manifest.json'),
              'aggregation_source_sha256': sha(Path(__file__).resolve()), 'limitations': compact['limitations']}
    dump(out / 'summary-table.json', result)
    public_compact = {key: value for key, value in result.items() if key != 'students'}
    public_compact['student_rows'] = [{key: row[key] for key in ('codec', 'policy', 'seed', 'primary', 'final_metrics', 'target_updates', 'executed_training_dense_MACs', 'unused_training_MACs_not_carried')} for row in students]
    public_compact['summary_table_sha256'] = sha(out / 'summary-table.json')
    dump(out / 'compact.json', public_compact)
    # A small report-facing index; no full logits, traces or tables in chat.
    start = datetime.fromisoformat(manifest['registered_UTC_before_first_scientific_update'])
    completed_artifact = datetime.fromtimestamp((run / 'compact.json').stat().st_mtime, timezone.utc)
    taipei = timezone(timedelta(hours=8))
    def whole_counts(metrics):
        return {subset: [metrics[subset]['whole'], metrics[subset]['total']] for subset in ('train', 'val', 'test')}
    def stage_fact(stage):
        prior = stage['current_format_retention']
        retention_fact = prior if prior['status'] == 'initial_stage_no_prior_semantic_cohort' else {
            key: prior[key] for key in ('prior_format_correct', 'prior_wrong_not_counted_as_forgetting',
                'lost_at_format_or_semantic_stage_entry', 'lost_at_stage_end',
                'first_observed_full_retention_or_recovery', 'first_observed_recovery_after_observed_loss', 'resolution')}
        return {'stage': stage['stage'], 'transition': stage['transition'], 'budget': stage['budget'],
                'entry_counts': whole_counts(stage['entry']), 'final_counts': whole_counts(stage['final']),
                'first_three_fit_passes': stage['first_observed_three_consecutive_fit_passes'],
                'prior_correct_cohort': retention_fact,
                'same_raw_growth_max_logit_difference': stage['same_raw_growth_check']['max_same_raw_logit_difference'],
                'prior_raw_prefix_target_conflicts': stage['prior_raw_prefix_target_conflicts']}
    facts = {
        'id': 'P035-report-facts', 'source_summary_sha256': sha(out / 'summary-table.json'),
        'scope': 'all12 fixed students; stored-result aggregation only; no new inference or training',
        'primary_rows': [{'codec': row['codec'], 'policy': row['policy'], 'seed': row['seed'],
                          'score': row['primary']['score'],
                          'cumulative_block_correct_total': [[block['whole'], block['total']] for block in row['primary']['blocks']]}
                         for row in students],
        'interactions': interactions,
        'final_per_operator': [{
            'codec': row['codec'], 'policy': row['policy'], 'seed': row['seed'],
            'free': {subset: {op: [score['whole'], score['total']] for op, score in row['final_metrics'][subset]['by_op'].items()}
                     for subset in ('train', 'val', 'test')},
            'teacher_whole': {subset: {op: [score['teacher_whole'], score['total']] for op, score in row['final_metrics'][subset]['by_op'].items()}
                              for subset in ('train', 'val', 'test')},
        } for row in students],
        'stagewise': [{
            'codec': row['codec'], 'policy': row['policy'], 'seed': row['seed'],
            'stages': [stage_fact(stage) for stage in row['stages']],
        } for row in students],
        'exposure_warning': 'Heldout values4/6 are absent from training operands. Neg1 returns6 andNeg3 returns4 in the training teacher responses; do not call these numbers unseen in every semantic role.',
        'training_response_values_4_and_6': [],
        'costs': {'primary_target_updates': compact['primary_target_updates'],
                  'additional_replay_target_updates': compact['additional_replay_target_updates'],
                  'primary_training_dense_MACs': compact['primary_training_dense_MACs'],
                  'additional_replay_training_dense_MACs': compact['additional_replay_training_dense_MACs'],
                  'reported_primary_inference_dense_MACs': compact['primary_inference_dense_MACs'],
                  'inference_counter_scope': 'Reported per-student counters include copied template initialization counters. They are not a unique physical-system operation count; initialization templates are shared across codecs.',
                  'per_student': [{key: row[key] for key in ('codec', 'policy', 'seed', 'target_updates', 'training_dense_MAC_cap',
                                  'executed_training_dense_MACs', 'unused_training_MACs_not_carried', 'array_bytes', 'primary_seconds', 'replay_seconds')}
                                  for row in students]},
        'time': {'manifest_registered_before_first_scientific_update_UTC': start.isoformat(),
                 'manifest_registered_Taipei': start.astimezone(taipei).isoformat(),
                 'compact_artifact_last_write_UTC': completed_artifact.isoformat(),
                 'compact_artifact_last_write_Taipei': completed_artifact.astimezone(taipei).isoformat(),
                 'wall_seconds_primary_replay_evidence': compact['wall_seconds_primary_replay_evidence'],
                 'timestamp_limit': 'Runner does not store an absolute process-exit timestamp. Compact artifact timestamp is file metadata, not an invented exact process exit; root launch/exit record can supply that separately.'},
    }
    for row in students:
        response_counts = Counter()
        for item in read(run / f"{row['codec']}-{row['policy']}-seed{row['seed']}" / 'interface-exposure.json'):
            response_counts[int(item['target'][:-2], 2)] += item['presentations']
        facts['training_response_values_4_and_6'].append({'codec': row['codec'], 'policy': row['policy'], 'seed': row['seed'],
                                                        'value4': response_counts[4], 'value6': response_counts[6]})
    dump(out / 'report-facts.json', facts)
    print(json.dumps({'status': 'passed', 'students': 12, 'scores': interactions,
                      'summary_table': str(out / 'summary-table.json')}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[2] / 'work/sle-p035/publication')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    aggregate(args.run.resolve(), args.out.resolve())


if __name__ == '__main__':
    main()
