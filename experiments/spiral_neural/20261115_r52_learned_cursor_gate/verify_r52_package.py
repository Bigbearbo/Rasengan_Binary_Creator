"""R52 integrity and scoring audit; neural output replay is a separate command.
Run after extracting entire companion ZIP to a new directory.
"""
import hashlib, json
from pathlib import Path
P = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    base = json.loads((P/'PACKAGE_SHA256.json').read_text())
    add = json.loads((P/'R52_PACKAGE_SHA256.json').read_text())['added_files']
    expected = set(base) | set(add) | {'PACKAGE_SHA256.json', 'R52_PACKAGE_SHA256.json'}
    found = {str(f.relative_to(P)) for f in P.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    assert found == expected, (len(found),len(expected),sorted(found^expected)[:20])
    for rel,h in {**base, **add}.items():
        assert sha(P/rel) == h, ('hash mismatch',rel)
    pre = json.loads((P/'r52_prereg.json').read_text())
    results = json.loads((P/'r52_outputs/results.json').read_text())
    assert sha(P/'r52_learned_cursor_gate.py') == results['runner_SHA256']
    assert sha(P/'r52_prereg.json') == results['prereg_SHA256']
    assert sha(P/'r52_outputs/raw_results.jsonl') == results['raw_SHA256']
    rows = [json.loads(line) for line in (P/'r52_outputs/raw_results.jsonl').read_text().splitlines()]
    assert len(rows)==816 and len({(x['seed'],x['Q']) for x in rows})==816
    assert results['joint_gate']=='PASS' and len(results['gates'])==6 and all(results['gates'].values())
    assert results['total_optimizer_updates']==1500 and results['train_target_presentations']==96000
    assert results['student_parameters_total_each']==10465 and results['trainable_gate_parameters_each']==8
    assert results['stop_logit_invariance_check']==816
    assert sum(r['exact'] for r in rows if r['bucket']=='fresh')==66
    assert sum(r['exact'] for r in rows if r['bucket']=='legacy')==0
    assert sum(r['exact'] for r in rows if r['bucket']=='retention')==220
    for seed,g in results['gate_by_seed'].items():
        assert g[0][0]>max(g[0][1:]) and g[1][1]>max(g[1][0],g[1][2],g[1][3]),seed
    print('R52 clean package PASS',len(base),'inherited checksums;',len(add),'new checksums; 816 results; 6/6 predeclared gates')
    print('To independently recompute NN generations: python r52_learned_cursor_gate.py replay && python r52_learned_cursor_gate.py numpy')
if __name__=='__main__':main()
