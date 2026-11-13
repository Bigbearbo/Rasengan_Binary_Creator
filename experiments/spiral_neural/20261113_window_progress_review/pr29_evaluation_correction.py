"""Read-only correction of PR29's mislabeled training-suffix evaluation.

The four published inference-only checkpoints are evaluated with NumPy. No torch,
training driver, optimizer, checkpoint export, or original file is executed/written.
First reproduce each of the 480 distinct archived (model, raw Q) outputs once;
then evaluate the 384 genuinely new train suffix interventions. Exactness refers
to generated token strings, not bitwise equality of PyTorch and NumPy logits.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import platform
from pathlib import Path

import numpy as np


REFERENCE_COMMIT = 'dcabc3a65a4b9e7a50ab83ff8266b2c233d15000'
REFERENCE_DIR = 'experiments/spiral_neural/20261113_scheduled_suffix_exposure'
PINNED_SHA256 = {
    'experiment.py': 'a21edd9453215edc553206aff364599e650594505bc2a0af5f006c41049c57c8',
    'preregistered_protocol.json': '27cd6874fa08054a58e7cd9d02b2aebee879136eb71d440eaf17a885dec01b2f',
    'results.json': 'f02fc5e951c3fc4f517350508cc562f2d9ab3b70b7c88a4bebd5d905381a6aae',
    'checkpoint_export_results.json': 'b72041867c3e3d956bcfbf3e63b5317b9757b017d6115cf0af1ea26bf4bf2798',
}
TENSOR_ORDER = ('0.weight', '0.bias', '2.weight', '2.bias')
TENSOR_SHAPES = ((64, 160), (64,), (3, 64), (3,))
SPLITS = ('train', 'val', 'test')
SUFFIXES = ('seen', 'changed_low', 'unseen_high')
L, H, CAP = 80, 64, 32


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_head_without_git_command(root: Path) -> str:
    """Read repository/worktree metadata; no Git command or mutation is needed."""
    marker = root / '.git'
    if marker.is_dir():
        gitdir = marker
    else:
        text = marker.read_text().strip()
        if not text.startswith('gitdir: '):
            raise ValueError('Not a recognized worktree .git marker')
        gitdir = (root / text[len('gitdir: '):]).resolve()
    head = (gitdir / 'HEAD').read_text().strip()
    if not head.startswith('ref: '):
        return head
    ref = head[len('ref: '):]
    roots = [gitdir]
    if (gitdir / 'commondir').exists():
        roots.append((gitdir / (gitdir / 'commondir').read_text().strip()).resolve())
    for directory in roots:
        direct = directory / ref
        if direct.exists():
            return direct.read_text().strip()
        packed = directory / 'packed-refs'
        if packed.exists():
            for line in packed.read_text().splitlines():
                if line and not line.startswith(('#', '^')):
                    commit, name = line.split(' ', 1)
                    if name == ref:
                        return commit
    raise ValueError('HEAD ref cannot be resolved')


def word(value: int) -> str:
    assert 0 <= value < 30
    return f'{value:05b}0'


def question(r: int, a: int, b: int, c: int, d: int) -> str:
    assert r in (1, 2)
    q = '01' + '010' + f'{r:03b}0' + ''.join(map(word, (a, b, c, d))) + '111100'
    assert len(q) == 39
    return q


def expected_answer(r: int, a: int, b: int) -> str:
    return word(a) + (word(b) if r == 2 else '') + 'S'


def split_name(a: int, b: int) -> str:
    return 'val' if (a+b) % 6 == 0 else 'test' if (a+b) % 6 == 1 else 'train'


def evaluation_suffix(a: int, b: int, regime: str) -> tuple[int, int]:
    """Use the evaluation transformation even when the answer pair was trained."""
    c0, d0 = (7*a+3*b) % 15, (5*a+11*b) % 15
    if regime == 'seen':
        return c0, d0
    if regime == 'changed_low':
        result = (c0+8) % 15, (d0+9) % 15
    elif regime == 'unseen_high':
        result = 15+c0, 15+d0
        assert min(result) >= 15
    else:
        raise ValueError(regime)
    assert result != (c0, d0)
    return result


class FrozenNumpyModel:
    def __init__(self, checkpoint: dict, archived: dict):
        assert checkpoint['schema'] == 'AE1-SUFFIX-FINAL-WEIGHTS-v1'
        assert checkpoint['purpose'] == 'inference_only_no_adam_state'
        assert checkpoint['source_sha256'] == PINNED_SHA256['experiment.py']
        assert checkpoint['protocol_sha256'] == PINNED_SHA256['preregistered_protocol.json']
        assert checkpoint['updates'] == archived['optimizer_steps'] == 1600
        assert checkpoint['initial_weights_sha256'] == archived['initial_sha256']
        assert set(checkpoint['tensors']) == set(TENSOR_ORDER)
        tensor_hash = hashlib.sha256()
        arrays = []
        for key, shape in zip(TENSOR_ORDER, TENSOR_SHAPES):
            tensor = checkpoint['tensors'][key]
            assert tensor['dtype'] == 'float32' and tuple(tensor['shape']) == shape
            raw = base64.b64decode(tensor['little_endian_base64'], validate=True)
            array = np.frombuffer(raw, dtype='<f4').reshape(shape).copy()
            assert np.isfinite(array).all()
            array.flags.writeable = False
            tensor_hash.update(key.encode())
            tensor_hash.update(raw)
            arrays.append(array)
        assert sum(x.size for x in arrays) == 10499
        assert tensor_hash.hexdigest() == checkpoint['final_weights_sha256'] == archived['final_weights_sha256']
        self.w1, self.b1, self.w2, self.b2 = arrays
        self.forward_count = 0
        self.minimum_argmax_margin = float('inf')

    def generate(self, q: str) -> tuple[str, str]:
        output = ''
        for _ in range(CAP):
            context = q + output
            if len(context) > L:
                return output, 'overflow'
            assert set(context) <= {'0', '1'}
            x = np.zeros(2*L, dtype=np.float32)
            indices = np.fromiter((2*i+int(ch) for i, ch in enumerate(context)), dtype=np.int64)
            x[indices] = np.float32(1)
            hidden = np.tanh(self.w1 @ x + self.b1)
            logits = self.w2 @ hidden + self.b2
            ordered = np.sort(logits)
            self.minimum_argmax_margin = min(self.minimum_argmax_margin, float(ordered[-1]-ordered[-2]))
            self.forward_count += 1
            token = '01S'[int(np.argmax(logits))]
            output += token
            if token == 'S':
                return output, 'stop'
        return output, 'cap'


def score_rows(rows: list[dict]) -> dict:
    return {
        'n': len(rows),
        'exact': sum(x['exact'] for x in rows),
        'stop_position': sum(x['stop_position_correct'] for x in rows),
        'bits_correct': sum(x['bits_correct'] for x in rows),
        'bits_total': sum(len(x['expected'])-1 for x in rows),
    }


def run(reference_root: Path) -> dict:
    assert read_head_without_git_command(reference_root) == REFERENCE_COMMIT
    directory = reference_root / REFERENCE_DIR
    watched = {}
    for name, expected_hash in PINNED_SHA256.items():
        actual = sha256((directory / name).read_bytes())
        assert actual == expected_hash, (name, actual, expected_hash)
        watched[name] = actual
    archive = json.loads((directory / 'results.json').read_text())
    exports = json.loads((directory / 'checkpoint_export_results.json').read_text())
    assert archive['source_sha256'] == PINNED_SHA256['experiment.py']
    assert archive['protocol_sha256'] == PINNED_SHA256['preregistered_protocol.json']
    models = {}
    cache = {}
    archived_predictions = {}
    archive_rows = 0
    archive_replay_mismatches = []
    checkpoint_proofs = []
    for archived in archive['per_model']:
        seed, mode = archived['seed'], archived['mode']
        key = seed, mode
        record = next(x for x in exports['records'] if (x['seed'], x['mode']) == key)
        relative_path = 'checkpoints/' + record['checkpoint']
        raw = (directory / relative_path).read_bytes()
        assert len(raw) == record['size_bytes'] and sha256(raw) == record['sha256']
        watched[relative_path] = sha256(raw)
        checkpoint = json.loads(raw)
        assert (checkpoint['seed'], checkpoint['mode']) == key
        model = FrozenNumpyModel(checkpoint, archived)
        models[key] = model
        checkpoint_proofs.append({
            'seed': seed, 'mode': mode, 'path': relative_path,
            'file_sha256': watched[relative_path],
            'final_weights_sha256': checkpoint['final_weights_sha256'],
            'stored_prior_optimizer_steps': checkpoint['updates'],
            'new_optimizer_steps': 0,
        })
        for split in SPLITS:
            for regime in SUFFIXES:
                for r in (1, 2):
                    for a, b, c, d, stored_r, observed in archived['evaluation'][split][regime][str(r)]['predictions']:
                        assert stored_r == r and split_name(a, b) == split
                        q = question(r, a, b, c, d)
                        case_key = seed, mode, q
                        archive_rows += 1
                        if case_key in archived_predictions:
                            assert archived_predictions[case_key] == observed
                        else:
                            archived_predictions[case_key] = observed
                            generated, reason = model.generate(q)
                            cache[case_key] = generated, reason
                            if generated != observed:
                                archive_replay_mismatches.append({
                                    'seed': seed, 'mode': mode, 'Q': q,
                                    'archived': observed, 'numpy': generated, 'reason': reason,
                                })
    assert len(models) == 4 and archive_rows == 864 and len(archived_predictions) == 480
    replay_forwards = sum(x.forward_count for x in models.values())
    if archive_replay_mismatches:
        return {
            'status': 'ARCHIVE_REPLAY_MISMATCH', 'reference_commit': REFERENCE_COMMIT,
            'scope': 'No corrected evaluation proceeded after NumPy output disagreement.',
            'distinct_archive_queries': 480, 'mismatches': archive_replay_mismatches,
            'new_optimizer_steps': 0, 'forward_count': replay_forwards,
        }

    corrected = []
    for (seed, mode), model in models.items():
        for split in SPLITS:
            for regime in SUFFIXES:
                for a in range(6):
                    for b in range(6):
                        if split_name(a, b) != split:
                            continue
                        c, d = evaluation_suffix(a, b, regime)
                        for r in (1, 2):
                            q = question(r, a, b, c, d)
                            case_key = seed, mode, q
                            reused = case_key in archived_predictions
                            if case_key not in cache:
                                cache[case_key] = model.generate(q)
                            produced, reason = cache[case_key]
                            expected = expected_answer(r, a, b)
                            corrected.append({
                                'seed': seed, 'mode': mode, 'split': split, 'suffix_regime': regime,
                                'a': a, 'b': b, 'c': c, 'd': d, 'r': r,
                                'Q': q, 'expected': expected, 'actual': produced, 'stop_reason': reason,
                                'exact': produced == expected,
                                'stop_position_correct': produced.endswith('S') and len(produced) == len(expected),
                                'bits_correct': sum(i < len(produced) and produced[i] == bit for i, bit in enumerate(expected[:-1])),
                                'reused_unique_archive_inference': reused,
                            })
    assert len(corrected) == len({(x['seed'], x['mode'], x['Q']) for x in corrected}) == 864
    assert len(cache) == 864
    assert sum(not x['reused_unique_archive_inference'] for x in corrected) == 384
    assert all(x['c'] >= 15 and x['d'] >= 15 for x in corrected if x['suffix_regime'] == 'unseen_high')
    summaries = []
    for seed, mode in models:
        own = [x for x in corrected if (x['seed'], x['mode']) == (seed, mode)]
        summaries.append({
            'seed': seed, 'mode': mode,
            'evaluation': {
                split: {
                    regime: {str(r): score_rows([x for x in own if x['split'] == split and x['suffix_regime'] == regime and x['r'] == r]) for r in (1, 2)}
                    for regime in SUFFIXES
                }
                for split in SPLITS
            },
        })
    preserved = {}
    for mode in ('fixed', 'varied'):
        old = sum(x['evaluation']['test']['unseen_high']['2']['exact'] for x in archive['per_model'] if x['mode'] == mode)
        new = sum(x['exact'] for x in corrected if x['mode'] == mode and x['split'] == 'test' and x['suffix_regime'] == 'unseen_high' and x['r'] == 2)
        assert old == new == (7 if mode == 'fixed' else 9)
        preserved[mode] = {'original_exact': old, 'corrected_exact': new, 'n': 12, 'unchanged': True}
    after = {name: sha256((directory / name).read_bytes()) for name in watched}
    assert after == watched and read_head_without_git_command(reference_root) == REFERENCE_COMMIT
    total_forwards = sum(x.forward_count for x in models.values())
    return {
        'status': 'PASS', 'owner': '視窗GPT / independent NumPy read-only correction',
        'reference_commit': REFERENCE_COMMIT, 'reference_directory': REFERENCE_DIR,
        'reference_files_sha256': watched, 'reference_files_unchanged': True,
        'correction_script_sha256': sha256(Path(__file__).read_bytes()),
        'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'inference': 'independent float32 NumPy, no torch import'},
        'finding': 'Published rows(which=train) ignores suffix_mode; the three archived train regimes repeat the original suffix.',
        'scope': 'Only generated 0/1/S strings are compared exactly. PyTorch/NumPy logits are not claimed bit-identical. No training, optimizer, checkpoint export, or source mutation.',
        'archive_replay': {
            'archived_labeled_rows': archive_rows, 'distinct_model_question_pairs': 480,
            'exact_output_matches': 480, 'duplicate_labeled_rows': 384,
            'forward_count': replay_forwards, 'mismatches': [],
        },
        'corrected_evaluation': {
            'distinct_model_question_pairs': 864, 'reused_archive_inferences': 480,
            'new_train_suffix_queries': 384, 'new_train_suffix_forward_count': total_forwards - replay_forwards,
            'train_queries_per_model': 144, 'train_distinct_queries_per_model': 144,
            'high_suffix_ids_all_at_least_15': True,
        },
        'cost': {
            'new_optimizer_steps': 0, 'new_training_targets': 0,
            'complete_generations': 864, 'forward_count': total_forwards,
            'dense_affine_MAC_per_forward': 10432, 'dense_affine_MAC': total_forwards * 10432,
            'MAC_scope': 'Linear multiplications only; excludes biases, tanh, other operations and I/O.',
        },
        'minimum_argmax_logit_margin': min(x.minimum_argmax_margin for x in models.values()),
        'checkpoint_proofs': checkpoint_proofs, 'original_test_result_preserved': preserved,
        'per_model': summaries, 'corrected_raw_predictions': corrected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('pr29_correction_results.json'))
    args = parser.parse_args()
    result = run(args.reference_root.resolve())
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'reference_commit', 'archive_replay', 'corrected_evaluation', 'original_test_result_preserved', 'cost') if key in result}, ensure_ascii=False))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
