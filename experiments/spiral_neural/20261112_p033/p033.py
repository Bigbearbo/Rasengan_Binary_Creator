"""P033 coverage and from-scratch interleaving trials, with full update replay."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import copy
import hashlib
import itertools
import json
import platform
import time
from collections import Counter
from pathlib import Path

import numpy as np
import p032_reference as old
import diagnostic

ref = old.ref
SPLITS = dict(old.SPLITS) | {'C0': {'train': [0, 1, 2, 3, 4, 7], 'val': [5], 'test': [6]},
                           'C1': {'train': [0, 1, 2, 3, 5, 6], 'val': [4], 'test': [7]}}
OFFSETS = {'S0': 0, 'C0': 0, 'S1': 10000, 'C1': 10000}
TIMINGS = ['T0', 'T1', 'T0B']
SEEDS = [101, 202, 303]


def multiset_lessons(values, seed, mode):
    streams = {}
    for op in (0, 1):
        rng = np.random.default_rng(seed + 60000 + 1000 * op)
        streams[op] = [int(v) for _ in range(250) for v in rng.permutation(values)]
    rng = np.random.default_rng(seed + 70000)
    if mode == 'T0':
        ops = [0] * 1500 + [1] * 1500
    elif mode == 'T1':
        ops = rng.permutation([0, 1]).tolist() + rng.permutation([0] * 4 + [1] * 4).tolist()
        ops += [int(op) for _ in range(299) for op in rng.permutation([0] * 5 + [1] * 5)]
    elif mode == 'T0B':
        ops = [0] * 1000 + [int(op) for _ in range(500) for op in rng.permutation([0, 1, 1, 1])]
    else:
        raise ValueError('Unknown timing curriculum')
    indices = {0: 0, 1: 0}
    result = []
    for op in ops:
        result.append((int(op), streams[op][indices[op]]))
        indices[op] += 1
    assert indices == {0: 1500, 1: 1500}
    assert Counter(result) == Counter({(op, v): 250 for op in (0, 1) for v in values})
    return result


def checks():
    coverage = {}
    for name, split in SPLITS.items():
        sets = [set(split[k]) for k in ('train', 'val', 'test')]
        assert len(set.union(*sets)) == 8 and sum(map(len, sets)) == 8
        words = [format(v, '03b') for v in split['train']]
        missing = {f'{i},{j}': sorted({'00', '01', '10', '11'} - {w[i] + w[j] for w in words})
                   for i, j in itertools.combinations(range(3), 2)}
        assert (all(not v for v in missing.values())) == name.startswith('C')
        coverage[name] = missing
        for seed in SEEDS:
            courses = [multiset_lessons(split['train'], seed, mode) for mode in TIMINGS]
            assert all(Counter(c) == Counter(courses[0]) for c in courses)
            for op in (0, 1):
                assert all([v for o, v in c if o == op] == [v for o, v in courses[0] if o == op] for c in courses)
            assert {o for o, _ in courses[1][:2]} == {0, 1}
            for course in courses:
                for op, value in set(course):
                    q = ref.encode(ref.PHASES[4], op, value)
                    assert ref.parse(ref.PHASES[4].name, q) == (op, value)
                    assert not set(q) - set('01')
    return {'coverage': coverage, 'exact_same_multiset_and_per_op_value_streams': True,
            'fresh_interleaving_begins_in_first_two_lessons': True,
            'pure_binary_and_roundtrip': True}


def grade(net, split):
    return {name: ref.small(ref.metrics(net, ref.PHASES[4], split[name])) for name in ('train', 'val', 'test')}


def coverage_trial(out, archive):
    out.mkdir()
    results = []
    for split_name in ('S0', 'C0', 'S1', 'C1'):
        split = SPLITS[split_name]
        for seed in SEEDS:
            root = out / f'{split_name}-seed{seed}'
            root.mkdir()
            net = old.make_model(seed, 72)
            warm = []
            for phase, budget in enumerate(old.WARM_BUDGETS):
                p = ref.PHASES[phase]
                values = list(range(2 ** p.nd)) if p.nd < 3 else split['train']
                val = values if p.nd < 3 else split['val']
                warm.append(old.fit_verified(net, p, values, val, seed + OFFSETS[split_name] + 100 * phase,
                                              budget, root / f'warm-{phase}'))
            before = copy.deepcopy(net)
            stage = old.fit_verified(net, ref.PHASES[4], split['train'], split['val'],
                                     seed + OFFSETS[split_name] + 400, 3000, root / 'neg70', 7)
            baseline_equal = None
            if split_name.startswith('S'):
                source_root = archive / 'training' / f'{split_name}-seed{seed}-H72'
                expected = old.restore(source_root / 'neg70/final-state.npz', seed)
                assert ref.equal_state(expected.state(), net.state())
                for phase in range(4):
                    assert json.loads((root / f'warm-{phase}/trace.json').read_text()) == json.loads((source_root / f'warm-{phase}/trace.json').read_text())
                assert json.loads((root / 'neg70/trace.json').read_text()) == json.loads((source_root / 'neg70/trace.json').read_text())
                baseline_equal = True
            result = {'split': split_name, 'seed': seed, 'warm': warm, 'Neg': stage,
                      'metrics': grade(net, split), 'Echo_before': ref.small(ref.metrics(before, ref.PHASES[3], split['test'])),
                      'Echo_after': ref.small(ref.metrics(net, ref.PHASES[4], split['test'], (0,))),
                      'baseline_P032_actual_rerun_trace_optimizer_equal': baseline_equal,
                      'train_MACs': net.train_macs, 'inference_MACs': net.inference_macs,
                      'parameter_optimizer_array_bytes': sum(a.nbytes for name in ('p', 'm', 'v', 'birth') for a in getattr(net, name))}
            rows = [old.truth_row(net, ref.PHASES[4], op, v) for op in (0, 1) for v in range(8)]
            old.dump(root / 'final-truth-table.json', rows)
            old.dump(root / 'result.json', result)
            results.append(result)
            print(json.dumps({'family': 'coverage', 'split': split_name, 'seed': seed,
                              'test': result['metrics']['test']['by_op']}), flush=True)
    old.dump(out / 'results.json', results)
    return results


def timing_learning(net, lessons):
    p = ref.PHASES[4]
    curve, trace, states, tables = [], [], {}, {}
    def measure(at):
        curve.append({'presentations': at, 'metrics_all_values': ref.small(ref.metrics(net, p, list(range(8))))})
    measure(0)
    for n, (op, value) in enumerate(lessons, 1):
        q, a = ref.encode(p, op, value), ref.answer(op, 3, value)
        prediction, _ = net.lesson(q, a)
        trace.append([op, value, prediction])
        if n % 100 == 0:
            measure(n)
        if n in (1000, 1500, 3000):
            states[n] = net.state()
            tables[n] = [old.truth_row(net, p, op, v) for op in (0, 1) for v in range(8)]
    return trace, curve, states, tables


def timing_trial(out):
    out.mkdir()
    results = []
    for group, split_name in [('G0', 'S0'), ('G1', 'C1')]:
        split = SPLITS[split_name]
        for seed in SEEDS:
            initial = old.make_model(seed, 72)
            first_initial_state = initial.state()
            for mode in TIMINGS:
                folder = out / f'{group}-seed{seed}-{mode}'
                folder.mkdir()
                net = copy.deepcopy(initial)
                assert ref.equal_state(net.state(), first_initial_state)
                lessons = multiset_lessons(split['train'], seed, mode)
                start = time.perf_counter()
                trace, curve, states, tables = timing_learning(net, lessons)
                elapsed = time.perf_counter() - start
                frozen = net.state()
                replay = copy.deepcopy(initial)
                rr, cc, ss, tt = timing_learning(replay, lessons)
                assert trace == rr and curve == cc and tables == tt
                assert ref.equal_state(frozen, replay.state())
                for n in states:
                    assert ref.equal_state(states[n], ss[n])
                    np.savez(folder / f'state-{n}.npz', **states[n])
                    old.dump(folder / f'truth-table-{n}.json', tables[n])
                assert net.t == 15000 and net.train_macs == 15000 * 73 * 72
                old.dump(folder / 'trace.json', trace)
                old.dump(folder / 'curve.json', curve)
                old.dump(folder / 'lesson-multiset.json', {f'{o}:{v}': n for (o, v), n in sorted(Counter(lessons).items())})
                result = {'group': group, 'split': split_name, 'seed': seed, 'timing': mode,
                          'parameters': net.parameters, 'presentations': 3000, 'target_updates': net.t,
                          'raw_question_bits': sum(len(ref.encode(ref.PHASES[4], op, v)) for op, v in lessons),
                          'teacher_answer_bits': 12000, 'train_MACs': net.train_macs,
                          'inference_MACs': net.inference_macs, 'seconds_training_and_probes': elapsed,
                          'metrics': grade(net, split), 'replay_trace_curve_tables_optimizer_RNG_equal': True,
                          'parameter_optimizer_array_bytes': sum(a.nbytes for name in ('p', 'm', 'v', 'birth') for a in getattr(net, name))}
                old.dump(folder / 'result.json', result)
                results.append(result)
                print(json.dumps({'family': 'timing', 'group': group, 'seed': seed, 'timing': mode,
                                  'test': result['metrics']['test']['by_op']}), flush=True)
    old.dump(out / 'results.json', results)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--p032-run', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Choose a fresh experiment directory')
    args.out.mkdir(parents=True)
    source_hashes = {p.name: old.sha(p) for p in Path(__file__).parent.iterdir() if p.suffix in ('.py', '.md')}
    manifest = {'experiment': 'P033-D+A+3A', 'upstream': '9118abf4e895204588f7c5aa1bfc2615d0ab52b8',
                'seed': SEEDS, 'splits': SPLITS, 'coverage_schedule_offsets': OFFSETS,
                'coverage_LH': [16, 72], 'coverage_new_percent': 70, 'warm_budgets': old.WARM_BUDGETS,
                'coverage_Neg_budget': 3000, 'timing_groups': {'G0': 'S0', 'G1': 'C1'}, 'timings': TIMINGS,
                'timing_budget': 3000, 'timing_exposure_per_op_value': 250,
                'timing_value_rng': 'seed+60000+1000*op', 'timing_op_rng': 'seed+70000',
                'source_sha256': source_hashes, 'python': platform.python_version(), 'numpy': np.__version__,
                'not_run': ['V1/V2 pairing exposures', 'B learned architecture', 'extra widths', 'new math operators']}
    old.dump(args.out / 'manifest.json', manifest)
    started = time.perf_counter()
    old.dump(args.out / 'checks.json', checks())
    diag = diagnostic.run(args.p032_run, args.out / 'diagnostic')
    a = coverage_trial(args.out / 'coverage', args.p032_run)
    t = timing_trial(args.out / 'timing')
    assert all(old.sha(Path(__file__).parent / name) == digest for name, digest in source_hashes.items())
    compact = {'status': 'passed', 'meaning': 'execution and replay accepted; see learning scores separately',
               'diagnostic_checkpoints': len(diag['checkpoints_unchanged']), 'counterfactual_rows': diag['counterfactual_rows'],
               'coverage_learners': len(a), 'timing_primary_learners': 12, 'timing_T0B_supplementary': 6,
               'training_presentations': 12 * 4824 + 18 * 3000, 'target_updates': 12 * 23736 + 18 * 15000,
               'all_updates_fully_replayed': True, 'original_P032_controls_reproduced': 6,
               'wall_seconds_with_diagnostic_and_replay': time.perf_counter() - started}
    old.dump(args.out / 'compact.json', compact)
    print(json.dumps(compact), flush=True)


if __name__ == '__main__':
    main()
