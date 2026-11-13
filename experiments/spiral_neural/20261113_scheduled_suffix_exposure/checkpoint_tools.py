"""Deterministic post-run checkpoint export and independent read-only verification.
The preregistered train program and fixed results are not modified. Use Python, NumPy, PyTorch.
"""
import argparse,base64,copy,hashlib,json
from pathlib import Path
import numpy as np,torch
from torch import nn
import experiment as exp
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'results.json'; PROTO=ROOT/'preregistered_protocol.json'; CHECKPOINTS=ROOT/'checkpoints'

def export():
    CHECKPOINTS.mkdir(exist_ok=True)
    report=json.loads(DATA.read_text());manifest=json.loads(PROTO.read_text());records=[]
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    for seed in exp.SEEDS:
        initial=exp.network(seed)
        permutations=[np.random.default_rng(seed+41000+e).permutation(480) for e in range(exp.EPOCHS)]
        assert exp.sh(exp.canonical([x.tolist() for x in permutations]).encode())==manifest['schedule_sha256_by_seed'][str(seed)]
        for mode in exp.MODES:
            entry=next(x for x in report['per_model'] if (x['seed'],x['mode'])==(seed,mode))
            net=copy.deepcopy(initial);opt=torch.optim.Adam(net.parameters(),lr=exp.LR)
            steps=0
            for epoch in range(exp.EPOCHS):
                X,y=exp.teacher(exp.rows('train',epoch,mode));perm=permutations[epoch]
                for offset in range(0,len(y),exp.BATCH):
                    ids=perm[offset:offset+exp.BATCH]
                    loss=nn.functional.cross_entropy(net(X[ids]),y[ids]);opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(net.parameters(),1.);opt.step();steps+=1
            actual=exp.weights_sha(net)
            if actual!=entry['final_weights_sha256'] or steps!=entry['optimizer_steps']:
                raise AssertionError(f'REPLAY MISSMATCH {seed}/{mode} expected {entry["final_weights_sha256"]} got {actual}')
            cp={'schema':'AE1-SUFFIX-FINAL-WEIGHTS-v1','purpose':'inference_only_no_adam_state','source_sha256':report['source_sha256'],'protocol_sha256':report['protocol_sha256'],'seed':seed,'mode':mode,'updates':steps,'initial_weights_sha256':entry['initial_sha256'],'final_weights_sha256':actual,'tensors':{k:{'shape':list(v.shape),'dtype':'float32','little_endian_base64':base64.b64encode(v.detach().numpy().astype('<f4').tobytes()).decode('ascii')} for k,v in net.state_dict().items()}}
            path=CHECKPOINTS/f'weights_seed{seed}_{mode}.json'
            if path.exists():
                original=json.loads(path.read_text());assert original==cp
            else:path.write_text(json.dumps(cp,sort_keys=True,separators=(',',':'))+'\n')
            records.append({'seed':seed,'mode':mode,'checkpoint':path.name,'size_bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'final_weights_sha256':actual,'match':True})
            print('CHECKPOINT EXACT',seed,mode,actual,flush=True)
    result={'records':records,'rerun_type':'post-run deterministic checkpoint export, identical frozen schedule and model; not a second scientific trial','scope':'inference weights only; optimizer not exported'}
    file=ROOT/'checkpoint_export_results.json'
    if file.exists(): assert json.loads(file.read_text())==result
    else:file.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return verify()

def verify():
    report=json.loads(DATA.read_text());passed=0
    for entry in report['per_model']:
        seed,mode=entry['seed'],entry['mode'];cp=json.loads((CHECKPOINTS/f'weights_seed{seed}_{mode}.json').read_text())
        net=exp.network(seed)
        with torch.no_grad():
            for name,p in net.state_dict().items():
                z=cp['tensors'][name];v=np.frombuffer(base64.b64decode(z['little_endian_base64']),dtype='<f4').reshape(z['shape']).copy()
                assert list(p.shape)==z['shape'];p.copy_(torch.from_numpy(v))
        assert exp.weights_sha(net)==cp['final_weights_sha256']==entry['final_weights_sha256']
        for split in ('train','val','test'):
            for suffix in ('seen','changed_low','unseen_high'):
                for r in (1,2):
                    for a,b,c,d,_,actual in entry['evaluation'][split][suffix][str(r)]['predictions']:
                        observed,_=exp.run_free(net,exp.qbits(r,a,b,c,d));assert observed==actual
                        passed+=1
        print('PASS eval checkpoint',seed,mode)
    assert passed==864
    print('PASS 864/864 matching archive free-generation outputs and four final weight hashes')
    return passed

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['export','verify']);a=parser.parse_args();export() if a.command=='export' else verify()
