"""AE1 R15: frozen-readout change of b context for a25..27; no optimizer.
Usage: python run_r15.py gate | infer
Source is R14 companion, checkpoint F32 stored in source_r14, never changed.
"""
import base64, hashlib, importlib.util, json, os, sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
import torch

P=Path(__file__).resolve().parent
S=P/'source_r14'
H=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
ARMS=('control16','control8','balanced8_16')
SEEDS=(101,202,303)

def load_source():
    spec=importlib.util.spec_from_file_location('ae1_frozen_r14_source',S/'run.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def checkpoints():
    meta=json.loads((S/'control_source_results.json').read_text())
    r13=json.loads((S/'r13_results.json').read_text())
    r14=json.loads((S/'results.json').read_text())
    for seed in SEEDS:
        for arm in ARMS:
            if arm=='control16':
                path=S/'checkpoints_controls'/f'weights_{seed}_tied.json'
                digest=next(z['checkpoint_sha256'] for z in meta['blocks'] if z['seed']==seed and z['arm']=='tied')
            elif arm=='control8':
                path=S/'checkpoints_controls'/f'weights_{seed}_treatment8.json'
                digest=r13['checkpoint_sha256'][str(seed)]
            else:
                path=S/'checkpoints_new'/f'weights_{seed}_balanced.json'
                digest=r14['checkpoint_sha256'][str(seed)]
            assert H(path)==digest,(seed,arm,H(path),digest)
            yield seed,arm,path,digest

def manifest():return [json.loads(l) for l in (P/'manifest.jsonl').read_text().splitlines()]

def gate():
    cfg=json.loads((P/'prereg.json').read_text())
    assert cfg['profile']=='SLE-AE1-n5-v1'
    assert cfg['source_r14_zip_sha256']=='ec431291aef5e913690d4f0303d94cd3b5768ace73d86f98902cdddebb5eb0d3'
    for key,rel in (('source_runner_sha256','source_r14/run.py'),('source_parent_sha256','source_r14/parent_course.json'),('source_r14_raw_sha256','source_r14/raw_results.jsonl'),('manifest_sha256','manifest.jsonl')):
        assert H(P/rel)==cfg[key], (key,H(P/rel),cfg[key])
    assert H(P/'run_r15.py')==cfg['runner_sha256']
    assert len(list(checkpoints()))==9
    rows=manifest(); assert len(rows)==51 and len({r['Q'] for r in rows})==51
    assert Counter(r['split'] for r in rows)==Counter({'validation_new_b':6,'test_new_b':15,'calibration_seen_a_new_b':30})
    source=load_source()
    parent=[tuple(row) for row in json.loads((S/'parent_course.json').read_text())]
    r14=__import__('train_r14_unused') if False else None
    # This is exactly the frozen R14 injection, not a new lesson.
    inject8=[(2,a,(a-8+j)%4,0,1) for a in (8,9,10,11) for j in (0,1)]
    inject16=[(2,a,(a-16+j+2)%4,0,1) for a in (16,17,18,19) for j in (0,1)]
    full_course=parent+inject8+inject16
    assert len(full_course)==136 and len(set(full_course))==112
    trainQs={source.question(*r) for r in full_course}
    parent_b={r[2] for r in parent}
    testB={15,16,17,20,21}; valB={4,5}
    assert (testB|valB).issubset(parent_b)
    assert all(all(v not in (25,26,27) for v in row[1:]) for row in full_course)
    oldQs={json.loads(l)['Q'] for l in (S/'cases.jsonl').read_text().splitlines()}
    for row in rows:
        assert row['r']==2 and row['c']==0 and row['d']==1 and row['a']<=27
        assert row['Q']==source.question(row['r'],row['a'],row['b'],row['c'],row['d'])
        assert row['expected']==source.answer(row['r'],row['a'],row['b'])
        assert row['Q'] not in trainQs and row['Q'] not in oldQs
        assert (row['a'] in (25,26,27))==(row['split']!='calibration_seen_a_new_b')
        assert row['b'] in (testB if row['split']!='validation_new_b' else valB)
    m=source.WordStudent(True)
    assert sum(v.numel() for v in m.parameters())==10457 and source.FORWARD_MAC==10920
    print('STATIC GATE PASS: 51 new 39-bit native01 Q; 9 immutable F32 checkpoints; source parent b exposure; no optimizer/NN forward',flush=True)


def load_model(path,source):
    js=json.loads(path.read_text());m=source.WordStudent(True)
    s={k:torch.from_numpy(np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy().reshape(v['shape'])) for k,v in js['tensors'].items()}
    m.load_state_dict(s,strict=True);m.eval();return m

def summarize(rows):
    blocks=[]
    for seed in SEEDS:
        for arm in ARMS:
            stats={}
            for split in ('validation_new_b','test_new_b','calibration_seen_a_new_b'):
                x=[r for r in rows if r['seed']==seed and r['arm']==arm and r['split']==split]
                stats[split]={'n':len(x),'exact':sum(r['exact'] for r in x),'first_word':sum(r['first_word'] for r in x),
                 'second_word':sum(r['second_word'] for r in x),'stop_correct':sum(r['stop_correct'] for r in x)}
            blocks.append(dict(seed=seed,arm=arm,metrics=stats))
    gates=[]
    for seed in SEEDS:
        b=next(y for y in blocks if y['seed']==seed and y['arm']=='balanced8_16')['metrics']['test_new_b']
        c=[next(y for y in blocks if y['seed']==seed and y['arm']==arm)['metrics']['test_new_b'] for arm in ('control16','control8')]
        passing=(b['first_word']>=10 and b['exact']>=7 and b['first_word']-max(z['first_word'] for z in c)>=8)
        gates.append(dict(seed=seed,pass_gate=passing,balanced=b,controls=c))
    return blocks,gates

@torch.no_grad()
def infer():
    torch.set_num_threads(1);gate();src=load_source(); rows=[]; fw_total=0
    for seed,arm,path,digest in checkpoints():
        m=load_model(path,src)
        for case in manifest():
            actual,cause,fw=src.free(m,case['Q']);fw_total+=fw
            a=case['expected']
            row=dict(seed=seed,arm=arm,**case,actual=actual,cause=cause,forward_calls=fw,
              exact=actual==a,first_word=actual[:6]==a[:6],second_word=actual[6:12]==a[6:12],
              stop_correct=(cause=='stop' and len(actual)==len(a)))
            rows.append(row)
    blocks,gates=summarize(rows)
    raw=''.join(json.dumps(row,separators=(',',':'))+'\n' for row in rows)
    (P/'raw_results.jsonl').write_text(raw)
    status='PASS' if sum(g['pass_gate'] for g in gates)>=2 else 'FAIL'
    result=dict(work_id='AE1-R15-B-CONTEXT-TRANSFER-20261114',status=status,gate_passing=sum(g['pass_gate'] for g in gates),
       total_model_predictions=len(rows),forward_calls=fw_total,inference_dense_MAC=fw_total*10920,
       param_per_model=10457,optimizer_updates=0,training_MAC=0,
       source_r14_zip_sha256='ec431291aef5e913690d4f0303d94cd3b5768ace73d86f98902cdddebb5eb0d3',
       source_checkpoint_shas={f'{s}_{a}':v for s,a,p,v in checkpoints()},
       raw_sha256=H(P/'raw_results.jsonl'),blocks=blocks,gates=gates)
    (P/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('R15',status,'passed',sum(g['pass_gate'] for g in gates),'/3',len(rows),'complete native01 answers',fw_total,'forward; 0 optimizer')
    for q in blocks:
        z=q['metrics']['test_new_b'];print(q['seed'],q['arm'],'test exact',z['exact'],'firstword',z['first_word'],'secondword',z['second_word'],'stop',z['stop_correct'],'/15')

if __name__=='__main__':
    if sys.argv[1:]==['gate']:gate()
    elif sys.argv[1:]==['infer']:infer()
    else:raise SystemExit('python run_r15.py gate|infer')
