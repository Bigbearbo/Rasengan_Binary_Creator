"""P033 H3 follow-up: matched warm-state Echo-only continuation, fixed budget.

Separate from the first 30 trials; added after their results, as the upstream H3
control. This is not a new blind test or a hyperparameter search.
"""
import argparse
import json
import time
from pathlib import Path
import p032_reference as old


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run', type=Path)
    args = p.parse_args()
    destination = args.run / 'echo-only-followup-v2'
    if destination.exists():
        raise FileExistsError('Do not overwrite an existing follow-up')
    destination.mkdir()
    splits = json.loads((args.run / 'manifest.json').read_text('utf-8'))['splits']
    offsets = {'S0': 0, 'C0': 0, 'S1': 10000, 'C1': 10000}
    manifest = {'id': 'P033-H3-EchoOnly', 'source_plan': '9118abf H3',
                'registered_before_followup_training': True,
                'selection': 'separate upstream H3 control added after D+A+3A results; not blind',
                'seeds': [101, 202, 303], 'splits': splits, 'budget': 3000,
                'L': 16, 'H': 72, 'teacher_target_updates': 15000,
                'initial_state': 'corresponding completed coverage warm-3 checkpoint, including Adam/RNG',
                'schedule': 'same phase4 seed+offset+400; onlyEcho, per-op value stream matches Neg70 Echo stream',
                'exposure_limit': '3000Echo versus Neg70 900Echo+2100Neg: equal total budget, unequal operator information',
                'source_sha256': old.sha(Path(__file__))}
    old.dump(destination / 'manifest.json', manifest)
    rows = []
    start = time.perf_counter()
    for split_name, split in splits.items():
        for seed in manifest['seeds']:
            root = args.run / 'coverage' / f'{split_name}-seed{seed}'
            warm = root / 'warm-3/final-state.npz'
            before_hash = old.sha(warm)
            net = old.restore(warm, seed)
            initial_updates = net.t
            result = old.fit_verified(net, old.ref.PHASES[3], split['train'], split['val'],
                                      seed + offsets[split_name] + 400, 3000,
                                      destination / f'{split_name}-seed{seed}-echo-only')
            assert net.t == initial_updates + 15000
            assert old.sha(warm) == before_hash
            assert net.train_macs == 78840000
            scores = {name: old.ref.small(old.ref.metrics(net, old.ref.PHASES[3], split[name]))
                      for name in ('train', 'val', 'test')}
            row = {'split': split_name, 'seed': seed, 'initial_checkpoint_sha256': before_hash,
                   'initial_updates': initial_updates, 'summary': result, 'metrics': scores}
            old.dump(destination / f'{split_name}-seed{seed}-echo-only' / 'result.json', row)
            rows.append(row)
    assert manifest['source_sha256'] == old.sha(Path(__file__))
    comparison = []
    coverage = json.loads((args.run / 'coverage/results.json').read_text('utf-8'))
    for split_name in splits:
        selected = [r for r in rows if r['split'] == split_name]
        control = [r for r in coverage if r['split'] == split_name]
        comparison.append({'split': split_name,
                           'Echo_only_val': [sum(r['metrics']['val']['by_op']['echo']['whole'] for r in selected), 3],
                           'Echo_only_test': [sum(r['metrics']['test']['by_op']['echo']['whole'] for r in selected), 3],
                           'Echo_after_Neg70_val': [sum(r['metrics']['val']['by_op']['echo']['whole'] for r in control), 3],
                           'Echo_after_Neg70_test': [sum(r['Echo_after']['by_op']['echo']['whole'] for r in control), 3]})
    compact = {'status': 'passed', 'learners': len(rows), 'comparisons': comparison,
               'extra_presentations': 36000, 'extra_target_updates': 180000,
               'extra_updates_with_replay': 360000, 'all_trace_curve_optimizer_RNG_replayed': True,
               'wall_seconds_with_replay': time.perf_counter() - start}
    old.dump(destination / 'results.json', rows)
    old.dump(destination / 'compact.json', compact)
    print(json.dumps(compact), flush=True)


if __name__ == '__main__':
    main()
