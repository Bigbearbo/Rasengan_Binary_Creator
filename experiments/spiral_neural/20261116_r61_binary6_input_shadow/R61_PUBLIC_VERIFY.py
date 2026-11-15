"""R61 artifact receipt verifier (stdlib, no neural computation).
Usage: python R61_PUBLIC_VERIFY.py /path/to/r56_workspace
Does not substitute for running the included neural/NumPy replay script.
"""
import sys, json, hashlib
from pathlib import Path

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
read=lambda p: json.loads((root/p).read_text(encoding='utf-8'))
lines=lambda p: [json.loads(s) for s in (root/p).read_text(encoding='utf-8').splitlines()]
sha=lambda p: hashlib.sha256((root/p).read_bytes()).hexdigest()
p=read('r61_prereg.json'); r=read('r61_outputs/results.json')
assert sha('r61_binary6_input_isomorphism.py')==p['runner_sha256']==r['runner_sha256']
assert sha('r61_prereg.json')==r['prereg_sha256']
assert sha('r61_manifest.jsonl')==p['manifest_sha256']
for src,expected in p['sources_sha256'].items():
    assert sha(src)==expected, ('source SHA',src)
manifest=lines('r61_manifest.jsonl')
assert len(manifest)==272
for item in manifest:
    a=item['Q_sle']; b=item['Q_binary6']; vals=[item[k] for k in 'abcd']
    assert len(a)==len(b)==39 and a[:9]==b[:9] and a[33:]==b[33:]
    assert 0<=min(vals)<=max(vals)<=29 and item['r'] in (1,2)
    assert a[9:33]==''.join(f'{v:05b}0' for v in vals)
    assert b[9:33]==''.join(f'{v:06b}' for v in vals)
raw=lines('r61_outputs/raw_results.jsonl')
assert len(raw)==816 and sha('r61_outputs/raw_results.jsonl')==r['actual_raw_sha256']
manifest_q={x['Q_sle']:x for x in manifest}
assert len(manifest_q)==272
seen=set(); equal=0; exact_binary=0; exact_sle=0
for x in raw:
    item=manifest_q[x['Q_sle']]; k=(x['seed'],x['Q_sle'])
    assert x['seed'] in p['seeds'] and k not in seen; seen.add(k)
    assert x['Q_binary6']==item['Q_binary6'] and x['expected']==item['expected_sle_output']
    assert x['same_output']==(x['actual_binary6']==x['actual_R52_sle'])
    assert x['exact_binary6']==(x['actual_binary6']==x['expected'])
    assert x['exact_R52']==(x['actual_R52_sle']==x['expected'])
    equal+=x['same_output'];exact_binary+=x['exact_binary6'];exact_sle+=x['exact_R52']
assert len(seen)==816 and equal==r['same_answers']
assert exact_binary==r['full_binary6'] and exact_sle==r['full_SLE_R52']
assert r['independent_numpy_replay_count']==816 and r['optimizer_updates']==1500
assert r['joint_gate']==('PASS' if all(r['gates'].values()) else 'FAIL')
assert r['max_gate_abs']<0.01 and r['max_logits_abs']<0.005
assert equal>=810
for seed in p['seeds']:
    orig=read(f'r52_outputs/gate_{seed}.json')['gate_logits']
    new=read(f'r61_outputs/gate_{seed}.json')['gate_logits']
    assert max(abs(a-b) for q,z in zip(orig,new) for a,b in zip(q,z))<.01
print(f'R61 RECEIPTS PASS: {len(manifest)} paired Q, 816 answers, {equal}/816 same, {exact_binary} exact, six gates {r["joint_gate"]}')
