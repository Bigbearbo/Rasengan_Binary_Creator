"""Read-only P032 checkpoint review; no retraining or checkpoint copying.

Example:
  python -B review_probe.py --p032-dir /checkout/experiments/spiral_neural/20261112_p032 --out /new/review-output
Or --evidence-zip /path/to/evidence.zip (source modules must be beside it),
or supply both when the archive and its matching source modules are separate.

The exact reviewed P032 source/archive Git blobs are verified before loading.
Output files contain synthetic predictions, probes and hashes only.
"""
import argparse
import collections
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np

SOURCE_COMMIT = 'f003980f719f84b366cda13601091ecf8c256d51'
EXPECTED_BLOBS = {
    'p032.py': 'c973eb190ab8aec2be5711d9aad7066252c9a991',
    'p030_reference.py': '8b41433c6415c6d0927d69ed0aad14ff035fbe40',
    'evidence.zip': 'e30d190fa6c27ca3bd39d1b3a8d42783895a8251',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--p032-dir', type=Path)
    parser.add_argument('--evidence-zip', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.p032_dir is None and args.evidence_zip is None:
        parser.error('Provide --p032-dir or --evidence-zip')
    source_dir = (args.p032_dir or args.evidence_zip.parent).resolve()
    archive_path = (args.evidence_zip or source_dir / 'evidence.zip').resolve()
    if args.out.exists():
        raise FileExistsError('Use a new output directory')
    source_bytes = {name: (source_dir / name).read_bytes() for name in ('p032.py', 'p030_reference.py')}
    source_bytes['evidence.zip'] = archive_path.read_bytes()
    for name, data in source_bytes.items():
        if git_blob(data) != EXPECTED_BLOBS[name]:
            raise ValueError(f'{name} differs from reviewed commit {SOURCE_COMMIT}')
    sys.path.insert(0, str(source_dir))
    ex = importlib.import_module('p032')
    ref = importlib.import_module('p030_reference')
    archive = zipfile.ZipFile(io.BytesIO(source_bytes['evidence.zip']))
    names = archive.namelist()
    assert len(names) == len(set(names)), 'Duplicate archive members'
    prefix = 'evidence/training/'
    runs = sorted({n[len(prefix):].split('/')[0] for n in names if n.startswith(prefix) and n.endswith('/warm-3/final-state.npz')})
    assert len(runs) == 12
    checkpoints = {n: digest(archive.read(n)) for n in names if n.endswith('.npz')}
    assert len(checkpoints) == 36
    p = ref.PHASES[4]
    rows, sensitivity, middle_pairs = [], [], []
    for run in runs:
        split = run.split('-')[0]
        for stage in ('warm-3', 'neg50', 'neg70'):
            path = f'{prefix}{run}/{stage}/final-state.npz'
            model = ex.restore(io.BytesIO(archive.read(path)))
            before = model.state()
            for op in ((0,) if stage == 'warm-3' else (0, 1)):
                for value in range(8):
                    row = ex.truth_row(model, p, op, value)
                    subset = next(k for k, values in ex.SPLITS[split].items() if value in values)
                    target, generated = row['target'], row['generated']
                    first = next((i for i, t in enumerate(target) if i >= len(generated) or t != generated[i]), None)
                    rows.append({'run': run, 'stage': stage, 'subset': subset, 'op': op, 'value': value,
                                 'Q': row['Q'], 'target': target, 'generated': generated, 'first_wrong': first,
                                 'free_correct': row['bit_correct'],
                                 'tf_correct': [x['prediction'] == x['target'] for x in row['teacher_forcing']],
                                 'tf_prediction': ''.join(x['prediction'] for x in row['teacher_forcing'])})
                    q, a = ref.encode(p, op, value), ref.answer(op, p.nd, value)
                    if stage != 'warm-3' and subset == 'val':
                        value2 = ex.SPLITS[split]['test'][0]
                        assert value ^ value2 == 2
                        answer_prefix = a[:1]
                        assert answer_prefix == ref.answer(op, 3, value2)[:1]
                        q2 = ref.encode(p, op, value2)
                        z0 = model.forward(q + answer_prefix)[2]
                        z1 = model.forward(q2 + answer_prefix)[2]
                        l0, l1 = float(z0[1] - z0[0]), float(z1[1] - z1[0])
                        middle_pairs.append({'run': run, 'stage': stage, 'op': op, 'val': value, 'test': value2,
                                             'Q_val': q, 'Q_test': q2, 'prefix': answer_prefix,
                                             'logodds_val': l0, 'logodds_test': l1,
                                             'signed_change': (l1 - l0) * (1 if op == 0 else -1),
                                             'predict_val': '01S'[int(z0.argmax())],
                                             'predict_test': '01S'[int(z1.argmax())],
                                             'logits_val': z0.tolist(), 'logits_test': z1.tolist()})
                    for output in range(3):
                        z = model.forward(q + a[:output])[2]
                        l = float(z[1] - z[0])
                        for input_bit in range(3):
                            value2 = value ^ (1 << (2 - input_bit))
                            q2 = ref.encode(p, op, value2)
                            z2 = model.forward(q2 + a[:output])[2]
                            l2 = float(z2[1] - z2[0])
                            sign = 1 if a[output] == '0' else -1
                            sensitivity.append({'run': run, 'stage': stage, 'subset': subset, 'op': op, 'value': value,
                                                'input_bit': input_bit, 'output_bit': output, 'delta': l2 - l,
                                                'abs_delta': abs(l2 - l),
                                                'own_bit_correct_direction': (l2 - l) * sign > 0 if input_bit == output else None,
                                                'prefix_consistent': input_bit >= output})
            assert ref.equal_state(before, model.state()), 'Probe changed model state'
    matched = 0
    for run in runs:
        for stage in ('neg50', 'neg70'):
            old = json.loads(archive.read(f'{prefix}{run}/{stage}/final-truth-table.json'))
            here = [x for x in rows if x['run'] == run and x['stage'] == stage]
            assert [(x['Q'], x['target'], x['generated']) for x in old] == [(x['Q'], x['target'], x['generated']) for x in here]
            assert [[z['prediction'] for z in x['teacher_forcing']] for x in old] == [list(x['tf_prediction']) for x in here]
            matched += 1
    summary = {'source_commit': SOURCE_COMMIT, 'trained': False, 'checkpoints_unchanged': len(checkpoints),
               'rows': len(rows), 'bit_flip_probes': len(sensitivity), 'published_post_checkpoints_reproduced': matched,
               'information_bit_order': 'MSB first, zero-based; middle bit is b1', 'groups': [],
               'middle_bit_pairs': {'n': len(middle_pairs),
                   'correct_logodds_direction': sum(x['signed_change'] > 0 for x in middle_pairs),
                   'decision_changes': sum(x['predict_val'] != x['predict_test'] for x in middle_pairs),
                   'median_correct_direction_logodds_shift': float(np.median([x['signed_change'] for x in middle_pairs])),
                   'all_prefixes_consistent_for_both_inputs': True},
               'limits': ['Retrospective diagnosis, not a new blind test or causal training intervention.',
                          '48 test evaluations are 24 checkpoints times 2 operators, not 48 independent tasks.',
                          'Off-diagonal sensitivity probes with input_bit < output_bit intentionally use inconsistent prefixes.']}
    for stage in ('warm-3', 'neg50', 'neg70'):
        for subset in ('train', 'val', 'test'):
            for op in (0, 1):
                g = [x for x in rows if (x['stage'], x['subset'], x['op']) == (stage, subset, op)]
                if not g:
                    continue
                summary['groups'].append({'stage': stage, 'subset': subset, 'op': op, 'n': len(g),
                    'exact': sum(x['first_wrong'] is None for x in g),
                    'first_wrong': dict(collections.Counter(str(x['first_wrong']) for x in g)),
                    'free_bit_correct': [sum(x['free_correct'][i] for x in g) for i in range(4)],
                    'tf_bit_correct': [sum(x['tf_correct'][i] for x in g) for i in range(5)]})
    test = [x for x in rows if x['stage'] != 'warm-3' and x['subset'] == 'test']
    val = [x for x in rows if x['stage'] != 'warm-3' and x['subset'] == 'val']
    summary['post_test'] = {'n': len(test), 'first_wrong': dict(collections.Counter(str(x['first_wrong']) for x in test)),
                            'free_middle_bit_correct': sum(x['free_correct'][1] for x in test),
                            'teacher_forced_middle_bit_correct': sum(x['tf_correct'][1] for x in test)}
    summary['post_validation'] = {'n': len(val), 'teacher_forced_middle_bit_correct': sum(x['tf_correct'][1] for x in val)}
    assert summary['post_test'] == {'n': 48, 'first_wrong': {'1': 38, '0': 8, 'None': 2}, 'free_middle_bit_correct': 10, 'teacher_forced_middle_bit_correct': 2}
    assert len(rows) == 480 and len(sensitivity) == 4320 and matched == 24
    assert summary['middle_bit_pairs']['correct_logodds_direction'] == 48
    assert summary['middle_bit_pairs']['decision_changes'] == 2
    assert summary['post_validation']['teacher_forced_middle_bit_correct'] == 48
    # Re-read source/archive bytes: analysis must not modify its inputs.
    for name in ('p032.py', 'p030_reference.py'):
        assert (source_dir / name).read_bytes() == source_bytes[name]
    assert archive_path.read_bytes() == source_bytes['evidence.zip']
    args.out.mkdir(parents=True)
    outputs = {'summary.json': summary, 'truth_rows.json': rows, 'bit_flip_probes.json': sensitivity,
               'second_bit_counterfactual.json': middle_pairs, 'checkpoint_sha256.json': checkpoints}
    for name, obj in outputs.items():
        write_json(args.out / name, obj)
    manifest = {'source_commit': SOURCE_COMMIT, 'source_repository': 'https://github.com/Bigbearbo/Rasengan_Binary_Creator',
                'source_sha256': {n: digest(b) for n, b in source_bytes.items()},
                'source_git_blobs': EXPECTED_BLOBS,
                'probe_script_sha256': digest(Path(__file__).read_bytes()),
                'python': sys.version.split()[0], 'numpy': np.__version__,
                'output_sha256': {n: digest((args.out / n).read_bytes()) for n in outputs}}
    write_json(args.out / 'manifest.json', manifest)
    print(json.dumps({k: summary[k] for k in ('checkpoints_unchanged', 'rows', 'bit_flip_probes', 'published_post_checkpoints_reproduced', 'post_test', 'post_validation', 'middle_bit_pairs')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
