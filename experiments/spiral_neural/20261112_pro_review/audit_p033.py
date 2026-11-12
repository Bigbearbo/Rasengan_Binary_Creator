"""Independently reaggregate published P033 predictions/results; no model runs.

Usage: python -B audit_p033.py --p033-dir PATH --out NEW_DIRECTORY
Requires the exact files from PR7 commit e217bd0fd6cfe654062c3615ee2aa73a36d1ca71.
Uses only Python's standard library and never extracts or loads checkpoints.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

COMMIT = 'e217bd0fd6cfe654062c3615ee2aa73a36d1ca71'
REPORT = 'P033-覆蓋與從頭混教實測結果-2026-11-12.md'
EXPECTED_SHA256 = {
    'evidence.zip': 'bab2291add697b4d57593c7410633d976c4eb926132bf349c75e6581b46c7564',
    'summary-table.json': '2f3ca4f63c78d5470356c0a23b7ed35bbd7658d6b8c8f4db3ed6e83d9c850d03',
    REPORT: '7abf06cd6baa2bc03f898a1ce496dd137e5d71f5df04d801bb735b0899535a5c',
    'p033.py': '6e7445b8824b781f6e00356bfbcb6678c099299157b6baddb216d733e5379b48',
    'echo_only_followup.py': '79a8d1b443759d9929e6afd99316204786a14f14a7d3eca1965d8f34fc293f8d',
}
SPLITS = {
    'S0': {'train': [0, 1, 2, 3, 5, 7], 'val': [4], 'test': [6]},
    'C0': {'train': [0, 1, 2, 3, 4, 7], 'val': [5], 'test': [6]},
    'S1': {'train': [0, 1, 2, 3, 4, 6], 'val': [5], 'test': [7]},
    'C1': {'train': [0, 1, 2, 3, 5, 6], 'val': [4], 'test': [7]},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--p033-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a fresh output directory')
    raw = {name: (args.p033_dir / name).read_bytes() for name in EXPECTED_SHA256}
    assert {name: sha(data) for name, data in raw.items()} == EXPECTED_SHA256, 'Inputs differ from reviewed PR7 commit'
    archive = zipfile.ZipFile(io.BytesIO(raw['evidence.zip']))
    assert len(archive.namelist()) == len(set(archive.namelist()))
    members_read = {}

    def read(name):
        data = archive.read(name)
        members_read[name] = sha(data)
        return json.loads(data)

    published = json.loads(raw['summary-table.json'])
    report = raw[REPORT].decode('utf-8')
    manifest = read('evidence/manifest.json')
    assert manifest['splits'] == SPLITS
    seeds = [101, 202, 303]
    timing_results = read('evidence/timing/results.json')
    coverage_results = read('evidence/coverage/results.json')
    echo_results = read('evidence/echo-only-followup-v2/results.json')
    echo_compact = read('evidence/echo-only-followup-v2/compact.json')
    echo_manifest = read('evidence/echo-only-followup-v2/manifest.json')
    assert len(timing_results) == 18 and len(coverage_results) == 12 and len(echo_results) == 12
    assert echo_manifest['budget'] == 3000 and echo_manifest['teacher_target_updates'] == 15000
    regraded_rows = 0

    def score_table(table, split, metrics):
        nonlocal regraded_rows
        assert len(table) == 16
        assert Counter((r['operator'], r['value']) for r in table) == Counter((op, v) for op in ('echo', 'neg') for v in range(8))
        scored = {subset: {op: [0, 0] for op in ('echo', 'neg')} for subset in ('train', 'val', 'test')}
        for row in table:
            op, value = row['operator'], row['value']
            op_number = 0 if op == 'echo' else 1
            expected_q = '01' + format(op_number, '02b') + '0' + format(value, '03b') + '0'
            expected_answer = format(value if op == 'echo' else value ^ 7, '03b') + '0S'
            assert row['Q'] == expected_q and row['target'] == expected_answer
            assert row['n_data'] == 3 and row['n_op'] == 2 and row['END_active'] is False
            exact = row['generated'] == expected_answer and not row['overflow']
            assert exact == row['whole_correct']
            subset = next(k for k, values in SPLITS[split].items() if value in values)
            scored[subset][op][0] += int(exact)
            scored[subset][op][1] += 1
        for subset in scored:
            for op, count in scored[subset].items():
                old = metrics[subset]['by_op'][op]
                assert count == [old['whole'], old['total']]
        regraded_rows += len(table)
        return scored

    detailed = {'timing': [], 'coverage': [], 'echo_only_archived_metrics': []}
    for result in timing_results:
        group, seed, mode = result['group'], result['seed'], result['timing']
        assert result['split'] == {'G0': 'S0', 'G1': 'C1'}[group]
        assert result['presentations'] == 3000 and result['target_updates'] == 15000
        name = f'evidence/timing/{group}-seed{seed}-{mode}/truth-table-3000.json'
        scored = score_table(read(name), result['split'], result['metrics'])
        detailed['timing'].append({'group': group, 'seed': seed, 'timing': mode, 'scores': scored})
    assert {(r['group'], r['seed'], r['timing']) for r in detailed['timing']} == {(g, s, t) for g in ('G0', 'G1') for s in seeds for t in ('T0', 'T1', 'T0B')}
    for result in coverage_results:
        split, seed = result['split'], result['seed']
        name = f'evidence/coverage/{split}-seed{seed}/final-truth-table.json'
        scored = score_table(read(name), split, result['metrics'])
        detailed['coverage'].append({'split': split, 'seed': seed, 'scores': scored,
                                    'Echo_before_test_from_archived_result': result['Echo_before']['by_op']['echo']['whole']})
    assert {(r['split'], r['seed']) for r in detailed['coverage']} == {(s, n) for s in SPLITS for n in seeds}

    def aggregate(rows):
        return {subset: {op: [sum(r['scores'][subset][op][i] for r in rows) for i in (0, 1)] for op in ('echo', 'neg')} for subset in ('train', 'val', 'test')}

    def combined(score, subset):
        return [sum(score[subset][op][i] for op in ('echo', 'neg')) for i in (0, 1)]

    timing = []
    labels = {'G0': 'G0缺口', 'G1': 'G1完整pair'}
    modes = {'T0': 'T0分段', 'T1': 'T1從頭混合', 'T0B': 'T0B後期混合'}
    for group in ('G0', 'G1'):
        for mode in ('T0', 'T1', 'T0B'):
            score = aggregate([r for r in detailed['timing'] if r['group'] == group and r['timing'] == mode])
            old = next(r for r in published['fresh_timing'] if r['group'] == group and r['timing'] == mode)
            for subset in ('train', 'val', 'test'):
                assert combined(score, subset) == old[subset]
                for op, published_key in [('echo', 'Echo'), ('neg', 'Neg')]:
                    assert score[subset][op] == old[f'{subset}_{published_key}']
            counts = [score['train']['echo'], score['train']['neg'], combined(score, 'val'), combined(score, 'test')]
            report_row = '|' + '|'.join([labels[group], modes[mode]] + [f'{a}/{b}' for a, b in counts]) + '|'
            assert report_row in report, f'Report timing row differs: {report_row}'
            timing.append({'group': group, 'timing': mode, 'scores': score,
                           'heldout_combined': [sum(combined(score, s)[i] for s in ('val', 'test')) for i in (0, 1)]})
    coverage = []
    for split in ('S0', 'C0', 'S1', 'C1'):
        group = [r for r in detailed['coverage'] if r['split'] == split]
        score = aggregate(group)
        old = next(r for r in published['coverage'] if r['split'] == split)
        for subset in ('train', 'val', 'test'):
            assert combined(score, subset) == old[subset]
        assert score['test']['echo'] == old['test_Echo']
        assert score['test']['neg'] == old['test_Neg']
        assert [sum(r['Echo_before_test_from_archived_result'] for r in group), 3] == old['Echo_test_before']
        label = split + ('有缺口' if split.startswith('S') else '全pair')
        count_text = [f'{a}/{b}' for a, b in [combined(score, 'train'), combined(score, 'val'), combined(score, 'test')]]
        report_row = '|' + '|'.join([label, ','.join(map(str, SPLITS[split]['train'])), f"{SPLITS[split]['val'][0]}/{SPLITS[split]['test'][0]}"] + count_text) + '|'
        assert report_row in report, f'Report coverage row differs: {report_row}'
        coverage.append({'split': split, 'scores': score})

    for result in echo_results:
        split, seed = result['split'], result['seed']
        per_run = read(f'evidence/echo-only-followup-v2/{split}-seed{seed}-echo-only/result.json')
        assert per_run == result
        assert result['summary']['presentations'] == 3000 and result['summary']['target_updates'] == 15000
        assert result['summary']['exposure'] == {f'0:{v}': 500 for v in SPLITS[split]['train']}
        warm_path = f'evidence/coverage/{split}-seed{seed}/warm-3/final-state.npz'
        warm_bytes = archive.read(warm_path)
        members_read[warm_path] = sha(warm_bytes)
        assert result['initial_checkpoint_sha256'] == sha(warm_bytes)
        scores = {subset: [result['metrics'][subset]['by_op']['echo'][k] for k in ('whole', 'total')] for subset in ('train', 'val', 'test')}
        assert scores['train'][1] == 6 and scores['val'][1] == scores['test'][1] == 1
        detailed['echo_only_archived_metrics'].append({'split': split, 'seed': seed, 'scores': scores})
    assert {(r['split'], r['seed']) for r in detailed['echo_only_archived_metrics']} == {(s, n) for s in SPLITS for n in seeds}
    echo_comparison = []
    for split in ('S0', 'C0', 'S1', 'C1'):
        rows = [r for r in detailed['echo_only_archived_metrics'] if r['split'] == split]
        echo = {subset: [sum(r['scores'][subset][i] for r in rows) for i in (0, 1)] for subset in ('train', 'val', 'test')}
        after = next(r for r in coverage if r['split'] == split)['scores']
        old = next(r for r in echo_compact['comparisons'] if r['split'] == split)
        assert echo['val'] == old['Echo_only_val'] and echo['test'] == old['Echo_only_test']
        assert after['val']['echo'] == old['Echo_after_Neg70_val'] and after['test']['echo'] == old['Echo_after_Neg70_test']
        before = [sum(r['Echo_before_test_from_archived_result'] for r in detailed['coverage'] if r['split'] == split), 3]
        report_row = '|' + '|'.join([split] + [f'{a}/{b}' for a, b in [before, echo['test'], after['test']['echo']]]) + '|'
        assert report_row in report
        echo_comparison.append({'split': split, 'before_test_archived': before, 'echo_only': echo,
                                'after_Neg70_echo': {s: after[s]['echo'] for s in ('train', 'val', 'test')}})
    assert regraded_rows == 480
    headline = {}
    for mode in ('T0', 'T1', 'T0B'):
        groups = [r for r in timing if r['timing'] == mode]
        headline[mode] = {'train_Echo': [sum(r['scores']['train']['echo'][i] for r in groups) for i in (0, 1)],
                          'heldout_both_ops': [sum(r['heldout_combined'][i] for r in groups) for i in (0, 1)]}
    assert headline['T0']['train_Echo'] == [1, 36]
    assert headline['T1'] == {'train_Echo': [36, 36], 'heldout_both_ops': [0, 24]}
    assert headline['T0B'] == {'train_Echo': [36, 36], 'heldout_both_ops': [1, 24]}
    echo_total = [sum(r['echo_only']['test'][i] for r in echo_comparison) for i in (0, 1)]
    mixed_total = [sum(r['after_Neg70_echo']['test'][i] for r in echo_comparison) for i in (0, 1)]
    assert echo_total == [12, 12] and mixed_total == [1, 12]
    for name, data in raw.items():
        assert (args.p033_dir / name).read_bytes() == data, 'Audit modified input'
    summary = {'status': 'PASS', 'producer': 'Pro independent archival audit', 'training_results_origin': 'Codex P033',
               'source_commit': COMMIT, 'source_sha256': EXPECTED_SHA256,
               'training_run': False, 'checkpoint_inference_run': False,
               'regraded_final_prediction_rows': regraded_rows, 'timing_learners': 18, 'coverage_learners': 12,
               'echo_only_result_records_checked': 12, 'headline': headline,
               'echo_only_test': echo_total, 'Neg70_Echo_test': mixed_total,
               'coverage': coverage, 'timing': timing, 'echo_only_comparison': echo_comparison,
               'scope': ['Recomputed exact-match counts from 30 saved final truth tables, independently checking binary Q/target construction.',
                         'Cross-checked per-run results, summary-table.json and the exact numerical Markdown report rows.',
                         'Echo-only archive supplies aggregate test metrics, not per-test generated strings; these were cross-checked with per-run results and compact.json, not independently inferred.',
                         'Echo-only warm checkpoint hashes were verified as bytes; no NPZ was parsed or executed.',
                         'No training/replay, model inference, diagnostic probe rerun, or new blind testing.']}
    args.out.mkdir(parents=True)
    put(args.out / 'summary.json', summary)
    put(args.out / 'per_learner.json', detailed)
    put(args.out / 'manifest.json', {'source_commit': COMMIT, 'source_sha256': EXPECTED_SHA256,
        'archive_members_read_sha256': members_read, 'script_sha256': sha(Path(__file__).read_bytes()),
        'python': sys.version.split()[0], 'outputs_sha256': {n: sha((args.out / n).read_bytes()) for n in ('summary.json', 'per_learner.json')}})
    print(json.dumps({'status': 'PASS', 'regraded_final_prediction_rows': regraded_rows, 'headline': headline,
                      'echo_only_test': echo_total, 'Neg70_Echo_test': mixed_total,
                      'archive_members_read': len(members_read), 'scope': 'archival reaggregation only; no training/inference'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
