"""Independent fixed-checkpoint SLE01 R22 logits replay, no optimizer/LLM.
python PUBLIC_NUMPY_VERIFY.py --source-root /path/to/R20_extracted --raw /path/to/r22/raw_logits.jsonl
"""
import argparse,base64,hashlib,json
from pathlib import Path
import numpy as np

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def unpack(path):
    d=json.loads(Path(path).read_text())
    return {k:np.frombuffer(base64.b64decode(t['little_endian_base64']),dtype='<f4').copy().reshape(t['shape']) for k,t in d['tensors'].items()}
def logits(row,w):
    state=np.zeros((80,2),dtype=np.float32)
    seq=row['Q']+row['expected'][:6]
    for i,c in enumerate(seq):state[i,'01'.index(c)]=1
    words=state[9:33].reshape(4,12).copy()
    cursor=6
    if row['arm']=='r19_dual_route':words[[0,2,3]]=0
    # In R20, r1 STOP (Q[6]=='0') has full-word access.
    elif row['arm']!='r20_corrected_route':raise ValueError(row['arm'])
    e=np.tanh(words@w['enc.weight'].T+w['enc.bias'])
    position=np.zeros(33,dtype=np.float32);position[cursor]=1
    features=np.concatenate([e.reshape(-1),state[5:9].reshape(-1),position])
    h=np.tanh(features@w['hidden.weight'].T+w['hidden.bias'])
    return h@w['out.weight'].T+w['out.bias']
def main(src,raw):
    data=[json.loads(z) for z in raw.read_text().splitlines()]
    assert len(data)==240
    assert len({(z['seed'],z['arm'],z['Q']) for z in data})==240
    assert all(z['r']==1 and z['c'] in (0,2) and z['d']==2 and len(z['Q'])==39 for z in data)
    maxerr=0;checked=0
    for arm in ('r19_dual_route','r20_corrected_route'):
        for seed in (101,202,303):
            file=src/('outputs_r19' if arm=='r19_dual_route' else 'outputs_r20')/f'weights_{seed}_dual.json'
            weights=unpack(file)
            for z in data:
                if z['seed']!=seed or z['arm']!=arm:continue
                calc=logits(z,weights)
                err=float(np.max(np.abs(calc-z['logits_0_1_S'])))
                assert err<5e-5,(arm,seed,err)
                assert int(np.argmax(calc))==int(np.argmax(z['logits_0_1_S']))
                maxerr=max(maxerr,err);checked+=1
    assert checked==240
    print(f'PASS {checked}/240 independent NumPy logits and argmax; max error {maxerr:.9g}; new optimizer updates=0')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--raw',type=Path,required=True);args=p.parse_args();main(args.source_root,args.raw)
