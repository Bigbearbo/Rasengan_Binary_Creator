"""AE1-R21 predeclared STOP c-bit intervention. No optimizer or training.

Input: pristine R20 companion archive extracted as a directory containing
r14_source/, experiment_r19/, experiment_r20/, outputs_r19/, outputs_r20/.
Commands: python run_r21.py gate --source-root ..
          python run_r21.py diagnose --source-root ..
          python run_r21.py numpy_verify --source-root ..
"""
import argparse,base64,collections,hashlib,importlib.util,json
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent
SEEDS=(101,202,303)
ARMS=('r19_dual_route','r20_corrected_route')
FWD_MAC=10920

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def imports(p,name):
    spec=importlib.util.spec_from_file_location(name,p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def rows(ref):
    for a in (0,1,2,3):
        for b in (24,25,26,27,28):
            for c in (2,0):
                q=ref.question(1,a,b,c,3)
                yield dict(split='validation_diagnostic' if a in (0,1) else 'test_diagnostic',
                           pair=f'a{a}_b{b}',r=1,a=a,b=b,c=c,d=3,Q=q,expected=ref.answer(1,a,b))

def gate(src):
    spec=json.loads((HERE/'prereg.json').read_text())
    r14=imports(src/'r14_source'/'run.py','r21_r14')
    m19=imports(src/'experiment_r19'/'run_r19.py','r21_r19')
    m20=imports(src/'experiment_r20'/'run_r19.py','r21_r20')
    panel=list(rows(r14));manifest=[json.loads(line) for line in (HERE/'manifest.jsonl').read_text().splitlines()]
    assert manifest==panel and len(panel)==40 and len({r['Q'] for r in panel})==40
    assert collections.Counter(r['split'] for r in panel)=={'validation_diagnostic':20,'test_diagnostic':20}
    assert all(r['expected'].endswith('S') and len(r['Q'])==39 and r['Q'][6]=='0' for r in panel)
    assert all(sum(v!=w for v,w in zip(r14.word(0),r14.word(2)))==1 for r in panel)
    assert sha(HERE/'manifest.jsonl')==spec['manifest_sha256']
    assert spec['runner_sha256']==sha(HERE/'run_r21.py')
    assert spec['r20_zip_sha256']=='9c698971dfd6fe1f89701be99fc2fa592edce006f017efd5c4e89dbdf5671866'
    for relative,s in spec['frozen_source_sha256'].items():assert sha(src/relative)==s,(relative,sha(src/relative),s)
    course=m20.high_course(r14)
    assert len(course)==136 and sum(q[0]==1 for q in course)==60 and sum(q[0]==2 for q in course)==76
    assert spec['seeds']==list(SEEDS) and spec['profile']=='SLE-AE1-n5-v1'
    assert spec['per_model_parameters']==10457 and spec['forward_MAC']==FWD_MAC
    assert spec['new_training_updates']==0 and spec['expected_neural_forwards']==240
    print('GATE PASS: 40 legal Q, 20 matched c2->c0 pairs, 2 frozen arms x 3 seeds; 0 forwards, 0 updates')
    return r14,m19,m20,panel,spec

def unpack(path):
    d=json.loads(path.read_text())
    return {k:np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy().reshape(v['shape']) for k,v in d['tensors'].items()}

def numpy_logits(q,prefix,w,arm):
    state=np.zeros((80,2),dtype=np.float32)
    for i,ch in enumerate(q+prefix):state[i,'01'.index(ch)]=1
    words=state[9:33].reshape(4,12).copy()
    cursor=len(prefix)
    if cursor<6:words[1:]=0
    if arm=='r19_dual_route' and 6<=cursor<12:words[[0,2,3]]=0
    if arm=='r20_corrected_route' and q[6]=='1' and 6<=cursor<12:words[[0,2,3]]=0
    embeddings=np.tanh(words@w['enc.weight'].T+w['enc.bias'])
    position=np.zeros((33,),dtype=np.float32);position[cursor]=1
    x=np.concatenate((embeddings.reshape(-1),state[5:9].reshape(-1),position))
    hidden=np.tanh(x@w['hidden.weight'].T+w['hidden.bias'])
    return hidden@w['out.weight'].T+w['out.bias']

def records_from_logits(rows,logits,seed,arm):
    for case,logit in zip(rows,logits):
        vals=[float(v) for v in logit]
        s=float(logit[2]-max(logit[0],logit[1]))
        yield {**case,'seed':seed,'arm':arm,'logits_0_1_S':vals,'S_margin':s,'S_predicted':int(np.argmax(logit))==2}

def summary(output):
    blocks=[];by={(v['seed'],v['arm'],v['split'],v['pair'],v['c']):v for v in output}
    for seed in SEEDS:
        for arm in ARMS:
            for split in ('validation_diagnostic','test_diagnostic'):
                ps=sorted({r['pair'] for r in output if r['split']==split})
                pairs=[(by[(seed,arm,split,p,2)],by[(seed,arm,split,p,0)]) for p in ps]
                deltas=[z['S_margin']-x['S_margin'] for x,z in pairs]
                old=sum(x['S_predicted'] for x,z in pairs)
                new=sum(z['S_predicted'] for x,z in pairs)
                recovered=sum((not x['S_predicted']) and z['S_predicted'] for x,z in pairs)
                regressed=sum(x['S_predicted'] and (not z['S_predicted']) for x,z in pairs)
                blocks.append(dict(seed=seed,arm=arm,split=split,c2_correct=old,c0_correct=new,
                    recovered=recovered,regressed=regressed,flip=recovered+regressed,
                    mean_delta_margin=float(np.mean(deltas)),mean_abs_delta_margin=float(np.mean(np.abs(deltas))),
                    max_abs_delta_margin=float(np.max(np.abs(deltas)))))
    r19_test=[x for x in blocks if x['arm']=='r19_dual_route' and x['split']=='test_diagnostic']
    r20_test=[x for x in blocks if x['arm']=='r20_corrected_route' and x['split']=='test_diagnostic']
    pass_seed=[x['seed'] for x in r20_test if x['c0_correct']-x['c2_correct']>=3 and x['recovered']>=3]
    negative_control_pass=all(x['flip']==0 and x['max_abs_delta_margin']<1e-5 for x in r19_test)
    return dict(gate='PASS' if len(pass_seed)>=2 and negative_control_pass else 'FAIL',
      pass_seeds=pass_seed,negative_control_r19_invariant=negative_control_pass,blocks=blocks)

def model_for(src,ref,m19,m20,seed,arm):
    module,path=(m19,src/'outputs_r19'/f'weights_{seed}_dual.json') if arm=='r19_dual_route' else (m20,src/'outputs_r20'/f'weights_{seed}_dual.json')
    return module.load_weights(path,module.DualRoutedStudent(ref))

def run(src):
    ref,m19,m20,panel,spec=gate(src)
    torch.set_num_threads(1)
    output=[]
    with torch.no_grad():
        for seed in SEEDS:
            for arm in ARMS:
                model=model_for(src,ref,m19,m20,seed,arm)
                batch=torch.from_numpy(np.stack([ref.xvec(v['Q']+v['expected'][:6]) for v in panel]))
                logits=model(batch).detach().numpy()
                output.extend(records_from_logits(panel,logits,seed,arm))
    assert len(output)==240
    dest=HERE/'raw_logits.jsonl'
    assert not dest.exists(), 'refuse overwrite results'
    dest.write_text(''.join(json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n' for x in output))
    report=summary(output);report.update(work_id=spec['work_id'],neural_forwards=len(output),new_updates=0,
       inference_dense_MAC=len(output)*FWD_MAC,per_model_parameters=10457,
       manifest_sha256=spec['manifest_sha256'],runner_sha256=spec['runner_sha256'],
       raw_sha256=sha(dest),source_checkpoint_sha256={k:v for k,v in spec['frozen_source_sha256'].items() if 'weights_' in k},
       status='nonblind_model_debug_only',stop_target_exposure={'r1_per_epoch':60,'r2_per_epoch':76,'r1_total_150':9000,'r2_total_150':11400})
    (HERE/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('DIAG',report['gate'],'seeds',report['pass_seeds'],'neg-control',report['negative_control_r19_invariant'],
          'forwards',len(output),'MAC',report['inference_dense_MAC'])
    for block in report['blocks']:print(block)

def verify(src):
    ref,m19,m20,panel,spec=gate(src)
    raw=[json.loads(x) for x in (HERE/'raw_logits.jsonl').read_text().splitlines()]
    report=json.loads((HERE/'results.json').read_text())
    assert sha(HERE/'raw_logits.jsonl')==report['raw_sha256'] and len(raw)==240
    max_err=0;bad=0
    for row in raw:
        path=(src/'outputs_r19' if row['arm']=='r19_dual_route' else src/'outputs_r20')/f"weights_{row['seed']}_dual.json"
        logits=numpy_logits(row['Q'],row['expected'][:6],unpack(path),row['arm'])
        err=float(np.max(np.abs(logits-row['logits_0_1_S'])))
        max_err=max(max_err,err)
        if err>5e-5 or int(np.argmax(logits))!=(2 if row['S_predicted'] else int(np.argmax(row['logits_0_1_S']))):bad+=1
    assert bad==0,(bad,max_err)
    for b in summary(raw)['blocks']:
        check=next(x for x in report['blocks'] if x['seed']==b['seed'] and x['arm']==b['arm'] and x['split']==b['split'])
        assert b==check
    assert report['gate']==summary(raw)['gate']
    print('INDEPENDENT NUMPY PASS',len(raw),'logits, max_abs_error',max_err,'additional torch forwards 0, updates 0')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('gate','diagnose','numpy_verify'))
    parser.add_argument('--source-root',default='..');args=parser.parse_args()
    root=Path(args.source_root).resolve()
    if args.mode=='gate':gate(root)
    elif args.mode=='diagnose':run(root)
    else:verify(root)
