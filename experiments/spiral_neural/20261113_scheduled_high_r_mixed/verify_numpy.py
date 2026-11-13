"""Independent NumPy forward from JSON checkpoints; checks generated bits and role comparisons."""
import base64, hashlib, json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'20261113_scheduled_input_target_exposure'

def weights(path):
    obj=json.loads(path.read_text())
    d={}
    for k,t in obj['tensors'].items():
        arr=np.frombuffer(base64.b64decode(t['little_endian_base64']),dtype='<f4').reshape(t['shape']).copy()
        d[k]=arr
    assert sorted(d)==['0.bias','0.weight','2.bias','2.weight']
    return d

def infer(w,q):
    out=''
    for n in range(32):
        s=q+out
        if len(s)>80:return out,'overflow',n
        x=np.zeros(160,dtype=np.float32)
        for i,char in enumerate(s):x[2*i+int(char)]=1
        z=w['2.weight']@np.tanh(w['0.weight']@x+w['0.bias'])+w['2.bias']
        out+='01S'[int(np.argmax(z))]
        if out.endswith('S'):return out,'stop',n+1
    return out,'cap',32

def word(v):return f'{v:05b}0'
def q(r,a,b,c=0,d=0):return '01'+'010'+f'{r:03b}'+'0'+''.join(word(v) for v in (a,b,c,d))+'111100'
def ans(r,a,b):return word(a)+(word(b) if r==2 else '')+'S'

def main():
    rec=[json.loads(line) for line in (HERE/'raw_cases.jsonl').read_text().splitlines()]
    assert len(rec)==288
    assert hashlib.sha256((HERE/'raw_cases.jsonl').read_bytes()).hexdigest()==json.loads((HERE/'results.json').read_text())['raw_sha256']
    matched=0;failed=[]
    for seed in [101,202]:
        w=weights(HERE/f'weights_seed{seed}_mixed.json')
        for z in (r for r in rec if r['seed']==seed):
            assert q(z['r'],z['a'],z['b'],z['c'],z['d'])==z['Q']
            assert ans(z['r'],z['a'],z['b'])==z['expected']
            generated,reason,n=infer(w,z['Q'])
            matched+=(generated,reason,n)==(z['actual'],z['cause'],z['forward_calls'])
            if (generated,reason,n)!=(z['actual'],z['cause'],z['forward_calls']):failed.append((seed,z['split'],z['Q'],generated,z['actual']))
    assert not failed, failed[:5]
    comparisons=[]
    for seed in [101,202]:
        for arm in ['high_output','high_input_only']:
            w=weights(OLD/f'weights_seed{seed}_{arm}.json')
            for s in [4,5]:
                for r in [1,2]:
                    correct=first=second=stops=0;errors=[]
                    for v in range(15,24):
                        pred,reason,_=infer(w,q(r,s,v))
                        expected=ans(r,s,v)
                        correct+=pred==expected
                        first+=pred[:6]==word(s)
                        second+=r==2 and pred[6:12]==word(v)
                        stops+=pred.endswith('S') and len(pred)==len(expected)
                        if pred!=expected:errors.append({'s':s,'v':v,'r':r,'expected':expected,'actual':pred})
                    comparisons.append({'seed':seed,'historical_arm':arm,'partner':s,'r':r,'exact':correct,'n':9,'first_word':first,'second_word':second,'stop':stops,'failures':errors})
    output={'independent_numpy_replay':'PASS','matched':matched,'total':len(rec),'baseline_pr39_new_readonly_evaluations':comparisons,'new_training_updates_in_verifier':0,
            'baseline_cases':144,'first_incorrect_new_mixed':[r for r in rec if r['actual']!=r['expected']][:6]}
    (HERE/'verification.json').write_text(json.dumps(output,indent=2)+'\n')
    print('INDEPENDENT NUMPY',matched,'/',len(rec))
    for z in comparisons:print(z['seed'],z['historical_arm'],f"s{z['partner']}",f"r{z['r']}",str(z['exact'])+'/9', 'stop',z['stop'])
if __name__=='__main__':main()
