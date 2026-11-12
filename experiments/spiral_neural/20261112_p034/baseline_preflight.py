"""Verify pinned historical B0, course identity and read-only re-inference."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'reference'))
import p033 as prior
import numpy as np


def read(p):
    return json.loads(p.read_text('utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--p033-run', type=Path, required=True)
    p.add_argument('--p033-publication', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a fresh baseline verification directory')
    published = read(args.p033_publication / 'expected-git-blobs.json')
    artifact_inventory = None
    for entry in args.p033_publication.glob('entry-*.json'):
        value = read(entry)
        if value['path'].endswith('/local-artifact-hashes.json'):
            artifact_inventory = json.loads(value['content'])
    if artifact_inventory is None:
        raise ValueError('Pinned public inventory not found')
    source_hashes = {}
    for name in ('p033.py', 'p032_reference.py', 'p030_reference.py', 'diagnostic.py'):
        source = HERE / 'reference' / name
        raw = source.read_bytes()
        git_hash = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert git_hash == published['experiments/spiral_neural/20261112_p033/' + name]
        source_hashes[name] = sha(source)
    args.out.mkdir(parents=True)
    results, courses = [], []
    for group, split_name in [('G0', 'S0'), ('G1', 'C1')]:
        split = prior.SPLITS[split_name]
        for seed in (101, 202, 303):
            folder = args.p033_run / 'timing' / f'{group}-seed{seed}-T1'
            for name in ('trace.json', 'state-3000.npz', 'truth-table-3000.json', 'result.json'):
                path = folder / name
                relative = path.relative_to(args.p033_run).as_posix()
                assert sha(path) == artifact_inventory[relative]['sha256'], relative
            lessons = [list(t) for t in prior.multiset_lessons(split['train'], seed, 'T1')]
            trace = read(folder / 'trace.json')
            assert lessons == [r[:2] for r in trace]
            course_bytes = json.dumps(lessons, separators=(',', ':')).encode()
            course_hash = hashlib.sha256(course_bytes).hexdigest()
            (args.out / f'lessons-{group}-{seed}.json').write_bytes(course_bytes)
            courses.append({'group': group, 'split': split_name, 'seed': seed, 'sha256': course_hash,
                            'presentations': 3000, 'target_updates': 15000, 'train_values': split['train'],
                            'source_trace_sha256': sha(folder / 'trace.json')})
            state_file = folder / 'state-3000.npz'
            digest = sha(state_file)
            net = prior.old.restore(state_file, seed)
            frozen = net.state()
            old_table = read(folder / 'truth-table-3000.json')
            new_table = [prior.old.truth_row(net, prior.ref.PHASES[4], op, v) for op in (0, 1) for v in range(8)]
            assert old_table == new_table
            assert prior.ref.equal_state(frozen, net.state()) and digest == sha(state_file)
            metrics = {k: prior.ref.small(prior.ref.metrics(net, prior.ref.PHASES[4], split[k])) for k in ('train', 'val', 'test')}
            old_result = read(folder / 'result.json')
            assert metrics == old_result['metrics']
            results.append({'group': group, 'split': split_name, 'seed': seed, 'parameters': net.parameters,
                            'metrics': metrics, 'source_checkpoint_sha256': digest,
                            'historical_training': True, 'current_read_only_inference': True,
                            'rerun_training': False, 'all_sixteen_truth_rows_recomputed_equal': True})
    result = {'status': 'passed', 'source_commit': 'e217bd0fd6cfe654062c3615ee2aa73a36d1ca71',
              'source_sha256': source_hashes, 'learners': 6, 'read_only_Qs': 96,
              'new_B0_training': False, 'numpy': np.__version__, 'courses': courses, 'rows': results}
    (args.out / 'compact.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('courses', 'rows', 'source_sha256')}))


if __name__ == '__main__':
    main()
