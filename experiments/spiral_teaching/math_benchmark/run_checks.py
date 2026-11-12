"""One bounded bank build + actual acceptance run; emit compact machine evidence."""
import argparse
import hashlib
import json
import platform
import sys
import time
import unittest
from pathlib import Path

import teacher
from student_io import StudentBank, canonical_json
from test_bank import BankTests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Choose a fresh evidence directory')
    args.out.mkdir(parents=True)
    started = time.perf_counter()
    with (args.out / 'tests.txt').open('w', encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(BankTests))
    if not result.wasSuccessful():
        compact = {'status': 'failed', 'tests': result.testsRun,
                   'failures': len(result.failures), 'errors': len(result.errors),
                   'log': str(args.out / 'tests.txt')}
        (args.out / 'compact.json').write_text(json.dumps(compact, indent=2), encoding='utf-8')
        print(canonical_json(compact))
        return 1
    manifest = teacher.build_bank(args.out / 'bank')
    bank = StudentBank(args.out / 'bank')
    # Transport receipts, not VM learning or NN prediction accuracy.
    nn_digest, vm_digest = hashlib.sha256(), hashlib.sha256()
    def nn_receive(raw):
        nn_digest.update((raw + '\n').encode())
        return 'transport-only'
    def vm_receive(raw):
        vm_digest.update((raw + '\n').encode())
        return 'transport-only'
    for p in teacher.profiles():
        for split in ('train', 'val', 'test'):
            bank.dispatch(p.profile_id, split, nn_receive)
            bank.dispatch(p.profile_id, split, vm_receive)
    assert nn_digest.digest() == vm_digest.digest()
    lengths = {}
    for t, raw in teacher.generate():
        counts = lengths.setdefault(t.profile_id, {'cases': 0, 'question_bits': 0,
                                                 'answer_bits': 0, 'max_q': 0, 'max_prefix': 0})
        counts['cases'] += 1
        counts['question_bits'] += len(raw)
        counts['answer_bits'] += len(t.result_bits)
        counts['max_q'] = max(counts['max_q'], len(raw))
        counts['max_prefix'] = max(counts['max_prefix'], len(raw) + len(t.result_bits))
    (args.out / 'lengths.json').write_text(json.dumps(lengths, indent=2), encoding='utf-8')
    compact = {'status': 'passed', 'tests': result.testsRun, 'failures': 0, 'errors': 0,
               'cases': manifest['cases'], 'profiles': len(manifest['profiles']),
               'semantic_groups': manifest['semantic_groups'],
               'teacher_prefixes_checked': manifest['teacher_prefixes_checked'],
               'transport_both_sha256': nn_digest.hexdigest(),
               'transport_status': 'recording-sinks-only; actual VM student not executed',
               'new_training': False, 'pending': manifest['pending'],
               'bank_files_sha256': manifest['files'],
               'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(Path(__file__).parent.glob('*.py'))},
               'python': platform.python_version(), 'wall_seconds': time.perf_counter() - started}
    (args.out / 'compact.json').write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding='utf-8')
    print(canonical_json(compact))
    return 0


if __name__ == '__main__':
    sys.exit(main())
