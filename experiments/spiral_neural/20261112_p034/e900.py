"""P034 E900: filter the actual archived Neg70 trace, then replay every update.

Historical P033 controls are verified and evaluated read-only. No historical
training, checkpoint or source file is changed by this runner.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import gzip
import hashlib
import importlib
import json
import platform
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np

SEEDS = (101, 202, 303)
SPLIT_ORDER = ('S0', 'C0', 'S1', 'C1')
OFFSETS = {'S0': 0, 'C0': 0, 'S1': 10000, 'C1': 10000}
SPLITS = {
    'S0': {'train': [0, 1, 2, 3, 5, 7], 'val': [4], 'test': [6]},
    'C0': {'train': [0, 1, 2, 3, 4, 7], 'val': [5], 'test': [6]},
    'S1': {'train': [0, 1, 2, 3, 4, 6], 'val': [5], 'test': [7]},
    'C1': {'train': [0, 1, 2, 3, 5, 6], 'val': [4], 'test': [7]},
}
P033_COMMIT = 'e217bd0fd6cfe654062c3615ee2aa73a36d1ca71'
PUBLIC_BASE = 'experiments/spiral_neural/20261112_p033/'
SOURCE_NAMES = ('p030_reference.py', 'p032_reference.py', 'p033.py', 'echo_only_followup.py')
CHECK_VERSION = 'P034-E900-v1'


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2), encoding='utf-8')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return sha_bytes(path.read_bytes())


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def relative(root, path):
    return path.relative_to(root).as_posix()


def frozen_state(path):
    with np.load(path, allow_pickle=False) as state:
        return {name: state[name].copy() for name in state.files}


def state_signature(state):
    """Hash dtype, shape and exact bytes of every parameter/optimizer/RNG field."""
    result = {}
    groups = {name: [f'{name}{i}' for i in range(4)] for name in ('p', 'm', 'v', 'birth')}
    groups['step_shape_rng'] = ['t', 'L', 'H', 'growth_rng']
    assert set(state) == set(sum(groups.values(), []))
    for label, names in groups.items():
        digest = hashlib.sha256()
        for name in names:
            array = np.asarray(state[name])
            digest.update(canonical([name, array.dtype.str, list(array.shape)]))
            digest.update(array.tobytes(order='C'))
        result[label] = digest.hexdigest()
    result['all'] = sha_bytes(canonical(result))
    return result


def counters(net):
    return [net.t, net.train_macs, net.inference_macs, net.inference_calls]


def first_wrong(actual, target):
    for i in range(max(len(actual), len(target))):
        got = actual[i] if i < len(actual) else None
        want = target[i] if i < len(target) else None
        if got != want:
            return {'position_zero_based': i, 'target': want, 'actual': got}
    return None


def truth_table(old, net):
    # Echo-only profile is the archived native op2/data3 grammar without END.
    p = old.ref.PHASES[3]
    rows = []
    for value in range(8):
        row = old.truth_row(net, p, 0, value)
        teacher = ''.join(item['prediction'] for item in row['teacher_forcing'])
        row['teacher_generated_under_correct_prefix'] = teacher
        row['teacher_whole_correct'] = teacher == row['target']
        row['first_wrong_token_free'] = first_wrong(row['generated'], row['target'])
        row['first_wrong_token_teacher'] = first_wrong(teacher, row['target'])
        row['first_wrong_information_bit_free'] = next(
            (i for i in range(3) if i >= len(row['generated']) or row['generated'][i] != row['target'][i]), None)
        row['first_wrong_answer_bit_free'] = next(
            (i for i in range(4) if i >= len(row['generated']) or row['generated'][i] != row['target'][i]), None)
        row['teacher_STOP_correct'] = row['teacher_forcing'][-1]['prediction'] == 'S'
        rows.append(row)
    return rows


def subset_score(rows, values):
    selected = [row for row in rows if row['value'] in values]
    assert len(selected) == len(values)
    return {
        'values': values,
        'whole': sum(row['whole_correct'] for row in selected),
        'total': len(selected),
        'information_bit_correct': [sum(row['bit_correct'][i] for row in selected) for i in range(3)],
        'syntax_tail_correct': sum(row['bit_correct'][3] for row in selected),
        'answer_bit_correct': [sum(row['bit_correct'][i] for row in selected) for i in range(4)],
        'STOP_position_correct': sum(row['STOP_position_correct'] for row in selected),
        'teacher_whole': sum(row['teacher_whole_correct'] for row in selected),
        'teacher_correct': sum(item['prediction'] == item['target'] for row in selected for item in row['teacher_forcing']),
        'teacher_targets': len(selected) * 5,
        'teacher_STOP_correct': sum(row['teacher_STOP_correct'] for row in selected),
        'first_wrong_answer_bit_free': {str(row['value']): row['first_wrong_answer_bit_free'] for row in selected},
        'first_wrong_token_free': {str(row['value']): row['first_wrong_token_free'] for row in selected},
        'free_outputs': {str(row['value']): row['generated'] for row in selected},
    }


def grade_table(rows, split):
    return {name: subset_score(rows, split[name]) for name in ('train', 'val', 'test')}


def measure(old, net, split, echo_count, slot):
    before = net.state()
    rows = truth_table(old, net)
    assert old.ref.equal_state(before, net.state())
    return {
        'echo_presentations': echo_count,
        'external_slot': slot,
        'global_updates': net.t,
        'new_target_updates': echo_count * 5,
        'metrics': grade_table(rows, split),
        'all8_echo_metrics': subset_score(rows, list(range(8))),
        'truth_table': rows,
    }


def verify_sources(root):
    """No inherited code is imported until its pinned public blob is checked."""
    publication = root / 'work/sle-p033/publication-v2'
    pin_path = publication / 'expected-git-blobs.json'
    expected = load_json(pin_path)
    archive = root / 'work/sle-p033/trial-20261112'
    source_dir = root / 'outputs/sle-p033'
    before = {relative(root, pin_path): sha(pin_path)}
    pins = {}
    source_manifest = load_json(archive / 'manifest.json')
    followup_manifest = load_json(archive / 'echo-only-followup-v2/manifest.json')
    for name in SOURCE_NAMES:
        path = source_dir / name
        data = path.read_bytes()
        wanted_blob = expected[PUBLIC_BASE + name]
        assert git_blob(data) == wanted_blob, f'PUBLIC SOURCE MISMATCH: {name}'
        wanted_sha = (followup_manifest['source_sha256'] if name == 'echo_only_followup.py'
                      else source_manifest['source_sha256'][name])
        assert sha_bytes(data) == wanted_sha, f'SOURCE SHA256 MISMATCH: {name}'
        before[relative(root, path)] = sha_bytes(data)
        pins[name] = {'git_blob': wanted_blob, 'sha256': wanted_sha}
    zip_path = publication / 'evidence.zip'
    zip_bytes = zip_path.read_bytes()
    assert git_blob(zip_bytes) == expected[PUBLIC_BASE + 'evidence.zip'], 'PUBLIC EVIDENCE ZIP MISMATCH'
    before[relative(root, zip_path)] = sha_bytes(zip_bytes)
    assert source_manifest['splits'] == SPLITS
    assert followup_manifest['splits'] == SPLITS
    assert source_manifest['numpy'] == np.__version__ == '2.3.5'
    sys.path.insert(0, str(source_dir))
    old = importlib.import_module('p032_reference')
    assert Path(old.__file__).resolve() == (source_dir / 'p032_reference.py').resolve()
    assert Path(old.ref.__file__).resolve() == (source_dir / 'p030_reference.py').resolve()
    with zipfile.ZipFile(zip_path) as evidence:
        def pinned_local(path, member=None):
            member = member or 'evidence/' + path.relative_to(archive).as_posix()
            data = path.read_bytes()
            assert data == evidence.read(member), f'PUBLIC ARTIFACT MISMATCH: {path}'
            before[relative(root, path)] = sha_bytes(data)
            return sha_bytes(data)

        for path in (archive / 'manifest.json', archive / 'echo-only-followup-v2/manifest.json'):
            pinned_local(path)
        runs = []
        for split_name in SPLIT_ORDER:
            split = SPLITS[split_name]
            for seed in SEEDS:
                name = f'{split_name}-seed{seed}'
                coverage = archive / 'coverage' / name
                e3000 = archive / 'echo-only-followup-v2' / f'{name}-echo-only'
                inputs = {}
                for label, path in (
                    ('warm', coverage / 'warm-3/final-state.npz'),
                    ('neg_final', coverage / 'neg70/final-state.npz'),
                    ('neg_result', coverage / 'result.json'),
                    ('neg_truth', coverage / 'final-truth-table.json'),
                    ('neg_summary', coverage / 'neg70/summary.json'),
                    ('neg_curve', coverage / 'neg70/curve.json'),
                    ('e3000_final', e3000 / 'final-state.npz'),
                    ('e3000_result', e3000 / 'result.json'),
                    ('e3000_summary', e3000 / 'summary.json'),
                    ('e3000_curve', e3000 / 'curve.json'),
                ):
                    inputs[label] = {'path': relative(root, path), 'sha256': pinned_local(path)}
                trace_path = coverage / 'neg70/trace.json'
                trace = load_json(trace_path)
                before[relative(root, trace_path)] = sha(trace_path)
                inputs['neg_actual_trace'] = {'path': relative(root, trace_path), 'sha256': sha(trace_path)}
                assert len(trace) == 3000 and all(len(row) == 3 for row in trace)
                if split_name.startswith('S'):
                    member = f'evidence/p032-trace-supplement/training/{name}-H72/neg70/trace.json'
                    assert trace == json.loads(evidence.read(member).decode('utf-8'))
                    inputs['neg_actual_trace']['pinned_archive_member'] = member
                schedule = old.Schedule((0, 1), split['train'], seed + OFFSETS[split_name] + 400, 7)
                inherited_stream = [list(schedule.next()) for _ in range(3000)]
                assert [row[:2] for row in trace] == inherited_stream
                assert Counter(tuple(row[:2]) for row in trace) == Counter(
                    {(op, value): 150 if op == 0 else 350 for op in (0, 1) for value in split['train']})
                # Select from the ACTUAL trace, keeping the original external slot.
                lessons = [
                    {'source_slot': slot, 'op': int(op), 'value': int(value),
                     'Q': old.ref.encode(old.ref.PHASES[3], op, value),
                     'answer_bits': old.ref.answer(op, 3, value)}
                    for slot, (op, value, _) in enumerate(trace, 1) if op == 0]
                assert len(lessons) == 900
                assert Counter(row['value'] for row in lessons) == Counter({value: 150 for value in split['train']})
                assert [[row['op'], row['value']] for row in lessons] == [row[:2] for row in trace if row[0] == 0]
                for lesson in lessons:
                    assert old.ref.parse(old.ref.PHASES[3].name, lesson['Q']) == (0, lesson['value'])
                    assert len(lesson['answer_bits']) == 4
                    assert lesson['Q'] == old.ref.encode(old.ref.PHASES[4], 0, lesson['value'])
                # A fresh restore must contain every saved array, optimizer age and RNG.
                warm = old.restore(coverage / 'warm-3/final-state.npz', seed)
                raw_state = frozen_state(coverage / 'warm-3/final-state.npz')
                assert old.ref.equal_state(raw_state, warm.state())
                assert warm.t == 8736 and (warm.L, warm.H, warm.parameters) == (16, 72, 2595)
                assert all(array.dtype == np.float32 for field in ('p', 'm', 'v') for array in getattr(warm, field))
                assert all(array.dtype == np.int64 for array in warm.birth)
                # Historical controls are EVALUATED, never retrained here.
                historical = {}
                for label, path, result_path in (
                    ('Neg70', coverage / 'neg70/final-state.npz', coverage / 'result.json'),
                    ('E3000', e3000 / 'final-state.npz', e3000 / 'result.json'),
                ):
                    control = old.restore(path, seed)
                    archived_result = load_json(result_path)
                    assert control.t == 23736
                    for group in ('train', 'val', 'test'):
                        if label == 'Neg70':
                            actual = old.ref.small(old.ref.metrics(control, old.ref.PHASES[4], split[group]))
                        else:
                            actual = old.ref.small(old.ref.metrics(control, old.ref.PHASES[3], split[group]))
                        assert actual == archived_result['metrics'][group], f'PINNED HISTORICAL RESULT MISMATCH: {name}/{label}/{group}'
                    if label == 'Neg70':
                        expected_rows = load_json(coverage / 'final-truth-table.json')
                        actual_rows = [old.truth_row(control, old.ref.PHASES[4], op, value)
                                       for op in (0, 1) for value in range(8)]
                        assert actual_rows == expected_rows
                    rows = truth_table(old, control)
                    historical[label] = {
                        'status': 'historical_pinned_control_read_only_evaluation_no_training',
                        'source_checkpoint': relative(root, path), 'source_result': relative(root, result_path),
                        'checkpoint_sha256': sha(path), 'result_sha256': sha(result_path),
                        'archived_metrics_exactly_verified': True,
                        'presentations': 3000, 'echo_presentations': 900 if label == 'Neg70' else 3000,
                        'target_updates': 15000, 'train_dense_MACs': 15000 * 5256,
                        'metrics': grade_table(rows, split), 'truth_table': rows,
                    }
                warm_rows = truth_table(old, warm)
                neg_result = load_json(coverage / 'result.json')
                assert subset_score(warm_rows, split['test'])['whole'] == neg_result['Echo_before']['by_op']['echo']['whole']
                e3000_result = load_json(e3000 / 'result.json')
                assert e3000_result['initial_checkpoint_sha256'] == sha(coverage / 'warm-3/final-state.npz')
                assert e3000_result['initial_updates'] == 8736
                runs.append({
                    'name': name, 'split': split_name, 'seed': seed, 'inputs': inputs,
                    'actual_slots': trace, 'lessons': lessons, 'historical': historical,
                    'initial_signature': state_signature(raw_state),
                    'initial_metrics': grade_table(warm_rows, split),
                    'neg_stream_matches_inherited_source': True,
                    'echo_subsequence_sha256': sha_bytes(canonical([[row['op'], row['value']] for row in lessons])),
                    'lesson_manifest_sha256': sha_bytes(canonical(lessons)),
                })
    return old, runs, before, pins


def check_unchanged(root, before):
    after = {name: sha(root / name) for name in before}
    assert after == before, 'IMMUTABLE SOURCE OR HISTORICAL ARTIFACT CHANGED'
    return after


def update_row(net, slot, echo_index, bit, text, target, prediction, loss):
    return {'source_slot': slot, 'echo_index': echo_index, 'target_position': bit,
            'binary_prefix': text, 'target': target, 'prediction': prediction, 'loss': loss,
            'global_updates': net.t, 'state': state_signature(net.state())}


def primary_run(old, net, run, folder):
    split = SPLITS[run['split']]
    curve = [measure(old, net, split, 0, 0)]
    trace, slot_trace, updates = [], [], []
    states = {0: net.state()}
    lesson_map = {row['source_slot']: row for row in run['lessons']}
    context = {}
    source_step = net.step

    def recorded_step(text, target):
        bit = context['bit']
        assert text == context['Q'] + context['answer'][:bit]
        assert target == (context['answer'] + 'S')[bit]
        pred, loss = source_step(text, target)
        updates.append(update_row(net, context['slot'], context['echo_index'], bit, text, target, pred, loss))
        context['bit'] += 1
        return pred, loss

    # The source Model.lesson executes the unchanged source Model.step via this
    # observation wrapper. The replay below uses an independent target loop.
    net.step = recorded_step
    echo_index = 0
    for slot, (op, value, _) in enumerate(run['actual_slots'], 1):
        if op != 0:
            before = net.state()
            before_counters = counters(net)
            # Intentionally no updater, zero-gradient step, evaluation or RNG call.
            assert old.ref.equal_state(before, net.state())
            assert before_counters == counters(net)
            slot_trace.append({'source_slot': slot, 'source_op': op, 'source_value': value,
                               'action': 'skip_no_update', 'echo_presentations': echo_index,
                               'global_updates': net.t, 'state_sha256': state_signature(before)['all']})
            continue
        lesson = lesson_map[slot]
        echo_index += 1
        context.update(slot=slot, echo_index=echo_index, Q=lesson['Q'], answer=lesson['answer_bits'], bit=0)
        prediction, loss = net.lesson(lesson['Q'], lesson['answer_bits'])
        assert context['bit'] == 5 and net.t == 8736 + echo_index * 5
        trace.append([op, value, prediction])
        slot_trace.append({'source_slot': slot, 'source_op': op, 'source_value': value,
                           'action': 'echo_update', 'echo_presentations': echo_index,
                           'global_updates': net.t, 'prediction': prediction, 'loss': loss,
                           'state_sha256': state_signature(net.state())['all']})
        if echo_index % 100 == 0:
            curve.append(measure(old, net, split, echo_index, slot))
            states[echo_index] = net.state()
            np.savez(folder / f'state-{echo_index:04d}.npz', **states[echo_index])
    del net.step
    assert echo_index == 900 and net.t == 13236
    assert len(updates) == 4500 and len(slot_trace) == 3000
    assert net.train_macs == 23652000
    return trace, slot_trace, updates, curve, states


def replay_run(old, initial_path, run, expected_trace, expected_slots, expected_updates, expected_curve, states, folder):
    replay = old.restore(initial_path, run['seed'])
    assert old.ref.equal_state(states[0], replay.state())
    split = SPLITS[run['split']]
    curve = [measure(old, replay, split, 0, 0)]
    trace, slot_trace = [], []
    echo_index = update_index = noops = 0
    for slot, (op, value, _) in enumerate(run['actual_slots'], 1):
        if op != 0:
            before = replay.state()
            before_counters = counters(replay)
            assert old.ref.equal_state(before, replay.state())
            assert before_counters == counters(replay)
            row = {'source_slot': slot, 'source_op': op, 'source_value': value,
                   'action': 'skip_no_update', 'echo_presentations': echo_index,
                   'global_updates': replay.t, 'state_sha256': state_signature(before)['all']}
            noops += 1
        else:
            # Reconstruct labels from the archived oracle, independently of the
            # saved lesson labels and the primary Model.lesson dispatch.
            q = old.ref.encode(old.ref.PHASES[3], 0, value)
            answer = old.ref.answer(0, 3, value)
            echo_index += 1
            prediction, loss = '', 0.
            for bit, target in enumerate(answer + 'S'):
                text = q + answer[:bit]
                pred, target_loss = replay.step(text, target)
                observed = update_row(replay, slot, echo_index, bit, text, target, pred, target_loss)
                assert observed == expected_updates[update_index], f'UPDATE REPLAY MISMATCH: {run["name"]}/{update_index}'
                update_index += 1
                prediction += pred
                loss += target_loss
            trace.append([op, value, prediction])
            row = {'source_slot': slot, 'source_op': op, 'source_value': value,
                   'action': 'echo_update', 'echo_presentations': echo_index,
                   'global_updates': replay.t, 'prediction': prediction, 'loss': loss,
                   'state_sha256': state_signature(replay.state())['all']}
            if echo_index % 100 == 0:
                curve.append(measure(old, replay, split, echo_index, slot))
                assert old.ref.equal_state(states[echo_index], replay.state())
                assert old.ref.equal_state(frozen_state(folder / f'state-{echo_index:04d}.npz'), replay.state())
        assert row == expected_slots[slot - 1], f'SLOT REPLAY MISMATCH: {run["name"]}/{slot}'
        slot_trace.append(row)
    assert trace == expected_trace and slot_trace == expected_slots
    assert curve == expected_curve
    assert update_index == 4500 and noops == 2100
    assert old.ref.equal_state(states[900], replay.state())
    assert replay.train_macs == 23652000
    return {'target_updates_replayed': update_index, 'no_op_slots_replayed': noops,
            'every_target_parameter_Adam_birth_step_RNG_group_sha256_equal': True,
            'every_noop_full_state_and_counters_equal': True,
            'complete_trace_slot_trace_curve_truth_logits_equal': True,
            'all_100_echo_checkpoints_arrays_Adam_birth_step_RNG_directly_equal': True,
            'final_arrays_Adam_birth_step_RNG_directly_equal': True,
            'signature_method': 'SHA256(dtype,shape,bytes) by p/m/v/birth and t/L/H/RNG for each target; direct full-array equality at each 100Echo checkpoint and final'}


def run_one(root, out, old, run):
    folder = out / run['name']
    initial_path = root / run['inputs']['warm']['path']
    net = old.restore(initial_path, run['seed'])
    initial = net.state()
    assert state_signature(initial) == run['initial_signature']
    np.savez(folder / 'initial-state.npz', **initial)
    start = time.perf_counter()
    trace, slots, updates, curve, states = primary_run(old, net, run, folder)
    primary_seconds = time.perf_counter() - start
    final = net.state()
    np.savez(folder / 'final-state.npz', **final)
    dump(folder / 'trace.json', trace)
    dump(folder / 'slot-trace.json', slots)
    dump(folder / 'curve.json', curve)
    dump(folder / 'initial-truth-table.json', curve[0]['truth_table'])
    dump(folder / 'final-truth-table.json', curve[-1]['truth_table'])
    with gzip.open(folder / 'update-trace.json.gz', 'wt', encoding='utf-8') as stream:
        json.dump(updates, stream, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    # Replay from the immutable warm source and re-read the persisted evidence.
    with gzip.open(folder / 'update-trace.json.gz', 'rt', encoding='utf-8') as stream:
        persisted_updates = json.load(stream)
    replay_start = time.perf_counter()
    verification = replay_run(old, initial_path, run, load_json(folder / 'trace.json'),
                             load_json(folder / 'slot-trace.json'), persisted_updates,
                             load_json(folder / 'curve.json'), states, folder)
    replay_seconds = time.perf_counter() - replay_start
    assert old.ref.equal_state(final, frozen_state(folder / 'final-state.npz'))
    initial_metrics = curve[0]['metrics']
    final_metrics = curve[-1]['metrics']
    assert initial_metrics == run['initial_metrics']
    outcome = {}
    for subset in ('val', 'test'):
        before_correct = bool(initial_metrics[subset]['whole'])
        after_correct = bool(final_metrics[subset]['whole'])
        outcome[subset] = 'retained' if before_correct and after_correct else 'lost' if before_correct else 'gained' if after_correct else 'initially_wrong_still_wrong'
    result = {
        'split': run['split'], 'seed': run['seed'],
        'new_training': True, 'presentations': 900, 'external_slots': 3000, 'skipped_neg_slots': 2100,
        'initial_updates': 8736, 'final_updates': net.t, 'target_updates': net.t - 8736,
        'echo_value_exposure': {str(value): 150 for value in SPLITS[run['split']]['train']},
        'initial_metrics': initial_metrics, 'final_metrics': final_metrics,
        'paired_outcome_from_warm': outcome,
        'warm_validation_initially_wrong': not bool(initial_metrics['val']['whole']),
        'initial_checkpoint_sha256': run['inputs']['warm']['sha256'],
        'actual_Neg70_trace_sha256': run['inputs']['neg_actual_trace']['sha256'],
        'echo_subsequence_sha256': run['echo_subsequence_sha256'],
        'source_trace_matches_inherited_schedule': True, 'actual_trace_filter_order_and_counts_verified': True,
        'initial_signature': state_signature(initial), 'final_signature': state_signature(final),
        'train_dense_MACs': net.train_macs,
        'dense_MAC_formula_per_target': '4*L*H+9*H=5256; original source dense multiply-add convention',
        'evaluation_dense_MACs': net.inference_macs, 'evaluation_inference_calls': net.inference_calls,
        'parameter_optimizer_array_bytes': sum(array.nbytes for field in ('p', 'm', 'v', 'birth') for array in getattr(net, field)),
        'array_bytes_is_not_process_peak_memory': True,
        'seconds_training_probes_and_update_signatures': primary_seconds,
        'seconds_independent_replay_and_verification': replay_seconds,
        'verification': verification,
        'historical_controls': run['historical'],
    }
    dump(folder / 'result.json', result)
    dump(folder / 'replay-checks.json', verification)
    return result


def summarize(results, out, manifest, before, after, seconds):
    comparisons = []
    for name in SPLIT_ORDER:
        selected = [row for row in results if row['split'] == name]
        comparisons.append({
            'split': name,
            'warm_test': [sum(row['initial_metrics']['test']['whole'] for row in selected), 3],
            'E900_test': [sum(row['final_metrics']['test']['whole'] for row in selected), 3],
            'historical_Neg70_test': [sum(row['historical_controls']['Neg70']['metrics']['test']['whole'] for row in selected), 3],
            'historical_E3000_test': [sum(row['historical_controls']['E3000']['metrics']['test']['whole'] for row in selected), 3],
            'warm_val': [sum(row['initial_metrics']['val']['whole'] for row in selected), 3],
            'E900_val': [sum(row['final_metrics']['val']['whole'] for row in selected), 3],
            'historical_Neg70_val': [sum(row['historical_controls']['Neg70']['metrics']['val']['whole'] for row in selected), 3],
            'historical_E3000_val': [sum(row['historical_controls']['E3000']['metrics']['val']['whole'] for row in selected), 3],
        })
    per_seed = []
    for row in results:
        per_seed.append({
            'split': row['split'], 'seed': row['seed'],
            'warm': {name: [row['initial_metrics'][name]['whole'], row['initial_metrics'][name]['total']] for name in ('train', 'val', 'test')},
            'E900': {name: [row['final_metrics'][name]['whole'], row['final_metrics'][name]['total']] for name in ('train', 'val', 'test')},
            'historical_Neg70': {name: [row['historical_controls']['Neg70']['metrics'][name]['whole'], row['historical_controls']['Neg70']['metrics'][name]['total']] for name in ('train', 'val', 'test')},
            'historical_E3000': {name: [row['historical_controls']['E3000']['metrics'][name]['whole'], row['historical_controls']['E3000']['metrics'][name]['total']] for name in ('train', 'val', 'test')},
            'outcome_from_warm': row['paired_outcome_from_warm'],
            'warm_validation_initially_wrong': row['warm_validation_initially_wrong'],
        })
    return {
        'experiment': 'P034-E900', 'status': 'passed', 'new_learners': len(results),
        'attribution': {'U': 'user mixed-teaching research direction', 'A': 'ChatGPT Pro PR8 pre-experiment E900 design', 'T': 'Codex implementation, new E900 training and independent replay'},
        'new_blind_test': False,
        'primary': {
            'warm_test_correct': sum(row['initial_metrics']['test']['whole'] for row in results),
            'E900_test_correct': sum(row['final_metrics']['test']['whole'] for row in results),
            'historical_Neg70_test_correct': sum(row['historical_controls']['Neg70']['metrics']['test']['whole'] for row in results),
            'historical_E3000_test_correct': sum(row['historical_controls']['E3000']['metrics']['test']['whole'] for row in results),
            'total_paired_tests': 12,
            'E900_test_retained': sum(row['paired_outcome_from_warm']['test'] == 'retained' for row in results),
            'E900_test_lost': sum(row['paired_outcome_from_warm']['test'] == 'lost' for row in results),
            'warm_validation_initially_wrong': sum(row['warm_validation_initially_wrong'] for row in results),
            'E900_val_retained': sum(row['paired_outcome_from_warm']['val'] == 'retained' for row in results),
            'E900_val_lost': sum(row['paired_outcome_from_warm']['val'] == 'lost' for row in results),
        },
        'comparisons_by_split': comparisons, 'per_split_seed': per_seed,
        'fixed_cost_per_learner': {
            'E900': {'echo_lessons': 900, 'neg_lessons': 0, 'target_updates': 4500, 'train_dense_MACs': 23652000},
            'historical_Neg70': {'echo_lessons': 900, 'neg_lessons': 2100, 'target_updates': 15000, 'train_dense_MACs': 78840000},
            'historical_E3000': {'echo_lessons': 3000, 'neg_lessons': 0, 'target_updates': 15000, 'train_dense_MACs': 78840000},
            'equal_Echo_exposure_only': True, 'equal_updates_or_MACs': False,
            'MAC_scope': 'Original MLP dense multiply-add convention; excludes nonlinearities, optimizer elementwise arithmetic, hashing, probes and replay. Skipped slots have zero student compute.',
        },
        'executed_target_updates': 54000, 'additional_replay_target_updates': 54000,
        'executed_no_op_slots': 25200, 'additional_replay_no_op_slots': 25200,
        'all12_trace_curve_logits_Adam_RNG_replay_equal': all(row['verification']['final_arrays_Adam_birth_step_RNG_directly_equal'] for row in results),
        'historical_controls_retrained': False,
        'historical_controls_pinned_source_results_verified': True,
        'sources_SHA256_unchanged': before == after,
        'immutable_source_and_artifact_files_checked': len(before),
        'source_manifest_sha256': sha(out / 'manifest.json'),
        'source_audit': 'source-audit.json',
        'wall_seconds_with_source_checks_and_replay': seconds,
        'limitations': [
            'Three-bit domain and these splits have been inspected previously; mechanism comparison, not a new blind test.',
            'Matched Echo exposure is not matched optimizer age, target updates or dense MACs (4500 versus 15000 updates).',
            'A difference identifies the total effect of inserted Neg updates; semantics, shared-parameter competition and optimizer age are not separately identified.',
            'Historical Neg70 and E3000 are pinned archived controls; they were evaluated read-only, not retrained.',
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out.resolve() if args.out else root / 'work/sle-p034/e900'
    if out.exists():
        raise FileExistsError(f'Do not overwrite an existing E900 experiment: {out}')
    started = time.perf_counter()
    old, runs, before, pins = verify_sources(root)
    for name in ('PRO_RESEARCH_DESIGN_20261112.md', 'PR8_AGENTS.md', 'CURRENT_RESEARCH_STATUS.md', 'spiral_language_research_index.md'):
        path = root / 'work/sle-p034/source-plan' / name
        before[relative(root, path)] = sha(path)
    before[relative(root, Path(__file__).resolve())] = sha(Path(__file__).resolve())
    check_unchanged(root, before)
    out.mkdir(parents=True)
    manifest = {
        'experiment': 'P034-E900', 'check_version': CHECK_VERSION,
        'registered_UTC_before_first_training': datetime.now(timezone.utc).isoformat(),
        'registered_before_new_training': True,
        'public_source_commit': P033_COMMIT, 'public_source_blobs': pins,
        'runner_sha256': sha(Path(__file__).resolve()), 'python': platform.python_version(), 'numpy': np.__version__,
        'splits': SPLITS, 'seeds': list(SEEDS), 'learners': 12,
        'initial_state': 'Corresponding P033 coverage warm-3: p/m/v/birth/t/L/H/growth_rng restored by unchanged old.restore; t=8736.',
        'profile': {'name': old.ref.PHASES[3].name, 'operator_bits': 2, 'data_bits': 3, 'END': False, 'L': 16, 'H': 72, 'parameters': 2595},
        'optimizer': {'implementation': 'pinned P030 Model.step', 'lr': 0.003, 'clip_global_norm': 1.0,
                      'Adam_beta1': 0.9, 'Adam_beta2': 0.999, 'epsilon': 1e-8,
                      'parameter_birth_preserved': True, 'weight_and_moment_dtype': 'float32', 'age_dtype': 'int64'},
        'curriculum': 'FILTER op0 from actual P033 Neg70 3000-row trace, keep order and values: 900Echo, each train value150. No resampling.',
        'no_op_policy': 'Each op1 external slot executes no student/update/evaluation/RNG call; p/m/v/birth/t/RNG and all counters remain exactly equal.',
        'fixed_budget': {'echo_lessons': 900, 'target_updates': 4500, 'initial_t': 8736, 'final_t': 13236,
                         'external_slots': 3000, 'skipped_slots': 2100, 'train_dense_MACs': 23652000},
        'measurement': 'At 0 and every100Echo through900, all8 values Echo-only: free-run and correct-prefix teacher logits, bits, firstwrong and STOP; no updates.',
        'replay': 'Fresh restore; independent target loop against source Model.lesson primary; per-target p/m/v/birth/t/L/H/RNG SHA256, per-slot equality, all curve/truth/logits exact, direct checkpoint full arrays every100Echo/final.',
        'stopping': 'All12 fixed900Echo; stop on provenance/invariant failure. No holdout-driven budget or architecture extension.',
        'historical_controls': 'P033 Neg70 and E3000 evaluated read-only against public pinned results; no retraining.',
        'cost_warning': 'Matched Echo exposure only: 4500 vs15000 target updates;23652000 vs78840000 denseMACs. No equal-MAC claim.',
        'inputs_sha256_before_training': before,
        'courses': [{key: run[key] for key in ('name', 'split', 'seed', 'inputs', 'initial_signature', 'echo_subsequence_sha256', 'lesson_manifest_sha256')} for run in runs],
    }
    # All courses and the source/implementation manifest exist BEFORE any lesson.
    for run in runs:
        folder = out / run['name']
        folder.mkdir()
        dump(folder / 'lessons.json', run['lessons'])
        assert sha_bytes(canonical(load_json(folder / 'lessons.json'))) == run['lesson_manifest_sha256']
        dump(folder / 'historical-controls.json', run['historical'])
    with (out / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, ensure_ascii=False, sort_keys=True, indent=2)
    dump(out / 'source-checks-before-training.json', {'status': 'passed', 'source_SHA256': before,
                                                   'public_sources_and_zip_pinned': True,
                                                   'all12_actual_trace_subsequences_and_complete_warm_states_checked': True,
                                                   'historical_pinned_results_exactly_verified_without_training': True})
    results = []
    for run in runs:
        check_unchanged(root, before)
        results.append(run_one(root, out, old, run))
    after = check_unchanged(root, before)
    dump(out / 'source-audit.json', {'status': 'passed', 'before': before, 'after': after, 'all_equal': True})
    dump(out / 'results.json', results)
    compact = summarize(results, out, manifest, before, after, time.perf_counter() - started)
    dump(out / 'compact.json', compact)
    print(json.dumps({'status': compact['status'], 'experiment': 'P034-E900', 'learners': 12,
                      'primary': compact['primary'], 'source_SHA_unchanged': True,
                      'all12_replay_equal': True, 'compact_json': str(out / 'compact.json')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
