"""R12 pre-registered AE1 bit8 -> teacher-forced output margin intervention.
Source student remains a neural model; no training, editing or teacher oracle to answer.
"""
import argparse, base64, hashlib, json, sys
from pathlib import Path
import numpy as np
import torch
P=Path(__file__).resolve().parent
S=P/'source'
sys.path.insert(0,str(S))
import run as src
SEEDS=(101,202,303)
ARMS=('tied','untied')
BASES=(0,1,2,3)
ANCHORS=(18,19)
MAC=10920

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def manifest():
    for role in ('first','second'):
        for low in BASES:
            for anchor in ANCHORS:
                split='diagnostic_val' if low<2 else 'diagnostic_test'
                for flip in (0,8):
                    a,b=(low+flip,anchor) if role=='first' else (anchor,low+flip)
                    q=src.question(2,a,b,0,1)
                    ans=src.answer(2,a,b)
                    # 5-bit ID bit of value 8: position 1 of word, or absolute position 7.
                    index=1 if role=='first' else 7
                    yield dict(split=split,role=role,low=low,anchor=anchor,flip=flip,
                               a=a,b=b,r=2,c=0,d=1,Q=q,expected=ans,
                               output_index=index,prefix=ans[:index],target=ans[index])

def source_checks():
    assert sha(S/'run.py')=='79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a'
    assert sha(S/'results.json')=='78353a7db90a981eba4a9700361a00fafaf77124ef3ec230b98c5bd90d6152bd'
    report=json.loads((S/'results.json').read_text())
    rows=json.loads((S/'parent_course.json').read_text())
    lessons=[tuple(x) for x in rows]+src.inject()
    assert len(lessons)==136 and len(set(lessons))==112
    for seed in SEEDS:
        for arm in ARMS:
            path=S/'checkpoints'/f'weights_{seed}_{arm}.json'
            block=next(x for x in report['blocks'] if x['seed']==seed and x['arm']==arm)
            assert sha(path)==block['checkpoint_sha256']
    return lessons

def gate():
    spec=json.loads((P/'prereg.json').read_text())
    assert spec['script_sha256']==sha(P/'probe.py')
    assert spec['manifest_sha256']==sha(P/'cases.jsonl')
    expected=[json.loads(line) for line in (P/'cases.jsonl').read_text().splitlines()]
    assert expected==list(manifest()) and len(expected)==32 and len({x['Q'] for x in expected})==32
    lessons=source_checks()
    trained=set(x for _,a,b,c,d in lessons for x in (a,b,c,d))
    assert not trained.intersection({8,9,10,11})
    assert len({(r['role'],r['low'],r['anchor']) for r in expected})==16
    for r in expected:
        assert len(r['Q'])==39 and len(r['expected'])==13 and r['output_index'] in (1,7)
        assert r['target']==('1' if r['flip'] else '0')
        assert r['Q'].startswith('01010') and r['Q'].endswith('111100')
    print('STATIC GATE PASS: 32 legal 39bit cases, 16 bit8 pairs, 6 immutable F32 checkpoints; no neural calls')
    return expected

def model(seed,arm):
    data=json.loads((S/'checkpoints'/f'weights_{seed}_{arm}.json').read_text())
    m=src.WordStudent(arm=='tied')
    state={}
    for k,v in data['tensors'].items():
        state[k]=torch.from_numpy(np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').reshape(v['shape']).copy())
    m.load_state_dict(state,strict=True);m.eval()
    return m

def compute():
    torch.set_num_threads(1)
    cases=gate()
    out=[]
    with torch.no_grad():
        for seed in SEEDS:
            for arm in ARMS:
                m=model(seed,arm)
                for x in cases:
                    q=x['Q'];s=q+x['prefix'];inp=torch.from_numpy(src.xvec(s)).unsqueeze(0)
                    logits=m(inp)[0].numpy().tolist()
                    margin=float(logits[1]-logits[0])
                    w=torch.from_numpy(src.xvec(q)).reshape(1,80,2)[:,9:33,:].reshape(1,4,12)
                    emb=torch.tanh(m.enc(w)) if arm=='tied' else torch.tanh(torch.einsum('bik,ijk->bij',w,m.enc_w)+m.enc_b)
                    role_ix=0 if x['role']=='first' else 1
                    out.append(dict(seed=seed,arm=arm,**x,logits=[float(z) for z in logits],
                                    margin_1_minus_0=margin,predicted='01S'[int(np.argmax(logits))],
                                    embedding=[float(z) for z in emb[0,role_ix].numpy()]))
    bykey={(x['seed'],x['arm'],x['role'],x['low'],x['anchor'],x['flip']):x for x in out}
    pairs=[]
    for seed in SEEDS:
        for arm in ARMS:
            for role in ('first','second'):
                for low in BASES:
                    for anchor in ANCHORS:
                        pre=bykey[(seed,arm,role,low,anchor,0)]
                        post=bykey[(seed,arm,role,low,anchor,8)]
                        delta=float(post['margin_1_minus_0']-pre['margin_1_minus_0'])
                        embed_norm=float(np.linalg.norm(np.array(post['embedding'])-np.array(pre['embedding'])))
                        pairs.append(dict(seed=seed,arm=arm,role=role,split=pre['split'],low=low,anchor=anchor,
                            baseline_margin=pre['margin_1_minus_0'],flipped_margin=post['margin_1_minus_0'],
                            margin_delta=delta,embedding_delta_l2=embed_norm,
                            baseline_target_correct=pre['predicted']=='0',flipped_target_correct=post['predicted']=='1'))
    checks=[]
    for seed in SEEDS:
        p=[z for z in pairs if z['seed']==seed and z['arm']=='tied' and z['role']=='first' and z['split']=='diagnostic_test']
        aligned=sum(x['margin_delta']>0 for x in p)
        still_bad=sum(not x['flipped_target_correct'] for x in p)
        checks.append(dict(seed=seed,aligned=aligned,still_bad=still_bad,passes=(aligned>=3 and still_bad>=3)))
    passes=sum(x['passes'] for x in checks)
    result=dict(work_id='AE1-BIT8-ROUTE-R12-20261114',profile='SLE-AE1-n5-v1',
        question_count=32,student_count=6,inference_calls=len(out),pair_count=len(pairs),
        model_params=dict(tied=10457,untied=11081),dense_mac_per_call=MAC,
        total_forward_dense_mac=len(out)*MAC,optimizer_updates=0,
        test_gate='PASS' if passes>=2 else 'FAIL',seed_gates=checks,
        cases_sha256=sha(P/'cases.jsonl'),source_checkpoint_unchanged=True,
        source_zip='sle_ae1_word_weight_tying_20261114.zip',
        source_zip_sha256='53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0')
    (P/'logits.jsonl').write_text(''.join(json.dumps(z,separators=(',',':'))+'\n' for z in out))
    (P/'pairs.jsonl').write_text(''.join(json.dumps(z,separators=(',',':'))+'\n' for z in pairs))
    result['logits_sha256']=sha(P/'logits.jsonl');result['pairs_sha256']=sha(P/'pairs.jsonl')
    (P/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('TEST GATE',result['test_gate'],checks,'student-cases',len(out),'pairs',len(pairs))
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('cmd',choices=('gate','run','manifest'));args=a.parse_args()
    if args.cmd=='gate':gate()
    if args.cmd=='manifest':
        for r in manifest():print(json.dumps(r,separators=(',',':')))
    if args.cmd=='run':compute()
