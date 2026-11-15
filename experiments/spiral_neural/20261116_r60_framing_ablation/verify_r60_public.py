"""Stdlib-only audit of pre-registered R60 (no model inference)."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]

def verify():
    reg = json.loads((ROOT / 'r60_prereg.json').read_text())
    manifest = rows(ROOT / 'r60_manifest.jsonl')
    actual = rows(ROOT / 'r60_outputs/raw_results.jsonl')
    summary = json.loads((ROOT / 'r60_outputs/results.json').read_text())
    prior = rows(ROOT / 'r59_outputs/raw_results.jsonl')
    assert sha(ROOT / 'r60_framing_ablation.py') == reg['runner_sha256']
    assert sha(ROOT / 'r60_manifest.jsonl') == reg['manifest_sha256']
    for name, expected in reg['source_sha256'].items():
        assert sha(ROOT / name) == expected, name
    assert sha(ROOT / 'r60_outputs/raw_results.jsonl') == summary['raw_sha256']
    assert len(manifest) == 96 and len(prior) == len(actual) == 864
    assert collections.Counter(m['source_split'] for m in manifest) == {'validation': 32, 'test':64}
    lookup = {(p['arm'], p['seed'], p['Q']):p for p in prior}
    assert len(lookup) == 864
    n = collections.Counter()
    for p in actual:
        q, mutant = p['legal_Q'], p['negative_Q']
        assert len(q) == len(mutant) == 39 and q.startswith('01') and mutant == '1'+q[1:]
        assert sum(a!=b for a,b in zip(q,mutant)) == 1
        original = lookup[(p['arm'],p['seed'],q)]
        assert p['baseline_actual'] == original['actual']
        assert p['baseline_cause'] == original['cause']
        assert p['baseline_forwards'] == original['forwards']
        assert (p['negative_actual'],p['negative_cause'],p['negative_forwards']) == (original['actual'],original['cause'],original['forwards'])
        assert p['gold_prefix_logits_max_abs_diff'] == 0.0
        assert p['same_output'] is True
        assert p['negative_protocol_expected'] == 'REJECT_INVALID_FRAMING'
        n[p['arm'],p['seed'],p['source_split']] += 1
    assert len(n)==18 and all(v in (32,64) for v in n.values())
    assert summary['n'] == summary['same_outputs'] == summary['numpy_replay_count'] == 864
    assert summary['joint_gate']=='PASS' and all(summary['gate'].values())
    assert summary['new_training_updates'] == 0
    assert summary['new_forward_calls'] == sum(z['negative_forwards'] for z in actual)
    assert summary['theoretical_forward_MAC']==10920*summary['new_forward_calls']
    print('R60 stdlib audit PASS: 96 matched pairs, 864 frozen neural comparisons, 6/6 diagnostic gates')

if __name__=='__main__':verify()
