"""R26 frozen-checkpoint first-answer high-bit probe. Run preflight before any forward.
python r26_probe.py preflight|evaluate|replay --root . --work r26_experiment
Requires companion source files from R25 and the three pairs of R20/R23 checkpoint JSON.
"""
import argparse, collections, hashlib, importlib.util, json
from pathlib import Path
import numpy as np
import torch

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def imp(path,name):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def cases(ref):
    # Within each (b,c,d), the only 01 change is a's +4 (one information bit).
    for split,aval,bval in [('calibration',(16,20),range(6,10)),('test',(24,28),range(10,18))]:
        for a in aval:
            for b in bval:
                for c in (0,2):
                    yield dict(split=split,pair=f'{split}_b{b}_c{c}',r=1,a=a,b=b,c=c,d=6,
                               Q=ref.question(1,a,b,c,6),expected=ref.answer(1,a,b))

def preflight(root,work):
    sp=json.loads((work/'prereg.json').read_text())
    assert sp['runner_sha256']==sha(__file__)
    assert sp['manifest_sha256']==sha(work/'manifest.jsonl')
    for path,h in sp['source_sha256'].items(): assert sha(root/path)==h,(path,h)
    ref=imp(root/'r14_source/run.py','r26_ref')
    mod=imp(root/'experiment_r20/run_r19.py','r26_mod')
    rows=[json.loads(s) for s in (work/'manifest.jsonl').read_text().splitlines()]
    assert rows==list(cases(ref)) and len(rows)==48
    assert collections.Counter(r['split'] for r in rows)=={'test':32,'calibration':16}
    assert set(r['Q'] for r in rows).__len__()==48
    assert all(len(r['Q'])==39 and set(r['Q'])<=set('01') and r['expected']==ref.answer(1,r['a'],r['b']) for r in rows)
    for r in rows:
        match=next(q for q in rows if (q['split'],q['b'],q['c'])==(r['split'],r['b'],r['c']) and q['a']!=r['a'])
        assert sum(p!=q for p,q in zip(r['Q'],match['Q']))==1
        assert sum(p!=q for p,q in zip(r['expected'],match['expected']))==1
    historic=set()
    for f in sp['historical_manifests']:
        historic.update(json.loads(line)['Q'] for line in (root/f).read_text().splitlines())
    historic.update(ref.question(*v) for v in mod.high_course(ref))
    assert {r['Q'] for r in rows}.isdisjoint(historic)
    assert set(r['d'] for r in rows)=={6} and set(r['a'] for r in rows if r['split']=='test')=={24,28}
    assert set(r['a'] for r in rows if r['split']=='calibration')=={16,20}
    assert sum(p.numel() for p in mod.DualRoutedStudent(ref).parameters())==sp['parameters_each']==10457
    assert sp['seeds']==[101,202,303] and sp['training_updates']==0 and sp['student_oracle']==False
    print('R26 STATIC PREFLIGHT PASS: 48 legal raw01, 16 calibration + 32 test; paired a high-bit +4; 6 immutable checkpoints; no forward')
    return ref,mod,rows,sp

def summarize(rows,sp):
    seed_results=[]
    for seed in sp['seeds']:
        rec={'seed':seed}
        for split in ('calibration','test'):
            tb={}
            for arm in ('R20','R23'):
                for a in ((16,20) if split=='calibration' else (24,28)):
                    for c in (0,2):
                        subset=[x for x in rows if x['seed']==seed and x['split']==split and x['arm']==arm and x['a']==a and x['c']==c]
                        n=4 if split=='calibration' else 8
                        assert len(subset)==n
                        tb[f'{arm}_a{a}_c{c}']={'n':n,'first':sum(x['first_correct'] for x in subset),
                            'stop':sum(x['stop_correct'] for x in subset),'exact':sum(x['exact'] for x in subset),
                            'margin':float(np.mean([x['stop_margin'] for x in subset]))}
            if split=='test':
                crit=[]
                for a in (24,28):
                    o0,n0=tb[f'R20_a{a}_c0'],tb[f'R23_a{a}_c0']
                    o2,n2=tb[f'R20_a{a}_c2'],tb[f'R23_a{a}_c2']
                    crit.append({'a':a,'c2_margin_gain':n2['margin']-o2['margin'],
                        'first_delta':(n0['first']+n2['first'])-(o0['first']+o2['first']),
                        'c0_stop_delta':n0['stop']-o0['stop'],
                        'pass':n2['margin']-o2['margin']>=sp['gate']['min_c2_margin_gain'] and
                        n0['first']+n2['first']>=o0['first']+o2['first']-sp['gate']['max_first_loss_16'] and
                        n0['stop']>=o0['stop']-sp['gate']['max_c0_stop_loss_8']})
                # Guard against full ceiling/floor: without varying first-word correctness, retention is uninformative.
                first=[tb[f'{arm}_a{a}_c{c}']['first'] for arm in ('R20','R23') for a in (24,28) for c in (0,2)]
                informative=0<sum(first)<8*len(first)
                rec[split]={'cells':tb,'checks':crit,'informative_first':informative,
                    'pass':informative and all(x['pass'] for x in crit)}
            else:rec[split]={'cells':tb}
        seed_results.append(rec)
    passing=sum(x['test']['pass'] for x in seed_results)
    return {'gate':'PASS' if passing>=sp['gate']['min_seed_pass'] else 'FAIL',
        'passing_seeds':passing,'seeds':seed_results,
        'scope':'fixed-checkpoint high-bit a=24/28 with d6; student-heldout not researcher-blind; comparisons R20/R23 are historical curriculum intervention; NOT evidence of autonomous SLE rule invention'}

@torch.no_grad()
def evaluate(root,work):
    ref,mod,cases_,sp=preflight(root,work)
    torch.set_num_threads(1);out=[]
    for seed in sp['seeds']:
        for arm,prefix in [('R20','outputs_r20'),('R23','r23_outputs')]:
            net=mod.load_weights(root/prefix/f'weights_{seed}_dual.json',mod.DualRoutedStudent(ref));net.eval()
            for row in cases_:
                actual,cause,n=ref.free(net,row['Q'])
                logits=net(torch.from_numpy(ref.xvec(row['Q']+row['expected'][:6])).unsqueeze(0))[0].detach().numpy()
                out.append({**row,'seed':seed,'arm':arm,'actual':actual,'cause':cause,'n_forward':n,
                    'exact':actual==row['expected'],'first_correct':actual[:6]==row['expected'][:6],
                    'stop_correct':bool(logits.argmax()==2),
                    'stop_logits':[float(z) for z in logits],
                    'stop_margin':float(logits[2]-max(logits[0],logits[1]))})
    (work/'raw_results.jsonl').write_text(''.join(json.dumps(z,separators=(',',':'))+'\n' for z in out))
    result=summarize(out,sp)
    result.update(rows=len(out),greedy_forwards=sum(x['n_forward'] for x in out),stop_forwards=len(out),
        inference_MAC=(sum(x['n_forward'] for x in out)+len(out))*10920,
        training_updates=0,parameters_each=10457,raw_sha256=sha(work/'raw_results.jsonl'))
    (work/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('R26 T RESULT',result['gate'],result['passing_seeds'],'/3',result['rows'],'responses',result['inference_MAC'],'MAC')
    for x in result['seeds']:
        print('Seed',x['seed'],'TEST',x['test']['checks'],'informative',x['test']['informative_first'])

def replay(root,work):
    _,_,_,sp=preflight(root,work)
    v=imp(root/'r23_experiment/verify_numpy.py','r26_independent_np')
    rows=[json.loads(s) for s in (work/'raw_results.jsonl').read_text().splitlines()]
    assert len(rows)==288
    res=json.loads((work/'results.json').read_text())
    assert sha(work/'raw_results.jsonl')==res['raw_sha256']
    assert summarize(rows,sp)['seeds']==res['seeds']
    cache={};total=0;maxdiff=0
    for x in rows:
        prefix='outputs_r20' if x['arm']=='R20' else 'r23_outputs';key=(prefix,x['seed'])
        if key not in cache:cache[key]=v.arrays(root/prefix/f'weights_{x["seed"]}_dual.json')
        w=cache[key];actual,cause,n=v.generate(x['Q'],w)
        assert (actual,cause,n)==(x['actual'],x['cause'],x['n_forward'])
        ll=v.logits(x['Q'],x['expected'][:6],w)
        diff=float(np.max(np.abs(ll-np.array(x['stop_logits']))));maxdiff=max(maxdiff,diff)
        assert diff<5e-5 and abs(float(ll[2]-max(ll[0],ll[1]))-x['stop_margin'])<5e-5
        assert bool(int(ll.argmax())==2)==x['stop_correct'];total+=n

    assert res['greedy_forwards']==total and res['inference_MAC']==(total+len(rows))*10920
    print('R26 INDEPENDENT NUMPY PASS',len(rows),'native01 greedy outputs & stop logits; maximum logit difference',maxdiff)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('preflight','evaluate','replay'))
    p.add_argument('--root',required=True);p.add_argument('--work',required=True)
    a=p.parse_args();root=Path(a.root).resolve();work=Path(a.work).resolve()
    {'preflight':preflight,'evaluate':evaluate,'replay':replay}[a.mode](root,work)
