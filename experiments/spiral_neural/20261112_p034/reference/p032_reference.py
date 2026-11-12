"""P032-D read-only truth tables and preregistered P032-A 2x2 trial.

Learning math and binary codec are the unchanged published P030 implementation.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import copy
import hashlib
import json
import math
import platform
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
import p030_reference as ref

SEEDS = [101, 202, 303]
SPLITS = {'S0': {'train': [0, 1, 2, 3, 5, 7], 'val': [4], 'test': [6]},
          'S1': {'train': [0, 1, 2, 3, 4, 6], 'val': [5], 'test': [7]}}
WARM_BUDGETS = [96, 192, 768, 768]
NEG_BUDGET = 3000
SNAPSHOTS = {923, 1687, 3000}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore(path, seed=1):
    with np.load(path, allow_pickle=False) as state:
        net = ref.Model(seed, int(state['L']), int(state['H']))
        for name in ('p', 'm', 'v', 'birth'):
            setattr(net, name, [state[f'{name}{i}'].copy() for i in range(4)])
        net.t = int(state['t'])
        net.growth_rng.bit_generator.state = json.loads(str(state['growth_rng']))
    return net


def make_model(seed, hidden):
    big = ref.Model(seed)
    old = big.state()
    big.grow(16, 128, 'p032_fixed_common_initialization')
    small = copy.deepcopy(big)
    small.H = hidden
    for name in ('p', 'm', 'v', 'birth'):
        a = getattr(big, name)
        setattr(small, name, [a[0][:, :hidden].copy(), a[1][:hidden].copy(),
                              a[2][:hidden].copy(), a[3].copy()])
    for name in ('p', 'm', 'v', 'birth'):
        a = getattr(small, name)
        for i, sl in enumerate([(slice(0, 16), slice(0, 64)), (slice(0, 64),),
                                (slice(0, 64), slice(None)), (slice(None),)]):
            assert np.array_equal(a[i][sl], old[f'{name}{i}'])
    small.events = [{'from': [8, 64, 1283], 'to': [16, hidden, small.parameters],
                     'old_blocks_moments_birth_equal': True, 'new_hidden_output_zero': True}]
    small.train_macs = small.inference_macs = small.inference_calls = 0
    return small


class Schedule:
    def __init__(self, ops, values, seed, new_count=None):
        self.ops, self.values, self.new_count = ops, values, new_count
        self.rng = np.random.default_rng(seed)
        self.value_rng = {op: np.random.default_rng(seed + 1000 + op) for op in ops}
        self.queue = {op: [] for op in ops}
        self.block = []

    def next(self):
        if not self.block:
            choices = list(self.ops) if self.new_count is None else [1] * self.new_count + [0] * (10 - self.new_count)
            self.block = self.rng.permutation(choices).tolist()
        op = int(self.block.pop(0))
        if not self.queue[op]:
            self.queue[op] = self.value_rng[op].permutation(self.values).tolist()
        return op, int(self.queue[op].pop(0))


def points(budget):
    return ({0, 25, 50, 100, 192, 384, 768, budget} | set(range(100, budget + 1, 100))
            | (SNAPSHOTS if budget == NEG_BUDGET else set())) & set(range(budget + 1))


def learning(net, p, values, val, seed, count, ratio=None):
    schedule = Schedule(p.ops, values, seed, ratio)
    curve, trace, saved = [], [], {}
    start_t, start_mac = net.t, net.train_macs
    counter = Counter()
    measurement_points = points(count)
    def measure(at):
        train = ref.metrics(net, p, values)
        validation = ref.metrics(net, p, val)
        curve.append({'presentations': at, 'updates': net.t, 'train': ref.small(train),
                      'validation': ref.small(validation), 'passed': ref.passed(train, validation)})
    measure(0)
    first_gradient = last_gradient = None
    for n in range(1, count + 1):
        op, value = schedule.next()
        q, answer = ref.encode(p, op, value), ref.answer(op, p.nd, value)
        if n == 1 or n == count:
            _, gradients, _ = net.loss_grad(q, answer[0])
            gradient_norm = math.sqrt(sum(float(np.square(g).sum()) for g in gradients))
            if n == 1:
                first_gradient = gradient_norm
            else:
                last_gradient = gradient_norm
        pred, _ = net.lesson(q, answer)
        trace.append([op, value, pred])
        counter[(op, value)] += 1
        if n in measurement_points:
            measure(n)
        if ratio is not None and n in SNAPSHOTS:
            saved[n] = net.state()
    stable = 0
    confirmed = None
    for row in curve:
        if row['presentations']:
            stable = stable + 1 if row['passed'] else 0
            if stable >= 3 and confirmed is None:
                confirmed = row['presentations']
    summary = {'presentations': count, 'target_updates': net.t - start_t,
               'train_dense_MACs': net.train_macs - start_mac,
               'raw_question_bits': sum(len(ref.encode(p, op, value)) for op, value, _ in trace),
               'teacher_answer_bits': sum(len(ref.answer(op, p.nd, value)) for op, value, _ in trace),
               'exposure': {f'{op}:{v}': n for (op, v), n in sorted(counter.items())},
               'unique': len(counter), 'first_train_val_pass': next((r['presentations'] for r in curve if r['presentations'] and r['passed']), None),
               'first_three_consecutive_passes': confirmed,
               'first_token_gradient_norm_at_first_last_lesson': [first_gradient, last_gradient]}
    return summary, trace, curve, saved


def fit_verified(net, p, values, val, seed, count, folder, ratio=None):
    folder.mkdir()
    before = copy.deepcopy(net)
    started = time.perf_counter()
    summary, trace, curve, snapshots = learning(net, p, values, val, seed, count, ratio)
    summary['seconds_training_and_probes'] = time.perf_counter() - started
    final = net.state()
    replay_start = time.perf_counter()
    rr, tt, cc, ss = learning(before, p, values, val, seed, count, ratio)
    assert trace == tt and curve == cc
    assert {k: v for k, v in summary.items() if not k.startswith('seconds_')} == rr
    assert ref.equal_state(final, before.state())
    assert snapshots.keys() == ss.keys()
    for n in snapshots:
        assert ref.equal_state(snapshots[n], ss[n])
        np.savez(folder / f'state-{n}.npz', **snapshots[n])
    summary['seconds_replay'] = time.perf_counter() - replay_start
    summary['full_trace_curve_optimizer_rng_replay_equal'] = True
    summary['profile'] = asdict(p)
    np.savez(folder / 'final-state.npz', **final)
    dump(folder / 'trace.json', trace)
    dump(folder / 'curve.json', curve)
    dump(folder / 'summary.json', summary)
    return summary


def edit_distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def truth_row(net, p, op, value):
    q, a = ref.encode(p, op, value), ref.answer(op, p.nd, value)
    frozen = net.state()
    generated, overflow = net.generate(q)
    tf = []
    for i, target in enumerate(a + 'S'):
        z = net.forward(q + a[:i])[2].astype(np.float64)
        prob = np.exp(z - np.logaddexp.reduce(z))
        tf.append({'position': i, 'target': target, 'prediction': '01S'[int(z.argmax())],
                   'logits': z.tolist(), 'probabilities_01S': prob.tolist(),
                   'correct_probability': float(prob['01S'.index(target)])})
    free = []
    prefix = ''
    for token in generated:
        z = net.forward(q + prefix)[2].astype(np.float64)
        prob = np.exp(z - np.logaddexp.reduce(z))
        free.append({'prediction': token, 'logits': z.tolist(),
                     'selected_probability': float(prob['01S'.index(token)])})
        if token == 'S':
            break
        prefix += token
    assert ref.equal_state(frozen, net.state())
    return {'profile': p.name, 'n_op': p.nop, 'n_data': p.nd, 'END_active': p.end,
            'operator': ref.NAMES[op], 'value': value, 'Q': q, 'target': a + 'S',
            'operator_positions_zero_based': list(range(2, 3 + p.nop)),
            'data_positions_zero_based': list(range(3 + p.nop, 4 + p.nop + p.nd)),
            'generated': generated, 'overflow': overflow, 'whole_correct': generated == a + 'S' and not overflow,
            'STOP_position_correct': generated.endswith('S') and len(generated) == len(a) + 1,
            'bit_correct': [i < len(generated) and generated[i] == bit for i, bit in enumerate(a)],
            'edit_distance': edit_distance(generated, a + 'S'), 'teacher_forcing': tf, 'free_run': free}


def drift(before, net):
    layers = []
    for i, (old, new) in enumerate(zip(before.p, net.p)):
        delta = float(np.linalg.norm(new.astype(float) - old.astype(float)))
        layers.append({'array': ['W', 'b', 'V', 'a'][i], 'L2': delta,
                       'relative_L2': delta / max(float(np.linalg.norm(old)), 1e-12)})
    p = ref.PHASES[4]
    contribution = []
    for op in p.ops:
        for v in range(8):
            h = net.forward(ref.encode(p, op, v))[1][0]
            contribution.append(float(np.linalg.norm(h[64:] @ net.p[2][64:])))
    return {'layers': layers, 'hidden_above_original64_mean_logit_contribution_at_answer_start': float(np.mean(contribution)),
            'interpretation': 'movement and contribution are not proof of useful reorganization'}


def diagnostic(archive, out):
    out.mkdir()
    rows, sources = [], {}
    for path in sorted(archive.glob('*/**/state.npz')):
        p = ref.REGISTRY.get(path.parent.name)
        if p is None or p.nd != 3:
            continue
        before_hash = sha(path)
        net = restore(path)
        source = path.relative_to(archive).as_posix()
        for op in p.ops:
            for value in range(8):
                split = 'train' if value in [0, 1, 2, 3, 4, 7] else 'validation' if value == 5 else 'test'
                rows.append(truth_row(net, p, op, value) | {'checkpoint': source, 'P030_split': split})
        assert before_hash == sha(path)
        sources[source] = before_hash
    if not sources:
        raise RuntimeError('No saved P030 n3 stage checkpoints loaded')
    dump(out / 'truth-tables.json', rows)
    summary = {'checkpoints': len(sources), 'rows': len(rows), 'source_sha256_unchanged': sources,
               'n3_only': True, 'inactive_operators': 'not evaluated; no fictitious Zero in Echo/Neg-only profiles',
               'new_blind_test': False,
               'by_value': {str(v): {'correct': sum(r['whole_correct'] for r in rows if r['value'] == v),
                                    'total': sum(r['value'] == v for r in rows)} for v in range(8)}}
    dump(out / 'compact.json', summary)
    return summary


def checks():
    initialization = []
    for seed in SEEDS:
        a, b = make_model(seed, 72), make_model(seed, 128)
        max_error = 0.
        for q in ('010000', '010010', '0100010', '01000000', '010001010'):
            max_error = max(max_error, float(np.max(abs(a.forward(q)[2] - b.forward(q)[2]))))
        assert max_error < 2e-6
        assert np.array_equal(a.p[0], b.p[0][:, :72])
        assert np.all(a.p[2][64:] == 0) and np.all(b.p[2][64:] == 0)
        assert a.parameters == 2595 and b.parameters == 4611
        initialization.append({'seed': seed, 'maximum_logit_error': max_error, 'shared_initial_blocks_equal': True})
    for split in SPLITS.values():
        groups = [set(split[k]) for k in ('train', 'val', 'test')]
        assert set.union(*groups) == set(range(8)) and sum(map(len, groups)) == 8
        assert min(split['val'] + split['test']) >= 4
    for ratio in (5, 7):
        s = Schedule((0, 1), SPLITS['S0']['train'], 7, ratio)
        t = [s.next() for _ in range(3000)]
        assert sum(op for op, _ in t) == 300 * ratio
        assert all(sum(op for op, _ in t[i:i + 10]) == ratio for i in range(0, 3000, 10))
        assert len(set(t)) == 12
    return {'initialization': initialization, 'split_predeclared_disjoint': True,
            'per10_exact_new_old_and_train_coverage': True, 'shared_P030_learning_code': True}


def train(out):
    out.mkdir()
    results = []
    for split_index, (split_name, split) in enumerate(SPLITS.items()):
        for seed in SEEDS:
            for hidden in (72, 128):
                root = out / f'{split_name}-seed{seed}-H{hidden}'
                root.mkdir()
                net = make_model(seed, hidden)
                warm_summaries = []
                for i, (p, budget) in enumerate(zip(ref.PHASES[:4], WARM_BUDGETS)):
                    values = list(range(2 ** p.nd)) if p.nd < 3 else split['train']
                    val = values if p.nd < 3 else split['val']
                    s = fit_verified(net, p, values, val, seed + 10000 * split_index + 100 * i,
                                     budget, root / f'warm-{i}')
                    warm_summaries.append(s)
                warm = copy.deepcopy(net)
                pre_rows = [truth_row(warm, ref.PHASES[4], 0, v) for v in range(8)]
                for ratio in (7, 5):
                    net = copy.deepcopy(warm)
                    assert ref.equal_state(warm.state(), net.state())
                    folder = root / f'neg{ratio}0'
                    s = fit_verified(net, ref.PHASES[4], split['train'], split['val'],
                                     seed + 10000 * split_index + 400, NEG_BUDGET, folder, ratio)
                    final_rows = [truth_row(net, ref.PHASES[4], op, v) for op in (0, 1) for v in range(8)]
                    cost_snapshots = {}
                    for n in sorted(SNAPSHOTS):
                        snapped = restore(folder / f'state-{n}.npz', seed)
                        cost_snapshots[str(n)] = {'metrics': ref.small(ref.metrics(snapped, ref.PHASES[4], split['test'])),
                                                  'total_train_dense_MACs': int(snapped.t) * 73 * hidden,
                                                  'Neg_dense_MACs': n * 5 * 73 * hidden}
                    arrays_bytes = sum(a.nbytes for name in ('p', 'm', 'v', 'birth') for a in getattr(net, name))
                    row = {'split': split_name, 'seed': seed, 'H': hidden, 'new_percent': ratio * 10,
                           'parameters': net.parameters, 'warm': warm_summaries, 'Neg': s,
                           'final_test': ref.small(ref.metrics(net, ref.PHASES[4], split['test'])),
                           'final_all': ref.small(ref.metrics(net, ref.PHASES[4], list(range(8)))),
                           'preNeg_test_echo': ref.small(ref.metrics(warm, ref.PHASES[3], split['test'])),
                           'postNeg_test_echo': ref.small(ref.metrics(net, ref.PHASES[4], split['test'], (0,))),
                           'cost_snapshots': cost_snapshots, 'weight_drift': drift(warm, net),
                           'total_train_dense_MACs': net.train_macs, 'inference_dense_MACs': net.inference_macs,
                           'inference_calls': net.inference_calls, 'parameter_optimizer_array_bytes': arrays_bytes}
                    dump(folder / 'paired-echo-before.json', pre_rows)
                    dump(folder / 'final-truth-table.json', final_rows)
                    dump(folder / 'result.json', row)
                    results.append(row)
                    print(json.dumps({'split': split_name, 'seed': seed, 'H': hidden, 'ratio': ratio,
                                      'test': row['final_test']['by_op'], 'replay': True}), flush=True)
            for ratio in (7, 5):
                a = json.loads((out / f'{split_name}-seed{seed}-H72' / f'neg{ratio}0' / 'trace.json').read_text())
                b = json.loads((out / f'{split_name}-seed{seed}-H128' / f'neg{ratio}0' / 'trace.json').read_text())
                assert [r[:2] for r in a] == [r[:2] for r in b]
    dump(out / 'results.json', results)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--p030-archive', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Choose a fresh P032 run folder')
    args.out.mkdir(parents=True)
    source_hashes = {p.name: sha(p) for p in Path(__file__).parent.glob('*') if p.suffix in ('.py', '.md')}
    manifest = {'experiment': 'P032-D+A', 'upstream_plan_commit': 'a1881a3ada19105661df51015454751ab313bf10',
                'seeds': SEEDS, 'splits': SPLITS, 'L': 16, 'H': [72, 128], 'new_percent': [70, 50],
                'warm_budgets': WARM_BUDGETS, 'Neg_budget': NEG_BUDGET, 'snapshot_points': sorted(SNAPSHOTS),
                'scheduler_seed': 'seed+10000*split_index+100*phase_index; Neg phase_index=4',
                'max_target_updates_per_logical_learner': 23736, 'python': platform.python_version(),
                'numpy': np.__version__, 'source_sha256': source_hashes, 'B_growth': 'not run; conditional future study'}
    dump(args.out / 'manifest.json', manifest)
    started = time.perf_counter()
    check_result = checks()
    dump(args.out / 'checks.json', check_result)
    diag = diagnostic(args.p030_archive, args.out / 'diagnostic')
    results = train(args.out / 'training')
    assert all(sha(Path(__file__).parent / name) == value for name, value in source_hashes.items())
    compact = {'status': 'passed', 'meaning': 'execution and replay verification passed, not universal learning success',
               'diagnostic_checkpoints': diag['checkpoints'], 'diagnostic_rows': diag['rows'],
               'Neg_branches': len(results), 'shared_warm_prefixes': 12,
               'actual_presentations_without_replay': 12 * sum(WARM_BUDGETS) + 24 * NEG_BUDGET,
               'all_actual_updates_replayed': True,
               'rows': [{k: r[k] for k in ('split', 'seed', 'H', 'new_percent', 'parameters', 'final_test',
                                          'preNeg_test_echo', 'postNeg_test_echo', 'total_train_dense_MACs')} for r in results],
               'wall_seconds_with_full_replay': time.perf_counter() - started}
    dump(args.out / 'compact.json', compact)
    print(json.dumps({k: v for k, v in compact.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
