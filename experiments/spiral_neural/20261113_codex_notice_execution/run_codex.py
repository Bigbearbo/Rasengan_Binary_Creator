"""Execute the unchanged Pro UR1 trial with portable manifest path keys only.

No learner, data, curriculum, budget, stopping or evaluation function is changed.
The only adaptation replaces Windows separators in source-hash metadata keys.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import unittest

if sys.flags.optimize:
    raise RuntimeError('Optimized Python is disabled')
sys.dont_write_bytecode = True
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
PRO_HEAD = '0b6de1d24481c2886833e412d173645fca98609c'
MANIFEST_SHA = 'd74dedb0627d79a8c41057a1625a3e83ab3c5b2edfbb675fccd902e94929a7b0'
COURSE = 'experiments/spiral_neural/20261113_pro_notice_learning'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def posix_metadata(manifest):
    original = manifest['source_hashes']
    normalized = {key.replace('\\', '/'): value for key, value in original.items()}
    if len(normalized) != len(original):
        raise ValueError('Source metadata key collision')
    return manifest | {'source_hashes': normalized}


def inspect(source):
    course = source / COURSE
    manifest_path = course / 'frozen_manifest.json'
    assert sha(manifest_path) == MANIFEST_SHA, 'Original manifest bytes changed'
    frozen = read(manifest_path)
    freeze = read(course / 'source-freeze.json')
    assert freeze['manifest_sha256'] == MANIFEST_SHA
    assert freeze['source_hashes'] == frozen['source_hashes']
    for name, expected in frozen['source_hashes'].items():
        path = (source / name).resolve(strict=True)
        assert path.is_relative_to(source) and sha(path) == expected, name
    imported = source.parent / 'source-import.json'
    blob_count = 0
    if imported.exists():
        records = read(imported)
        assert records['base_head'] == PRO_HEAD
        for item in records['files']:
            content = (source / item['path']).read_bytes()
            actual = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            assert actual == item['git_blob'], ('Imported Git blob differs', item['path'])
            blob_count += 1
    sys.path.insert(0, str(course))
    trial = importlib.import_module('run_trial')
    original_build = trial.build_manifest
    native = original_build()
    normalized = posix_metadata(native)
    assert normalized == frozen, 'Scientific manifest differs after path normalization'
    assert {k: v for k, v in native.items() if k != 'source_hashes'} == {
        k: v for k, v in frozen.items() if k != 'source_hashes'}
    trial.build_manifest = lambda: posix_metadata(original_build())
    assert trial.validate_manifest(manifest_path, MANIFEST_SHA) == frozen
    return trial, manifest_path, {
        'status': 'PASS', 'base_head': PRO_HEAD, 'manifest_sha256': MANIFEST_SHA,
        'scientific_source_hashes_verified': len(frozen['source_hashes']),
        'imported_Git_blobs_verified': blob_count,
        'native_manifest_exact': native == frozen,
        'normalized_manifest_exact': True,
        'adaptation': 'source_hashes relative path key separators only',
        'runtime': frozen['runtime'],
        'formal_students_started': 0,
        'formal_heldout_neural_evaluations': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--inspect', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--approved-manifest-sha')
    parser.add_argument('--approved-launcher-sha')
    parser.add_argument('--claim-commit')
    args = parser.parse_args()
    source = args.source_root.resolve(strict=True)
    trial, manifest_path, inspection = inspect(source)
    if args.inspect:
        print(json.dumps(inspection, ensure_ascii=False, sort_keys=True))
        return
    if args.out is None:
        parser.error('--out is required')
    output = args.out.resolve()
    if args.check:
        output.mkdir(parents=True, exist_ok=False)
        started = time.perf_counter()
        preflight = trial.preflight()
        suite = unittest.defaultTestLoader.discover(str(source / COURSE), pattern='test_engineering.py')
        assert suite.countTestCases() == 6
        with (output / 'unittest.log').open('x', encoding='utf-8') as log:
            tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        assert tests.wasSuccessful(), 'Read the local unittest.log'
        # Actual metadata mismatches must still fail; normalization is not a bypass.
        original = trial.build_manifest
        for field, invalid in [('runtime', {}), ('data_sha256', '0' * 64), ('curricula', {})]:
            def changed(field=field, invalid=invalid):
                return original() | {field: invalid}
            trial.build_manifest = changed
            try:
                trial.validate_manifest(manifest_path, MANIFEST_SHA)
            except ValueError:
                pass
            else:
                raise AssertionError('Manifest mismatch was accepted: ' + field)
            finally:
                trial.build_manifest = original
        result = inspection | {'engineering_tests': tests.testsRun,
            'preflight': preflight, 'metadata_rejection_checks': 3,
            'synthetic_optimizer_update_calls': 12,
            'seconds': time.perf_counter() - started,
            'launcher_sha256': sha(__file__)}
        write_new(output / 'checks.json', result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return
    if args.approved_manifest_sha != MANIFEST_SHA or args.approved_launcher_sha != sha(__file__):
        raise ValueError('Explicit approved original manifest and launcher hashes required')
    if not args.claim_commit or len(args.claim_commit) != 40 or any(c not in '0123456789abcdef' for c in args.claim_commit):
        raise ValueError('Existing preregistration/ownership commit required')
    assert not output.exists(), 'Never overwrite or restart an existing experiment'
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'execution_author': 'Codex', 'design_implementation_author': 'ChatGPT Pro',
        'source_head': PRO_HEAD, 'ownership_preregistration_commit': args.claim_commit,
        'manifest_sha256': MANIFEST_SHA, 'launcher_sha256': sha(__file__),
        'started_UTC': datetime.now(timezone.utc).isoformat(), 'inspection': inspection,
        'runtime_adaptation': 'Only source hash metadata path separators; original seven science files unchanged',
        'original_summary_author_field_is_source_design_attribution': True,
        'actual_local_external_worker_calls_are_recorded_separately': True,
        'auto_retry': False}
    write_new(output.parent / 'codex-execution-receipt.json', receipt)
    trial.execute(manifest_path, MANIFEST_SHA, output)
    write_new(output / 'codex-execution-provenance.json', receipt | {
        'completed_UTC': datetime.now(timezone.utc).isoformat(), 'source_verification_after': inspect(source)[2],
        'status': 'complete'})


if __name__ == '__main__':
    main()
