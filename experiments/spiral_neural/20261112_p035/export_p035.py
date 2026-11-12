"""P035 explicit public whitelist, byte-verified ZIPs and Git API upload data.

Default mode only writes an export plan. Finalization requires all12 completed
primary/replay results, final documents, engineering evidence and parent review.
"""
import argparse
import base64
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import zipfile
import zlib

import numpy as np

PREFIX = 'experiments/spiral_neural/20261112_p035/'
ZIP_LIMIT = 3000000
CHUNK = 12000
CODEC_SHA = '0f38c76789f19cad6cc0ca4967b30fdb69b09416b48f77f5c3669b84babd19b2'
HOME = re.compile(r"(?i)(?:[a-z]:[\\/]users[\\/]|/(?:home|users)/)[^/\\\s\"']+")
SECRET = re.compile(r'(?:sk-or-v1-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})')
PRIVATE_FIELDS = {'raw_api_path', 'private_raw_api_record', 'raw_api_record', 'raw_api_response', 'raw_response',
                  'autonomous_state', 'account_metadata', 'account_state', 'privatehome', 'private_home',
                  'home_dir', 'user_home', 'api_key', 'apikey', 'authorization_header', 'access_token', 'refresh_token',
                  'private_key', 'credentials', 'quota', 'account_quota', 'remaining_quota', 'daily_quota', 'quota_remaining'}


def read(path):
    return json.loads(path.read_bytes().decode('utf-8'))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    assert name and not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name
    assert not any(part in name.lower() for part in ('__pycache__', 'mpl-cache', 'fontcache', '.env', '.aws', '/home/', 'raw-api', 'autonomous-state'))
    assert not HOME.search(name) and not SECRET.search(name)


def public_json(value, removed, pointer=''):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            location = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            private_auth_header = (key.lower() == 'authorization' and isinstance(item, str)
                                   and re.match(r'(?i)^(?:bearer|basic)\s+\S+', item))
            if key.lower() in PRIVATE_FIELDS or private_auth_header or isinstance(item, str) and HOME.search(item):
                removed.append({'json_pointer': location, 'original_value_sha256': digest(json.dumps(item, ensure_ascii=False, sort_keys=True).encode('utf-8')),
                                'reason': 'Private machine/API/account metadata removed only from PUBLIC copy'})
            else:
                result[key] = public_json(item, removed, location)
        return result
    if isinstance(value, list):
        return [public_json(item, removed, pointer + '/' + str(i)) for i, item in enumerate(value)]
    if isinstance(value, float):
        assert math.isfinite(value), pointer
    return value


def finite_npz(data, name):
    with np.load(BytesIO(data), allow_pickle=False) as state:
        assert state.files, name
        for key in state.files:
            array = state[key]
            assert array.dtype != object, (name, key)
            if np.issubdtype(array.dtype, np.number):
                assert np.isfinite(array).all(), (name, key)
            elif array.dtype.kind in 'SU':
                assert not HOME.search(str(array)) and not SECRET.search(str(array)), (name, key)


def load_entry(path, name, root):
    safe_name(name)
    original = path.read_bytes()
    data, removed = original, []
    if path.suffix == '.json':
        value = public_json(json.loads(original.decode('utf-8')), removed)
        if removed:
            data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if path.suffix.lower() in ('.py', '.json', '.md', '.txt'):
        text = data.decode('utf-8')
        assert text.encode('utf-8') == data
        assert not HOME.search(text) and not SECRET.search(text), name
    if path.suffix == '.npz':
        finite_npz(data, name)
    try:
        source = path.relative_to(root).as_posix()
    except ValueError:
        raise ValueError('Selected artifact is outside the declared workspace')
    return {'name': name, 'source': source, 'source_sha256': digest(original),
            'sha256': digest(data), 'git_blob': git_blob(data), 'bytes': len(data), 'redactions': removed, 'data': data}


def meta(entry):
    return {key: value for key, value in entry.items() if key != 'data'}


def selection(root, run, publication, engineering):
    source = root / 'outputs/sle-p035'
    work = root / 'work/sle-p035'
    direct, evidence = [], []
    def add(group, path, name):
        group.append((path, name))
    for name in ('codec_course.py', 'run_p035.py', 'summarize_p035.py', 'plot_p035.py', 'export_p035.py',
                 'protocol.json', 'source-freeze.json', 'review_notes.json', 'integration_review.json', 'README.md',
                 'P035-事前規格-2026-11-12.md', 'P035-輸入編碼與容量時序實測結果-2026-11-12.md'):
        add(direct, source / name, name)
    for name in ('student_io.py', 'teacher.py', 'reference_codec.py', 'p030_reference.py', 'lineage.json'):
        add(direct, source / 'reference' / name, 'reference/' + name)
    for name in ('compact.json', 'P035-paired-milestones.png', 'P035-stage-curves.png', 'plot-checks.json'):
        add(direct, publication / name, name)
    for name in ('summary-table.json', 'report-facts.json'):
        add(evidence, publication / name, 'analysis/' + name)
    for name in ('compact.json', 'results.json', 'manifest.json'):
        add(evidence, run / name, 'run/' + name)
    stage_names = ('s0_echo_d1', 's1_echo_d2', 's2_echo_d3', 's3_op2', 's4_neg')
    for policy in ('F', 'G'):
        for seed in (101, 202, 303):
            for stage in stage_names:
                name = f'courses/{policy}-seed{seed}/{stage}.json'
                add(evidence, run / name, 'run/' + name)
    for codec in ('S', 'H'):
        for policy in ('F', 'G'):
            for seed in (101, 202, 303):
                student = f'{codec}-{policy}-seed{seed}'
                for name in ('initial-state.npz', 'initialization.json', 'final-state.npz', 'final-truth.json',
                             'final-failures.json', 'result.json', 'exposure-ledger.json', 'interface-exposure.json'):
                    add(evidence, run / student / name, f'run/{student}/{name}')
                for stage in stage_names:
                    for name in ('growth.json', 'curve.json', 'summary.json', 'state-0.npz', 'state-100.npz'):
                        add(evidence, run / student / stage / name, f'run/{student}/{stage}/{name}')
                    for fraction in (0, 25, 50, 75, 100):
                        name = f'truth-{fraction}.json'
                        add(evidence, run / student / stage / name, f'run/{student}/{stage}/{name}')
    for name in ('checks.json', 'codec-course-description.json', 'course-checks.json', 'exposure-ledgers.json',
                 'actual-NN-interface.json', 'actual-NN-interface-tensors.npz'):
        add(evidence, work / 'codec-final-gate' / name, 'engineering/codec-final-gate/' + name)
    add(evidence, engineering, 'engineering/runner/checks.json')
    # Public advisory/review outputs only. No worker scripts, raw API files,
    # account state, source-plan dump, caches or whole autonomous workspaces.
    for name in ('public_request.json', 'request_provenance.json', 'public_candidate.json', 'local_checks.json', 'codec_independent_checks.json'):
        add(evidence, work / 'nvidia-review' / name, 'reviews/' + name)
    for folder in ('independent-engineering', 'integration-review'):
        for name in ('checks.json', 'compact.json', 'final_review.json'):
            path = work / folder / name
            if path.is_file():
                add(evidence, path, 'reviews/' + folder + '/' + name)
    return {'direct': direct, 'evidence': evidence}


def make_zip(entries):
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in sorted(entries, key=lambda x: x['name']):
            info = zipfile.ZipInfo(entry['name'], date_time=(2026, 11, 12, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entry['data'], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    data = output.getvalue()
    with zipfile.ZipFile(BytesIO(data)) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == sorted(entry['name'] for entry in entries)
        for entry in entries:
            actual = archive.read(entry['name'])
            assert actual == entry['data'] and digest(actual) == entry['sha256']
            if entry['name'].endswith('.npz'):
                finite_npz(actual, entry['name'])
    return data


def zip_batches(entries):
    batches, current, size = [], [], 200
    for entry in sorted(entries, key=lambda x: x['name']):
        estimate = len(zlib.compress(entry['data'], 9)) + 2 * len(entry['name'].encode('utf-8')) + 160
        if current and size + estimate > ZIP_LIMIT - 4096:
            batches.append(current)
            current, size = [], 200
        current.append(entry)
        size += estimate
    if current:
        batches.append(current)
    result = []
    for batch in batches:
        data = make_zip(batch)
        if len(data) > ZIP_LIMIT:
            assert len(batch) > 1, 'One selected file exceeds ZIP size cap'
            middle = len(batch) // 2
            result.extend(zip_batches(batch[:middle]))
            result.extend(zip_batches(batch[middle:]))
        else:
            result.append((data, batch))
    return result


def generated(name, value):
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    return {'name': name, 'source': 'generated-public-metadata', 'source_sha256': digest(data),
            'sha256': digest(data), 'git_blob': git_blob(data), 'bytes': len(data), 'redactions': [], 'data': data}


def final_guard(root, run, publication):
    source = root / 'outputs/sle-p035'
    assert sha(source / 'codec_course.py') == CODEC_SHA
    summary = read(publication / 'summary-table.json')
    assert summary['status'] == 'passed' and len(summary['students']) == 12
    assert summary['all_primary_and_replay_completed']
    review = read(source / 'integration_review.json')
    assert review['status'] == 'final_protocol_artifact_and_inference_review_pass'
    assert review['actionable_implementation_findings'] == []
    assert sha(run / 'manifest.json') == review['manifest_sha256']
    assert sha(run / 'compact.json') == review['compact_sha256']
    for name, expected in review['source_sha256'].items():
        assert sha(source / name) == expected, ('independently reviewed source changed', name)
    # Source-freeze is the root's pre-training scientific authority. Resolve
    # only explicit file/digest records, never execute text from that record.
    freeze = read(source / 'source-freeze.json')
    assert freeze['formal_students_started'] == freeze['formal_student_updates'] == 0
    verified = {}
    def walk(value):
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            candidate = item if isinstance(item, str) else item.get('sha256') if isinstance(item, dict) else None
            if Path(key).suffix in ('.py', '.json', '.md') and isinstance(candidate, str) and re.fullmatch('[0-9a-f]{64}', candidate):
                options = [source / key, root / key]
                paths = list({p.resolve() for p in options if p.is_file()})
                assert paths, ('source-freeze file unavailable', key)
                assert any(sha(path) == candidate for path in paths), ('source-freeze mismatch', key)
                verified[key] = candidate
            walk(item)
    walk(freeze)
    assert verified, 'No explicit scientific source hashes found in source-freeze'
    return verified


def finalize(root, run, publication, selected):
    guards = final_guard(root, run, publication)
    assert not publication.is_relative_to(run), 'Publication directory must be outside the scientific run tree'
    groups = {kind: [load_entry(path, name, root) for path, name in pairs] for kind, pairs in selected.items()}
    published_sources = {entry['source'] for entries in groups.values() for entry in entries}
    inventory = {path.relative_to(run).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path),
                    'published': path.relative_to(root).as_posix() in published_sources}
                 for path in sorted(run.rglob('*')) if path.is_file()}
    groups['direct'].append(generated('local-artifact-hashes.json', inventory))
    redactions = {entry['name']: {key: entry[key] for key in ('source', 'source_sha256', 'sha256', 'redactions')}
                  for entries in groups.values() for entry in entries if entry['redactions']}
    groups['direct'].append(generated('public-source-redactions.json', {'policy': 'Only listed machine/private metadata fields removed from PUBLIC JSON copies; scientific arrays/numbers/source unchanged. Originals remain local.', 'files': redactions}))
    public = publication / 'public'
    public.mkdir(parents=True, exist_ok=True)
    files, zip_entries = {}, {}
    for entry in groups['direct']:
        path = public / entry['name']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(entry['data'])
        files[entry['name']] = meta(entry)
    for i, (data, batch) in enumerate(zip_batches(groups['evidence']), 1):
        name = 'evidence' + ('' if i == 1 else f'-{i:02d}') + '.zip'
        (public / name).write_bytes(data)
        (publication / name).write_bytes(data)
        files[name] = {'sha256': digest(data), 'bytes': len(data), 'git_blob': git_blob(data)}
        zip_entries[name] = [meta(entry) for entry in batch]
    local_traces = {name: row for name, row in inventory.items() if name.endswith('token-trace.jsonl.gz')}
    record = generated('PUBLICATION_RECORD.json', {
        'id': 'P035-PUBLICATION-RECORD', 'author': 'Codex',
        'scope': 'Whitelist-only new P035 input-codec/capacity-timing package. No Git operation, old experiment modification or new scientific execution during export.',
        'ZIP_coverage': {name: {'entries': len(rows), **files[name]} for name, rows in zip_entries.items()},
        'scientific_source_freeze_sha256': sha(root / 'outputs/sle-p035/source-freeze.json'),
        'scientific_and_engineering_file_guards': guards,
        'integration_review_sha256': sha(root / 'outputs/sle-p035/integration_review.json'),
        'private_PUBLIC_copy_redactions': redactions,
        'original_private_metadata_policy': 'Unmodified originals remain local; only the listed public-copy fields are removed, never scientific numbers or source code.',
        'full_target_traces_local_only': {'files': len(local_traces), 'bytes': sum(row['bytes'] for row in local_traces.values()),
                                        'exact_source_SHA_list': 'local-artifact-hashes.json'},
        'published_NPZ_files': sum(entry['name'].endswith('.npz') for entry in groups['evidence']),
        'selected_states': 'Every student initial/final and every stage0/100percent full state; intermediate quarter states stay local with SHA.',
        'all_fixed_quarter_truth_tables_included': True,
        'no_P033_checkpoint_or_private_account_dependency': True,
        'source_newline_policy': 'read_bytes().decode(UTF-8) for API text; preserve original CRLF and raw source bytes.',
        'checks': {'every_ZIP_entry_exact_byte_roundtrip': True, 'every_selected_NPZ_numeric_array_finite': True,
                   'max_ZIP_bytes': ZIP_LIMIT, 'base64_chunk_characters': CHUNK},
        'Git_record': 'Root records the eventual Git publication separately after sealing; account state and doc-updates are not part of this science package.',
    })
    (public / record['name']).write_bytes(record['data'])
    groups['direct'].append(record)
    files[record['name']] = meta(record)
    manifest = {'schema': 'P035-public-bundle-v1', 'repository_prefix': PREFIX,
                'files': {name: {key: row[key] for key in ('sha256', 'bytes', 'git_blob')} for name, row in sorted(files.items())},
                'zip_entries': zip_entries, 'source_freeze_verified': guards, 'private_public_copy_redactions': redactions,
                'full_trace_policy': 'Complete target traces and omitted quarter states remain local with exact SHA in local-artifact-hashes.json.',
                'no_historical_checkpoint_dependency': True, 'ZIP_bytes_cap': ZIP_LIMIT,
                'every_entry_byte_roundtrip': True, 'NPZ_numeric_finite': True,
                'scope': 'All12 fixed students included; nested milestones are not independent skills; common response isolates input codec; no native-output/system-cost superiority claim.'}
    manifest_entry = generated('package-manifest.json', manifest)
    (public / 'package-manifest.json').write_bytes(manifest_entry['data'])
    dump(publication / 'package-manifest.json', manifest)
    files['package-manifest.json'] = meta(manifest_entry)
    text_entries, binaries, expected = [], [], {}
    for name in sorted(files):
        data = (public / name).read_bytes()
        assert digest(data) == files[name]['sha256'] and git_blob(data) == files[name]['git_blob']
        target = PREFIX + name
        expected[target] = git_blob(data)
        if Path(name).suffix in ('.py', '.md', '.json', '.txt'):
            content = data.decode('utf-8')  # Preserve original CRLF exactly.
            assert content.encode('utf-8') == data
            text_entries.append({'path': target, 'mode': '100644', 'type': 'blob', 'content': content})
        else:
            encoded = base64.b64encode(data).decode('ascii')
            chunks = []
            folder = publication / 'base64-chunks' / name.replace('/', '__')
            folder.mkdir(parents=True, exist_ok=True)
            for offset in range(0, len(encoded), CHUNK):
                chunk = folder / f'{offset // CHUNK:05d}.txt'
                chunk.write_text(encoded[offset:offset + CHUNK], encoding='ascii')
                chunks.append(chunk.relative_to(publication).as_posix())
            assert base64.b64decode(''.join((publication / p).read_text(encoding='ascii') for p in chunks), validate=True) == data
            binaries.append({'path': target, 'mode': '100644', 'type': 'blob', 'bytes': len(data),
                             'sha256': digest(data), 'git_blob': git_blob(data), 'chunks': chunks, 'chunk_characters': CHUNK})
    dump(publication / 'text-tree-entries.json', text_entries)
    for i, entry in enumerate(text_entries):
        dump(publication / f'text-entry-{i:03d}.json', entry)
    dump(publication / 'binary-entries.json', binaries)
    dump(publication / 'expected-git-blobs.json', expected)
    assert final_guard(root, run, publication) == guards
    for entries in groups.values():
        for entry in entries:
            if entry['source'] != 'generated-public-metadata':
                assert sha(root / entry['source']) == entry['source_sha256'], ('original selected source changed', entry['source'])
    result = {'status': 'passed', 'published_files': len(files), 'text_entries': len(text_entries),
              'binary_files': len(binaries), 'base64_chunks': sum(len(row['chunks']) for row in binaries),
              'ZIPs': {name: files[name] for name in zip_entries},
              'ZIP_entries_byte_equal': True, 'NPZ_finite': True, 'source_guards_after_export': True,
              'private_fields_redacted_files': len(redactions), 'originals_changed': False,
              'package_manifest': str(publication / 'package-manifest.json')}
    dump(publication / 'export-checks.json', result)
    dump(publication / 'publish-index.json', {
        'schema': 'P035-publication-upload-index-v1', 'repository_prefix': PREFIX,
        'public_directory': str(public), 'published_files': len(files),
        'text_entries': {'count': len(text_entries), 'json': str(publication / 'text-tree-entries.json'),
                         'individual_files': [str(publication / f'text-entry-{i:03d}.json') for i in range(len(text_entries))]},
        'binary_entries': {'count': len(binaries), 'json': str(publication / 'binary-entries.json'),
                           'total_chunks': sum(len(row['chunks']) for row in binaries), 'chunk_characters': CHUNK,
                           'files': [{key: row[key] for key in ('path', 'bytes', 'sha256', 'git_blob')} |
                                     {'chunks': len(row['chunks'])} for row in binaries]},
        'expected_git_blobs': str(publication / 'expected-git-blobs.json'),
        'package_manifest': {'path': str(publication / 'package-manifest.json'),
                             'sha256': files['package-manifest.json']['sha256'], 'git_blob': files['package-manifest.json']['git_blob']},
        'checks': str(publication / 'export-checks.json'),
        'root_Git_publication_record': 'Separate additional record after sealing; no self-reference or Git base hardcoded here.',
    })
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--runner-checks', type=Path)
    parser.add_argument('--finalize', action='store_true')
    args = parser.parse_args()
    root, run = args.root.resolve(), args.run.resolve()
    publication = args.out.resolve() if args.out else root / 'work/sle-p035/publication'
    engineering = args.runner_checks.resolve() if args.runner_checks else root / 'work/sle-p035/runner-engineering-final/checks.json'
    publication.mkdir(parents=True, exist_ok=True)
    selected = selection(root, run, publication, engineering)
    missing = [path.relative_to(root).as_posix() for pairs in selected.values() for path, _ in pairs if not path.is_file()]
    if not args.finalize:
        dump(publication / 'export-plan.json', {'finalized': False, 'missing': missing,
             'selection': {kind: [{'source': p.relative_to(root).as_posix(), 'name': name} for p, name in pairs] for kind, pairs in selected.items()}})
        print(json.dumps({'status': 'ready' if not missing else 'waiting', 'finalized': False,
                          'missing_count': len(missing), 'selected_counts': {kind: len(pairs) for kind, pairs in selected.items()}}))
        return
    assert not missing, 'Required final whitelist entries missing: ' + repr(missing)
    finalize(root, run, publication, selected)


if __name__ == '__main__':
    main()
