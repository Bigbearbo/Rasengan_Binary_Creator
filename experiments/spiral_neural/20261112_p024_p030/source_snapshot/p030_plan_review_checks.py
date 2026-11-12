"""Read-only design arithmetic/weight-growth controls; no neural training."""
import sys
sys.dont_write_bytecode=True
import hashlib,json
from pathlib import Path
import numpy as np

WORK=Path('D:/Codex用/work/sle-research-review/plan-review-ad6281c')

def main():
    identities=0
    for n in range(1,8):
        for value in range(2**n):
            before=format(value,f'0{n}b')+'0';after=format(value,f'0{n+1}b')+'0'
            assert after=='0'+before and int(after[:-1],2)==value
            identities+=1
    # Grow onehot input positions L->L+1 and hidden H->H+1. Copy old
    # parameter blocks and zero outgoing weights from the new hidden unit.
    rng=np.random.default_rng(30);L,H=8,64
    W=rng.normal(0,.1,(2*L,H));b=rng.normal(0,.1,H)
    V=rng.normal(0,.1,(H,3));a=rng.normal(0,.1,3)
    WW=rng.normal(0,.1,(2*(L+1),H+1));bb=rng.normal(0,.1,H+1)
    VV=np.zeros((H+1,3));WW[:2*L,:H]=W;bb[:H]=b;VV[:H]=V
    maximum=0.
    for length in range(1,L+1):
        slots=np.zeros((L,2));slots[np.arange(length),rng.integers(0,2,length)]=1
        x=slots.reshape(1,-1);xx=np.concatenate([x,np.zeros((1,2))],axis=1)
        old=np.tanh(x@W+b)@V+a;new=np.tanh(xx@WW+bb)@VV+a
        maximum=max(maximum,float(np.max(abs(old-new))))
        assert np.allclose(old,new,atol=1e-12,rtol=0)
    lengths=[{'example':'Q1/Q2','Q':6,'max_answer_prefix':2},
             {'example':'Q3','Q':7,'max_answer_prefix':3},
             {'example':'op2 unary before END','Q':8,'max_answer_prefix':3},
             {'example':'Q6 END enabled','Q':11,'max_answer_prefix':3},
             {'example':'op3 unary with4bitdata andEND','Q':14,'max_answer_prefix':4},
             {'example':'op3 binary with4bitdata andEND','Q':18,'max_answer_prefix':4},
             {'example':'two-layer Zero example','Q':23,'max_answer_prefix':4}]
    for row in lengths:row['context']=row['Q']+row['max_answer_prefix'];assert row['context']<=32
    result={'training_run':False,'numeric_ID_low_bits_preservation_cases':identities,
            'input_symbols':['0','1'],'output_symbols':['0','1','STOP'],
            'no_separator_context_lengths':lengths,
            'candidate_dynamic_MLP_arithmetic':{'L8_H64':(2*8+1)*64+(64+1)*3,'L32_H88':(2*32+1)*88+(88+1)*3},
            'same_old_prefix_growth_test_max_logit_error':maximum,
            'growth_test_limit':'Tests only the identical old prefix padded into larger shape; NOT the changed raw stream after inserting high bits, and NOT a trained capacity comparison.',
            'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (WORK/'source').rglob('*.md')}}
    (WORK/'review-compact.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':main()
