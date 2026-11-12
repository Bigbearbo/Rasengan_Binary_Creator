"""Whitelist-only P034 public export with byte verification and API upload data.

Default --plan never creates an archive. Use --finalize only after the parent
review approves the final documents and integrated experiment evidence.
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

REPOSITORY_PREFIX = 'experiments/spiral_neural/20261112_p034/'
MAX_ZIP_BYTES = 3000000
CHUNK_CHARACTERS = 12000
SEEDS = (101, 202, 303)
GROUPS = ('G0', 'G1')
SPLITS = ('S0', 'C0', 'S1', 'C1')
REPORT = 'P034-等曝光與近等參數表示實測結果-2026-11-12.md'
CODE = ('attention_model.py', 'test_attention.py', 'b1_trial.py', 'e900.py',
        'baseline_preflight.py', 'summarize_p034.py', 'plot_p034.py',
        'export_p034.py', 'prepare_public_inputs.py', 'reproduce.py')
DESIGN = ('PRO_RESEARCH_DESIGN_20261112.md', 'CURRENT_RESEARCH_STATUS.md',
          'PR8_AGENTS.md', 'spiral_language_research_index.md')
REFERENCE = ('p030_reference.py', 'p032_reference.py', 'p033.py', 'diagnostic.py')
HOME_PATH = re.compile(r"(?i)(?:[a-z]:[\\/]users[\\/]|/(?:home|users)/)[^/\\\s\"']+")
SECRET = re.compile(r'(?:sk-or-v1-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})')
DROP_METADATA_FIELDS = {'raw_api_path', 'privatehome', 'private_home', 'user_home', 'home_dir'}
FORBIDDEN_JSON_KEYS = {'api_key', 'apikey', 'authorization', 'access_token', 'refresh_token',
                       'private_key', 'remaining_quota', 'daily_quota', 'quota_remaining', 'quota'}


def read(path):
    return json.loads(path.read_bytes().decode('utf-8'))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def valid_name(name):
    path = PurePosixPath(name)
    assert name and not path.is_absolute() and '..' not in path.parts and '\\' not in name and ':' not in name
    lower = name.lower()
    assert not any(part in lower for part in ('fontcache', 'mpl-cache', '__pycache__', '.env', '.aws', 'api-quota', 'raw-api', '/home/'))
    assert not HOME_PATH.search(name) and not SECRET.search(name)


def finite_json(value, pointer=''):
    if isinstance(value, float):
        assert math.isfinite(value), pointer
    elif isinstance(value, dict):
        for key, item in value.items():
            assert key.lower() not in FORBIDDEN_JSON_KEYS, f'PRIVATE KEY/QUOTA FIELD: {pointer}/{key}'
            finite_json(item, pointer + '/' + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            finite_json(item, pointer + '/' + str(i))


def sanitize_metadata(value, removed, pointer=''):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            location = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            if key.lower() in DROP_METADATA_FIELDS or (isinstance(item, str) and HOME_PATH.search(item)):
                removed.append({'json_pointer': location, 'reason': 'private local path metadata removed from PUBLIC copy only',
                                'original_value_sha256': sha_bytes(json.dumps(item, ensure_ascii=False, sort_keys=True).encode('utf-8'))})
            else:
                result[key] = sanitize_metadata(item, removed, location)
        return result
    if isinstance(value, list):
        return [sanitize_metadata(item, removed, pointer + '/' + str(i)) for i, item in enumerate(value)]
    return value


def validate_npz(data, name):
    with np.load(BytesIO(data), allow_pickle=False) as state:
        assert state.files, name
        for key in state.files:
            array = state[key]
            assert array.dtype != object, (name, key)
            if np.issubdtype(array.dtype, np.number):
                assert np.isfinite(array).all(), (name, key, 'nonfinite')
            elif array.dtype.kind in 'SU':
                text = str(array)
                assert not HOME_PATH.search(text) and not SECRET.search(text), (name, key, 'private metadata')


def payload(source, logical_name, root):
    valid_name(logical_name)
    original = source.read_bytes()
    data, removed = original, []
    if source.suffix.lower() == '.json':
        value = json.loads(original.decode('utf-8'))
        public_value = sanitize_metadata(value, removed)
        finite_json(public_value)
        if removed:
            data = (json.dumps(public_value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if source.suffix.lower() in ('.py', '.md', '.json', '.svg', '.txt'):
        text = data.decode('utf-8')
        assert not HOME_PATH.search(text), f'PRIVATE HOME PATH: {logical_name}'
        assert not SECRET.search(text), f'SECRET PATTERN: {logical_name}'
        assert text.encode('utf-8') == data
    if source.suffix.lower() == '.npz':
        validate_npz(data, logical_name)
    return {
        'name': logical_name, 'source': source.relative_to(root).as_posix(),
        'source_sha256': sha_bytes(original), 'sha256': sha_bytes(data), 'bytes': len(data),
        'git_blob': blob(data), 'redactions': removed, 'data': data,
    }


def selected_files(root, publication):
    """Every public source/evidence/input path is named explicitly here."""
    source = root / 'outputs/sle-p034'
    work = root / 'work/sle-p034'
    direct, evidence, supplement = [], [], []

    def choose(target, path, name):
        target.append((path, name))

    for name in CODE + ('protocol.json', 'review_notes.json', 'integration_review.json', 'README.md', REPORT):
        choose(direct, source / name, name)
    for name in REFERENCE:
        choose(direct, source / 'reference' / name, 'reference/' + name)
    choose(direct, root / 'outputs/sle-p033/echo_only_followup.py', 'reference/echo_only_followup.py')
    for name in DESIGN:
        choose(direct, work / 'source-plan' / name, 'design/' + name)
    for name in ('compact.json', 'summary-table.json', 'plot-checks.json', 'b1-error-analysis.json',
                 'P034-E900-paired.png', 'P034-E900-paired.svg',
                 'P034-attention-paired.png', 'P034-attention-paired.svg'):
        choose(direct, publication / name, name)
    for name in ('compact.json', 'results.json', 'manifest.json', 'source-checks-before-training.json', 'source-audit.json'):
        choose(evidence, work / 'e900' / name, 'work/sle-p034/e900/' + name)
    for split in SPLITS:
        for seed in SEEDS:
            prefix = f'work/sle-p034/e900/{split}-seed{seed}/'
            for name in ('lessons.json', 'result.json', 'replay-checks.json', 'curve.json',
                         'initial-truth-table.json', 'final-truth-table.json', 'initial-state.npz', 'final-state.npz'):
                choose(evidence, root / prefix / name, prefix + name)
    for name in ('compact.json', 'results.json', 'manifest.json', 'preflight.json'):
        choose(evidence, work / 'b1' / name, 'work/sle-p034/b1/' + name)
    for group in GROUPS:
        for seed in SEEDS:
            prefix = f'work/sle-p034/b1/{group}-seed{seed}/'
            for name in ('result.json', 'curve.json', 'final-failures.json'):
                choose(evidence, root / prefix / name, prefix + name)
            for at in (0, 1000, 1500, 3000):
                for name in (f'state-{at}.npz', f'truth-table-{at}.json'):
                    choose(evidence, root / prefix / name, prefix + name)
    choose(evidence, work / 'baseline/compact.json', 'work/sle-p034/baseline/compact.json')
    for group in GROUPS:
        for seed in SEEDS:
            name = f'lessons-{group}-{seed}.json'
            choose(evidence, work / 'baseline' / name, 'work/sle-p034/baseline/' + name)
    choose(evidence, work / 'attention-engineering/checks.json', 'work/sle-p034/attention-engineering/checks.json')
    choose(evidence, work / 'portable-check/checks.json', 'work/sle-p034/portable-check/checks.json')
    for name in ('public_candidate.json', 'candidate_assessment.json', 'independent_code_checks.json', 'design_checks.json', 'final_review.json'):
        choose(evidence, work / 'nvidia-review' / name, 'work/sle-p034/nvidia-review/' + name)
    # The public supplement includes actual archived traces, never regenerated
    # predictions. PR7 contains all historical checkpoint/result prerequisites.
    prior = root / 'work/sle-p033'
    choose(supplement, prior / 'publication-v2/expected-git-blobs.json', 'work/sle-p033/publication-v2/expected-git-blobs.json')
    inventory_entries = []
    for path in (prior / 'publication-v2').glob('entry-*.json'):
        value = read(path)
        if value['path'].endswith('/local-artifact-hashes.json'):
            inventory_entries.append(path)
    assert len(inventory_entries) == 1
    choose(supplement, inventory_entries[0], 'work/sle-p033/publication-v2/entry-0.json')
    for split in SPLITS:
        for seed in SEEDS:
            name = f'work/sle-p033/trial-20261112/coverage/{split}-seed{seed}/neg70/trace.json'
            choose(supplement, root / name, name)
    for group in GROUPS:
        for seed in SEEDS:
            prefix = f'work/sle-p033/trial-20261112/timing/{group}-seed{seed}-T1/'
            choose(supplement, root / prefix / 'trace.json', prefix + 'trace.json')
    return {'direct': direct, 'evidence': evidence, 'input-supplement': supplement}


def metadata(entry):
    return {key: value for key, value in entry.items() if key != 'data'}


def archive_bytes(entries):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in sorted(entries, key=lambda e: e['name']):
            valid_name(entry['name'])
            info = zipfile.ZipInfo(entry['name'], date_time=(2026, 11, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, entry['data'], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    result = buffer.getvalue()
    with zipfile.ZipFile(BytesIO(result)) as archive:
        assert archive.namelist() == sorted(entry['name'] for entry in entries)
        assert archive.testzip() is None
        for entry in entries:
            actual = archive.read(entry['name'])
            assert actual == entry['data'], entry['name']
            assert sha_bytes(actual) == entry['sha256'], entry['name']
            if entry['name'].endswith('.npz'):
                validate_npz(actual, entry['name'])
    return result


def archive_parts(entries):
    batches, current, size = [], [], 200
    for entry in sorted(entries, key=lambda e: e['name']):
        estimate = len(zlib.compress(entry['data'], 9)) + 2 * len(entry['name'].encode('utf-8')) + 160
        if current and size + estimate > MAX_ZIP_BYTES - 4096:
            batches.append(current)
            current, size = [], 200
        current.append(entry)
        size += estimate
    if current:
        batches.append(current)
    result = []
    for batch in batches:
        data = archive_bytes(batch)
        if len(data) > MAX_ZIP_BYTES:
            assert len(batch) > 1, 'One whitelist artifact exceeds the public ZIP size cap'
            half = len(batch) // 2
            result.extend(archive_parts(batch[:half]))
            result.extend(archive_parts(batch[half:]))
        else:
            result.append((data, batch))
    return result


def guard_sources(root):
    work = root / 'work/sle-p034'
    e900 = read(work / 'e900/compact.json')
    b1 = read(work / 'b1/compact.json')
    audit = read(work / 'e900/source-audit.json')
    assert e900['status'] == b1['status'] == 'passed'
    assert audit['all_equal'] and audit['before'] == audit['after']
    for name, digest in audit['before'].items():
        assert sha(root / name) == digest, ('immutable E900 input/source changed', name)
    b1_manifest = read(work / 'b1/manifest.json')
    for name, digest in b1_manifest['source_sha256'].items():
        assert sha(root / 'outputs/sle-p034' / name) == digest, ('frozen B1 source changed', name)
    # Validate every input supplement byte against the public PR7 inventory.
    inventory = None
    for path in (root / 'work/sle-p033/publication-v2').glob('entry-*.json'):
        value = read(path)
        if value['path'].endswith('/local-artifact-hashes.json'):
            inventory = json.loads(value['content'])
            raw = value['content'].encode('utf-8')
            expected = read(root / 'work/sle-p033/publication-v2/expected-git-blobs.json')
            assert blob(raw) == expected['experiments/spiral_neural/20261112_p033/local-artifact-hashes.json']
    assert inventory is not None
    for split in SPLITS:
        for seed in SEEDS:
            rel = f'coverage/{split}-seed{seed}/neg70/trace.json'
            assert sha(root / 'work/sle-p033/trial-20261112' / rel) == inventory[rel]['sha256']
    for group in GROUPS:
        for seed in SEEDS:
            rel = f'timing/{group}-seed{seed}-T1/trace.json'
            assert sha(root / 'work/sle-p033/trial-20261112' / rel) == inventory[rel]['sha256']


def local_inventory(root, selected_sources):
    result = {}
    for folder in ('e900', 'b1'):
        for path in sorted((root / 'work/sle-p034' / folder).rglob('*')):
            if not path.is_file():
                continue
            name = path.relative_to(root).as_posix()
            result[name] = {'bytes': path.stat().st_size, 'sha256': sha(path),
                            'published': name in selected_sources,
                            'policy': 'whitelisted public evidence' if name in selected_sources else 'local-only complete trace/checkpoint; retained, not uploaded'}
    return result


def finalize(root, publication, selected):
    guard_sources(root)
    entries = {kind: [payload(path, name, root) for path, name in pairs] for kind, pairs in selected.items()}
    # Guard original source bytes again after every public copy and archive pass.
    selected_sources = {e['source'] for group in entries.values() for e in group}
    inventory = local_inventory(root, selected_sources)
    inventory_data = (json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    entries['direct'].append({'name': 'local-artifact-hashes.json', 'source': 'generated from local immutable experiment outputs',
                              'source_sha256': sha_bytes(inventory_data), 'sha256': sha_bytes(inventory_data),
                              'bytes': len(inventory_data), 'git_blob': blob(inventory_data), 'redactions': [], 'data': inventory_data})
    redactions = {e['name']: {'source': e['source'], 'source_sha256': e['source_sha256'],
                            'public_sha256': e['sha256'], 'fields': e['redactions']}
                  for group in entries.values() for e in group if e['redactions']}
    disclosure = {'policy': 'Only private local metadata fields are removed from PUBLIC JSON copies. Scientific numbers, arrays, logits, targets and model source are unchanged. Originals remain local.',
                  'files': redactions}
    disclosure_data = (json.dumps(disclosure, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    entries['direct'].append({'name': 'public-source-redactions.json', 'source': 'generated public-copy disclosure',
                              'source_sha256': sha_bytes(disclosure_data), 'sha256': sha_bytes(disclosure_data),
                              'bytes': len(disclosure_data), 'git_blob': blob(disclosure_data), 'redactions': [], 'data': disclosure_data})
    public = publication / 'public'
    public.mkdir(parents=True, exist_ok=True)
    files = {}
    zipped = {}
    for entry in entries['direct']:
        destination = public / entry['name']
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(entry['data'])
        assert destination.read_bytes() == entry['data']
        files[entry['name']] = metadata(entry)
    for kind in ('evidence', 'input-supplement'):
        parts = archive_parts(entries[kind])
        for i, (data, batch) in enumerate(parts, 1):
            name = kind + ('' if i == 1 else f'-{i:02d}') + '.zip'
            (public / name).write_bytes(data)
            # Convenient local path for the parent; the public copy is identical.
            (publication / name).write_bytes(data)
            assert (public / name).read_bytes() == data
            assert len(data) <= MAX_ZIP_BYTES
            files[name] = {'name': name, 'source': 'strict whitelist archive', 'source_sha256': sha_bytes(data),
                           'sha256': sha_bytes(data), 'bytes': len(data), 'git_blob': blob(data), 'redactions': []}
            zipped[name] = [metadata(e) for e in batch]
    trace_omissions = {name: value for name, value in inventory.items()
                       if not value['published'] and 'trace' in Path(name).name}
    record = {
        'id': 'P034-PUBLICATION-RECORD', 'execution_author': 'Codex',
        'scope': 'New P034 result package; no Git operation, merge or alteration of PR7/PR8 sources.',
        'zip_coverage': {name: {'entries': len(items), 'bytes': files[name]['bytes'],
                               'sha256': files[name]['sha256'], 'git_blob': files[name]['git_blob']}
                         for name, items in zipped.items()},
        'public_file_count_including_record_and_manifest': len(files) + 2,
        'text_newline_policy': 'Source bytes UTF-8 decoded directly for tree entries; CRLF preserved, no newline normalization.',
        'public_metadata_redactions': redactions,
        'private_original_metadata_policy': 'Unmodified originals remain local; only the listed public-copy fields are removed.',
        'root_source_pins': {
            'Pro_plan_PR8_head': 'adca797c1afa98ed754ff616f73b691ab2925002',
            'P033_PR7_head': 'e217bd0fd6cfe654062c3615ee2aa73a36d1ca71',
            'P033_evidence_zip_git_blob': '7bf5d28cd3d06a94afa903780694e4ef344671ba',
            'E900_frozen_manifest_sha256': sha(root / 'work/sle-p034/e900/manifest.json'),
            'B1_frozen_manifest_sha256': sha(root / 'work/sle-p034/b1/manifest.json'),
            'integrated_review_sha256': sha(root / 'outputs/sle-p034/integration_review.json'),
        },
        'historical_code_guards': 'Public P033 expected Git blobs, immutable source SHA256, original18 trace inventory SHA256, historical checkpoint/result/read-only truth equality all enforced; source files unchanged.',
        'large_traces_local_only': trace_omissions,
        'large_trace_count': len(trace_omissions),
        'large_trace_bytes': sum(item['bytes'] for item in trace_omissions.values()),
        'complete_local_inventory': 'local-artifact-hashes.json',
        'roundtrip': {'every_ZIP_entry_exact_bytes': True, 'NPZ_numeric_arrays_finite': True,
                      'base64_chunk_characters': CHUNK_CHARACTERS, 'ZIP_size_cap': MAX_ZIP_BYTES},
        'scientific_limits': ['E900 has4500 vs historicalNeg70 15000 updates; unequal MAC.',
                              'B1 parameters2596 vs B0 2595; equal updates but15.333333x matrixMAC.',
                              'B0/Neg70/E3000 training is historical, not retrained here.',
                              'B1 strong_success=false; engineering/replay PASS is not scientific success.'],
    }
    dump(public / 'PUBLICATION_RECORD.json', record)
    record_data = (public / 'PUBLICATION_RECORD.json').read_bytes()
    files['PUBLICATION_RECORD.json'] = {'sha256': sha_bytes(record_data), 'bytes': len(record_data), 'git_blob': blob(record_data)}
    manifest = {
        'schema': 'P034-public-bundle-v1', 'repository_path': REPOSITORY_PREFIX.rstrip('/'),
        'files': {name: {key: value[key] for key in ('sha256', 'bytes', 'git_blob')} for name, value in sorted(files.items())},
        'zip_entries': zipped,
        'code_and_metadata_sources': {e['name']: metadata(e) for e in entries['direct']},
        'source_plan': {'author': 'ChatGPT Pro', 'PR': 8, 'head': 'adca797c1afa98ed754ff616f73b691ab2925002', 'status_at_design': 'proposal, not trained'},
        'historical_P033': {'head': 'e217bd0fd6cfe654062c3615ee2aa73a36d1ca71',
                            'evidence_zip_git_blob': '7bf5d28cd3d06a94afa903780694e4ef344671ba',
                            'policy': 'Original PR7 archive is an external pinned prerequisite; source and original artifacts are unchanged.'},
        'strict_whitelist': True, 'max_zip_bytes': MAX_ZIP_BYTES,
        'every_zip_entry_byte_roundtrip': True, 'every_NPZ_numeric_array_finite': True,
        'full_target_hash_traces': 'Local only; each source SHA and byte size appears in local-artifact-hashes.json.',
        'private_fields_removed_from_public_copies': redactions,
        'no_raw_API_quota_or_home_or_fontcache_files': True,
        'manifest_self_hash_policy': 'files excludes package-manifest.json itself; Git tree records its content hash.',
    }
    dump(public / 'package-manifest.json', manifest)
    manifest_data = (public / 'package-manifest.json').read_bytes()
    files['package-manifest.json'] = {'sha256': sha_bytes(manifest_data), 'bytes': len(manifest_data), 'git_blob': blob(manifest_data)}
    dump(publication / 'package-manifest.json', manifest)
    # Structured API text entries preserve CRLF: read bytes then UTF-8 decode.
    tree_entries = []
    binary_entries = []
    expected_blobs = {}
    chunks = publication / 'base64-chunks'
    for name in sorted(files):
        data = (public / name).read_bytes()
        assert sha_bytes(data) == files[name]['sha256'] and blob(data) == files[name]['git_blob']
        target = REPOSITORY_PREFIX + name
        expected_blobs[target] = blob(data)
        if Path(name).suffix.lower() in ('.py', '.json', '.md', '.svg', '.txt'):
            content = data.decode('utf-8')
            assert content.encode('utf-8') == data
            entry = {'path': target, 'mode': '100644', 'type': 'blob', 'content': content}
            tree_entries.append(entry)
        else:
            encoded = base64.b64encode(data).decode('ascii')
            chunk_dir = chunks / name.replace('/', '__')
            chunk_dir.mkdir(parents=True, exist_ok=True)
            names = []
            for i in range(0, len(encoded), CHUNK_CHARACTERS):
                part = chunk_dir / f'{i // CHUNK_CHARACTERS:05d}.txt'
                part.write_text(encoded[i:i+CHUNK_CHARACTERS], encoding='ascii')
                names.append(part.relative_to(publication).as_posix())
            reconstructed = base64.b64decode(''.join((publication / p).read_text(encoding='ascii') for p in names), validate=True)
            assert reconstructed == data
            binary_entries.append({'path': target, 'mode': '100644', 'type': 'blob',
                                   'source': 'public/' + name, 'sha256': sha_bytes(data), 'git_blob': blob(data),
                                   'bytes': len(data), 'base64_characters': len(encoded), 'chunk_characters': CHUNK_CHARACTERS,
                                   'chunks': names, 'base64_roundtrip_equal': True})
    dump(publication / 'text-tree-entries.json', tree_entries)
    for i, entry in enumerate(tree_entries):
        dump(publication / f'text-entry-{i:03d}.json', entry)
    dump(publication / 'binary-entries.json', binary_entries)
    dump(publication / 'expected-git-blobs.json', expected_blobs)
    guard_sources(root)
    result = {'status': 'passed', 'finalized': True,
              'text_tree_entries': len(tree_entries), 'binary_entries': len(binary_entries),
              'published_files': len(files), 'whitelisted_evidence_entries': sum(len(v) for v in zipped.values()),
              'zip_files': {name: files[name] for name in zipped},
              'redacted_public_JSON_files': len(redactions),
              'local_only_artifacts': sum(not row['published'] for row in inventory.values()),
              'every_entry_roundtrip_equal': True, 'NPZ_finite': True, 'source_guards_passed_after_export': True,
              'package_manifest': str(publication / 'package-manifest.json')}
    dump(publication / 'export-checks.json', result)
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--plan', action='store_true', help='Only list the whitelist and missing prerequisites; never archives')
    parser.add_argument('--finalize', action='store_true', help='Run only after parent final document/review approval')
    args = parser.parse_args()
    assert not (args.plan and args.finalize)
    root = args.root.resolve()
    publication = args.out.resolve() if args.out else root / 'work/sle-p034/publication'
    publication.mkdir(parents=True, exist_ok=True)
    selected = selected_files(root, publication)
    missing = [str(path.relative_to(root)) for pairs in selected.values() for path, _ in pairs if not path.is_file()]
    if not args.finalize:
        plan = {'status': 'ready' if not missing else 'waiting_for_final_files', 'finalized': False,
                'policy': 'Strict explicit whitelist; no archives until --finalize after parent signal.',
                'missing': missing,
                'selection': {kind: [{'source': path.relative_to(root).as_posix(), 'name': name,
                                     'bytes': path.stat().st_size if path.is_file() else None}
                                    for path, name in pairs] for kind, pairs in selected.items()}}
        dump(publication / 'export-plan.json', plan)
        print(json.dumps({'status': plan['status'], 'finalized': False, 'missing': missing,
                          'selected_entries': {kind: len(pairs) for kind, pairs in selected.items()},
                          'plan': str(publication / 'export-plan.json')}, ensure_ascii=False))
        return
    assert not missing, f'Required public files missing: {missing}'
    integration = read(root / 'outputs/sle-p034/integration_review.json')
    assert integration['status'] == 'final_protocol_and_artifact_review_pass'
    assert integration['actionable_implementation_findings'] == []
    for name, digest in integration['final_source_sha256'].items():
        assert sha(root / 'outputs/sle-p034' / name) == digest, ('reviewed source changed', name)
    finalize(root, publication, selected)


if __name__ == '__main__':
    main()
