"""Read-only real NN inference through shared-bank input, then offline grading.

This reuses already exposed P030 cases. It is integration evidence, not a new
blind test, training run, or VM solver. The original model source is explicit.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

from student_io import StudentBank, canonical_json, normalize_nn
from teacher import OfflineGrader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--model-source', type=Path, required=True)
    parser.add_argument('--checkpoints', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Choose a fresh evidence directory')
    args.out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('p030_shared_bank_probe', args.model_source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    bank = StudentBank(args.bank)
    results = []
    started = time.perf_counter()
    for seed in (101, 202, 303):
        checkpoint = args.checkpoints / f'dynamic-{seed}' / 'final-state.npz'
        before_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        with np.load(checkpoint, allow_pickle=False) as archive:
            net = module.Model(seed, int(archive['L']), int(archive['H']))
            for name in ('p', 'm', 'v', 'birth'):
                setattr(net, name, [archive[f'{name}{i}'].copy() for i in range(4)])
            net.t = int(archive['t'])
            net.growth_rng.bit_generator.state = json.loads(str(archive['growth_rng']))
        frozen = net.state()
        calls = []
        def predict(raw):
            # Only raw input is available here. No labels, parse tree or oracle.
            tokens, overflow = net.generate(raw)
            calls.append({'q': raw, 'generated': tokens, 'overflow': overflow})
            return tokens
        outputs = []
        for split in ('train', 'val', 'test'):
            outputs.extend(bank.dispatch('s4_neg', split, predict))
        assert module.equal_state(frozen, net.state())
        # Re-run after inference, without loading any labels or changing the net.
        for row in calls[:]:
            tokens, overflow = net.generate(row['q'])
            assert (tokens, overflow) == (row['generated'], row['overflow'])
        assert module.equal_state(frozen, net.state())
        grader = OfflineGrader(args.bank)
        counts = {'all': {'correct': 0, 'total': 0},
                  'train': {'correct': 0, 'total': 0},
                  'val': {'correct': 0, 'total': 0},
                  'test': {'correct': 0, 'total': 0}}
        predictions = []
        valid_stop = 0
        for row in outputs:
            try:
                answer = normalize_nn(row['generated'])
                valid_stop += 1
                correct = grader.grade(row['case_id'], answer)
            except ValueError:
                correct = False
            split = bank.index[row['case_id']][1]
            for key in ('all', split):
                counts[key]['total'] += 1
                counts[key]['correct'] += int(correct)
            predictions.append(row | {'correct': correct, 'bank_split': split})
        assert before_hash == hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        results.append({'seed': seed, 'checkpoint_sha256': before_hash,
                        'shape': [net.L, net.H], 'parameters': net.parameters,
                        'counts': counts, 'syntactically_completed': valid_stop,
                        'prediction_replay_equal': True, 'checkpoint_unchanged': True,
                        'predictions': predictions})
    compact = {'status': 'passed', 'kind': 'actual-NN-inference-integration',
               'interpretation': 'P030 already-exposed truth table; bank splits differ from original P030; not new blind generalization',
               'new_training': False, 'vm_status': 'not_executed',
               'model_source_sha256': hashlib.sha256(args.model_source.read_bytes()).hexdigest(),
               'numpy': np.__version__, 'wall_seconds': time.perf_counter() - started,
               'models': [{k: v for k, v in row.items() if k != 'predictions'} for row in results]}
    (args.out / 'predictions.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.out / 'compact.json').write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding='utf-8')
    print(canonical_json(compact))


if __name__ == '__main__':
    main()
