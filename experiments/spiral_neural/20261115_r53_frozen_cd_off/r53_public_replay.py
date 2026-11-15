"""R53 public paired neural replay: run beside extracted R52+R53 ZIP.
Requires torch, numpy, and local R52 ZIP (hash named in PREINFERENCE_FREEZE).
No training, no answer oracle for student generation.
"""
import collections, hashlib, json
from pathlib import Path
import torch
from torch.nn import functional as F
import r52_learned_cursor_gate as r52
P=Path(__file__).resolve().parent
SEEDS=(101,202,303)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class FirstWordCDOff(r52.LearnedCursorGate):
    def forward(self,x):
        z=x.reshape(-1,80,2);q=z[:,9:33,:].reshape(-1,4,12)
        cursor=z.sum(-1).sum(-1).long()-39
        first=(cursor>=0)&(cursor<6)
        second=(cursor>=6)&(cursor<12)&(z[:,6,1]>0.5)
        gates=torch.sigmoid(self.gate_logits)
        first_gate=gates[0]*torch.tensor([1.,1.,0.,0.],dtype=x.dtype,device=x.device)
        mask=torch.where(first[:,None],first_gate[None,:].expand(len(x),-1),
              torch.where(second[:,None],gates[1][None,:].expand(len(x),-1),
                torch.ones_like(gates[0][None,:]).expand(len(x),-1)))
        emb=torch.tanh(self.base.enc(q*mask[:,:,None]))
        pos=F.one_hot(cursor.clamp(0,32),num_classes=33).to(x.dtype)
        feat=torch.cat([emb.reshape(-1,64),z[:,5:9,:].reshape(-1,8),pos],dim=-1)
        return self.base.out(torch.tanh(self.base.hidden(feat)))
@torch.no_grad()
def main():
    pre=json.loads((P/'r53_prereg.json').read_text())
    assert sha(P/'r52_outputs/raw_results.jsonl')==pre['r52_raw_sha256']
    assert sha(P/'r52_outputs/results.json')==pre['r52_summary_sha256']
    ref,m,_,items,_,_,_=r52.materials()
    old={(x['seed'],x['Q']):x for x in map(json.loads,(P/'r52_outputs/raw_results.jsonl').read_text().splitlines())}
    recorded={(x['seed'],x['Q']):x for x in map(json.loads,(P/'r53_outputs/raw_results.jsonl').read_text().splitlines())}
    assert len(old)==len(recorded)==816 and len(items)==272
    summary=collections.defaultdict(lambda:collections.Counter())
    for seed in SEEDS:
        backbone=m.load_weights(P/f'r50_outputs/weights_{seed}_dual.json',r52.r50.ScaffoldRelease(ref))
        backbone.only_b=False
        net=FirstWordCDOff(backbone).eval()
        g=json.loads((P/f'r52_outputs/gate_{seed}.json').read_text())
        net.gate_logits.data[:]=torch.tensor(g['gate_logits'],dtype=torch.float32)
        for item in items:
            q=item['Q'];exp=item['expected'];y,c,n=ref.free(net,q)
            row=recorded[(seed,q)];before=old[(seed,q)]
            assert (y,c,n)==(row['actual'],row['cause'],row['forwards'])
            assert row['r52_actual']==before['actual'] and y==row['actual']
            group=row['bucket'];t=summary[group]
            t['Q']+=1;t['first']+=y[:6]==exp[:6];t['full']+=y==exp
            t['baseline_full']+=before['actual']==exp
        print('replayed seed',seed)
    for group,v in summary.items():print(group,dict(v))
    assert {k:v['full'] for k,v in summary.items()}=={'retention':150,'legacy':35,'fresh':76}
    print('R53 PUBLIC PAIRED REPLAY PASS: 816/816')
if __name__=='__main__':main()
