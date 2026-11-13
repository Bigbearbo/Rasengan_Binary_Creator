"""AE1 independent six-model native-01 numeric transfer, frozen Git prereg 2e60b00960a355891950b22242a6a6f7fee2d0c7.
No training; all failed outputs are saved. Dependencies: Python, numpy, torch.
"""
import json,hashlib,base64,math,collections,sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
SW=ROOT/'20261113_scheduled_role_swap_pilot'
MX=ROOT/'20261113_scheduled_role_mix_pilot'
SHA_SRC={'sw':'05e2d730eecefcb50fa92392697556ffde313f5ecb59c2f4e583aad52e321303','mx':'e5b6f8b0c382b2720efdfa8acaa75c8352a41226045cc7768824e1630b47024c'}
PRE='2e60b00960a355891950b22242a6a6f7fee2d0c7'
def H(b):return hashlib.sha256(b).hexdigest()
def w(v):assert 0<=v<=29;return f'{v:05b}0'
def question(r,a,b):return '01010'+f'{r:03b}'+'0'+w(a)+w(b)+w(0)+w(0)+'111100'
def answer(r,a,b):return w(a)+(w(b) if r==2 else '')+'S'
def input01(b):
    assert 0<len(b)<=80 and set(b)<=set('01'); x=np.zeros(160,dtype=np.float32)
    for i,v in enumerate(b):x[2*i+int(v)]=1
    return torch.from_numpy(x).unsqueeze(0)
@torch.no_grad()
def predict(m,q):
    a=''
    for t in range(32):
        if len(q)+len(a)>80:return a,'overflow',t
        v=m(input01(q+a))[0]
        a+='01S'[int(torch.argmax(v))]
        if a.endswith('S'):return a,'stop',t+1
    return a,'cap',32
def reconstruct(filename,seed,arm,expect):
    cp=json.loads(filename.read_text());assert cp['seed']==seed and cp['weights_sha256']==expect
    m=nn.Sequential(nn.Linear(160,64),nn.Tanh(),nn.Linear(64,3));state={}
    for k,v in cp['tensors'].items():
        b=base64.b64decode(v['little_endian_base64']);arr=np.frombuffer(b,dtype='<f4').copy().reshape(v['shape'])
        assert np.isfinite(arr).all();state[k]=torch.from_numpy(arr)
    m.load_state_dict(state);parts=[]
    for k,t in m.state_dict().items():parts.extend([k.encode(),t.detach().numpy().tobytes()])
    assert H(b''.join(parts))==expect
    assert sum(p.numel() for p in m.parameters())==10499
    return m
def main():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    assert H((SW/'run.py').read_bytes())==SHA_SRC['sw']
    assert H((MX/'run.py').read_bytes())==SHA_SRC['mx']
    assert question(2,0,6)=='010100100000000001100000000000000111100'
    assert answer(2,0,6)=='000000001100S'
    original=[(SW,'HIGH_FIRST'),(SW,'HIGH_SECOND'),(MX,'MIX_PARITY')]
    models=[];all_replay=0;replay_calls=0
    for folder,arm in original:
        info=json.loads((folder/'results.json').read_text());raw=(folder/'raw_cases.jsonl').read_bytes()
        assert H(raw)==info['raw_sha256']; rows=[json.loads(s) for s in raw.splitlines()]
        assert len(rows)==(720 if folder==SW else 360)
        assert all(len(x['Q'])==39 and x['Q']==question(x['r'],x['a'],x['b']) and x['expected']==answer(x['r'],x['a'],x['b']) for x in rows)
        for entry in info['models']:
            if entry['arm']!=arm:continue
            seed=entry['seed'];cpath=entry.get('checkpoint_path') or entry.get('checkpoint')
            m=reconstruct(folder/cpath,seed,arm,entry['final_sha256']);these=[x for x in rows if x['seed']==seed and x['arm']==arm]
            assert len(these)==180
            for x in these:
                got,why,forward=predict(m,x['Q']);assert (got,why)==(x['actual'],x['cause']), (seed,arm,x)
                if 'forward_calls' in x: assert forward==x['forward_calls']
                all_replay+=1;replay_calls+=forward
            models.append((seed,arm,m,entry['final_sha256']))
    assert len(models)==6 and all_replay==1080
    print('SOURCE_GATE_PASS',len(models),'checkpoints,',all_replay,'old replies,',replay_calls,'old forward',flush=True)
    rows=[];forward_total=0;keys=set()
    for seed,arm,m,hashv in models:
        for domain,highs in [('seen_values',range(6,15)),('unseen_values',range(15,24))]:
            for v in highs:
                for s in range(6):
                    for orientation in ('HIGH_FIRST','HIGH_SECOND'):
                        a,b=(v,s) if orientation=='HIGH_FIRST' else (s,v)
                        q=question(2,a,b);truth=answer(2,a,b)
                        assert len(q)==39 and q.endswith('111100') and set(q)<=set('01')
                        key=(seed,arm,domain,v,s,orientation);assert key not in keys;keys.add(key)
                        got,why,n=predict(m,q);forward_total+=n
                        target_high=w(v);hi_piece=got[:6] if orientation=='HIGH_FIRST' else got[6:12]
                        rows.append({'seed':seed,'arm':arm,'domain':domain,'high_id':v,'low_id':s,
                            'orientation':orientation,'Q':q,'expected':truth,'actual':got,'cause':why,'forward_calls':n,
                            'exact':got==truth,'first_word_exact':got[:6]==w(a),'second_word_exact':got[6:12]==w(b),
                            'high_word_exact':hi_piece==target_high,'stop_at_expected':got.endswith('S') and len(got)==13,
                            'high_bit16_expected':target_high[0], 'high_bit16_generated':hi_piece[0] if len(hi_piece)>=1 else None})
    assert len(rows)==1296 and len(keys)==1296
    assert all(sum(1 for x in rows if x['seed']==s and x['arm']==a and x['domain']==d)==108 for s,a,_,_ in models for d in ('seen_values','unseen_values'))
    stats=[]
    for seed,arm,_,h in models:
      for domain in ('seen_values','unseen_values'):
        for orient in ('HIGH_FIRST','HIGH_SECOND'):
          for subset in ('all_s0_to_s5','primary_s5'):
            xs=[x for x in rows if x['seed']==seed and x['arm']==arm and x['domain']==domain and x['orientation']==orient and (subset=='all_s0_to_s5' or x['low_id']==5)]
            stats.append({'seed':seed,'arm':arm,'checkpoint_sha256':h,'domain':domain,'orientation':orient,
                'subset':subset,'n':len(xs),'exact':sum(x['exact'] for x in xs),'high_word_exact':sum(x['high_word_exact'] for x in xs),
                'stop_at_expected':sum(x['stop_at_expected'] for x in xs),'nonstop_cap':sum(x['cause']!='stop' for x in xs),
                'high_bit16_pred_ones':sum(x['high_bit16_generated']=='1' for x in xs)})
    report={'prereg_git_commit':PRE,'source_pr36_sha':'0b4a39342ee4ef00a0775ece7a2c20a1dfa08b25',
        'source_pr37_sha':'6a2162a687dc05b68034b2d00c287584a463f545',
        'source_code_sha256':SHA_SRC,'new_optimizer_updates':0,'checkpoints':6,'parameters_each':10499,
        'archived_replay_cases':all_replay,'archived_replay_forward':replay_calls,
        'new_case_count':len(rows),'new_forward':forward_total,'MAC_per_forward':10432,
        'new_dense_forward_MAC':forward_total*10432,'replay_dense_forward_MAC':replay_calls*10432,
        'stats':stats,'failed_examples':[x for x in rows if not x['exact']][:12]}
    payload=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows)
    (HERE/'raw_cases.jsonl').write_text(payload)
    report['raw_sha256']=H(payload.encode())
    (HERE/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('TEST',len(rows),'new cases',forward_total,'forward',forward_total*10432,'MAC')
    for t in stats:
        if t['subset']=='primary_s5': print(t['seed'],t['arm'],t['domain'],t['orientation'],t['exact'],'/',t['n'])
    print('RAW_SHA',report['raw_sha256'])
if __name__=='__main__':main()
