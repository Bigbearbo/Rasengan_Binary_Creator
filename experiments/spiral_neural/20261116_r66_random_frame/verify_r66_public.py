"""Read-only R66 companion ZIP verifier. Python 3 + NumPy. Never trains.
Usage: python verify_r66_public.py sle_ae1_r66_balanced_random_frame_20261116.zip
"""
import io,json,hashlib,sys,zipfile
from pathlib import Path
import numpy as np
PREFIX='r66_work/'
def h(b):return hashlib.sha256(b).hexdigest()
def check(path):
 with zipfile.ZipFile(path) as arc:
  assert arc.testzip() is None
  names=set(arc.namelist())
  def get(p):return arc.read(PREFIX+p)
  ledger=json.loads(get('R66_SHA256SUMS.json'))
  for k,v in ledger.items():
   assert h(get(k))==v,(k,'SHA mismatch')
  assert len(ledger)>=20
  pre=json.loads(get('r66_prereg.json'))
  assert h(get('r66_shuffled_aux.py'))==pre['runner_sha256']
  assert h(get('r66_flips.json'))==pre['flips_sha256']
  assert h(get('r64_reference/r64_manifest.jsonl'))==pre['r64_manifest_sha256']
  assert h(get('r64_reference/r64_joint_frame_math.py'))==pre['r64_runner_sha256']
  assert h(get('r64_reference/r64_outputs/raw_predictions.jsonl'))==pre['r64_predictions_sha256']
  flips=json.loads(get('r66_flips.json'))['flipped']
  assert len(flips)==128 and len(set(flips))==128
  rows=[json.loads(v) for v in get('r64_reference/r64_manifest.jsonl').decode().splitlines()]
  assert len(rows)==1472
  legal=lambda r: r['kind']=='valid'
  for r in rows:
   v=r['raw_bits']; assert len(v)==39 and set(v)<=set('01')
   assert v.startswith({'valid':'01','bad_00':'00','bad_11':'11','bad_10_unseen':'10'}[r['kind']])
   w=lambda n:f'{n:05b}0'
   q='01'+'010'+f'{r["r"]:03b}'+'0'+''.join(w(r[k]) for k in 'abcd')+'111100'
   assert v[2:]==q[2:]
   assert r['math_gold']==(w(r['a'])+(w(r['b']) if r['r']==2 else '')+'S' if legal(r) else None)
  tr=[r for r in rows if r['split']=='train']
  assert len(tr)==1024 and all(r['kind']!='bad_10_unseen' for r in tr)
  for i in range(256):
   rs=[r for r in tr if r['base']==f'train-{i:03d}']
   assert len(rs)==4
   assert sum(int(legal(r))^int(r['base'] in flips) for r in rs)==2
  gold=[r for r in rows if r['split']!='train']; assert len(gold)==448
  records=[json.loads(v) for v in get('r66_outputs/raw_predictions.jsonl').decode().splitlines()]
  old=[json.loads(v) for v in get('r64_reference/r64_outputs/raw_predictions.jsonl').decode().splitlines()]
  assert len(records)==1344 and len(old)==2688
  old_index={(z['seed'],z['arm'],z['id']):z for z in old}
  per=[];maxerr=0;changes=[]
  X=np.array([[int(bit)*2-1 for bit in r['raw_bits']] for r in gold],dtype=np.float32)
  for seed in [101,202,303]:
   sub=[r for r in records if r['seed']==seed]
   assert [r['id'] for r in sub]==[r['id'] for r in gold]
   with np.load(io.BytesIO(get(f'r66_outputs/model_{seed}_shuffled.npz'))) as ws:
    w={k:ws[k] for k in ws.files}
   hidden=np.tanh(X@w['enc.weight'].T+w['enc.bias'])
   scores=(hidden@w['math.weight'].T+w['math.bias']).reshape(-1,13,3)
   frame=hidden@w['frame.weight'].T+w['frame.bias']
   maxerr=max(maxerr,float(np.max(np.abs(frame.ravel()-np.array([r['frame_logit'] for r in sub])))))
   assert maxerr<1e-4
   for r,z in zip(sub,scores.argmax(-1)):
    answer=''
    for t in z:
     answer+='01S'[int(t)]
     if t==2:break
    assert answer==r['math_pred']
    assert (r['math_exact']==(answer==r['math_gold'])) if r['math_gold'] else r['math_exact'] is None
    assert r['frame_pred']==int(r['frame_logit']>=0)
   tested=[z for z in sub if z['split']=='test'];lg=[z for z in tested if z['kind']=='valid'];iv=[z for z in tested if z['kind']!='valid']
   per.append({'seed':seed,'exact':sum(z['math_exact'] for z in lg),'stop':sum(z['stop_pos_correct'] for z in lg),'valid_accept':sum(z['frame_pred'] for z in lg),'invalid_reject':sum(not z['frame_pred'] for z in iv)})
   for z in lg:
    oldz=old_index[(seed,'joint_lambda1',z['id'])]
    if oldz['math_exact']!=z['math_exact']: changes.append((seed,z['id'],bool(oldz['math_exact'])))
  saved=json.loads(get('r66_outputs/results.json'))
  assert per==[{k:v for k,v in z.items() if k in per[0]} for z in saved['per_seed']]
  assert sum(z['exact'] for z in per)==saved['math_exact']==73
  assert sum(z['valid_accept']+z['invalid_reject'] for z in per)==saved['frame_accuracy']==297
  assert len(changes)==saved['paired_changes']==100
  assert sum(x[2] for x in changes)==saved['true_joint_wins']==96
  assert sum(z['stop'] for z in per)==189
  assert saved['numpy_replay']==1344 and all(saved['gates'].values())
  print('PASS ZIP SHA',len(ledger),'NumPy full NN replay',len(records),'math',saved['math_exact'],'R64 truthful',saved['true_joint_exact'],'R64 math-only',saved['math_only_exact'],'frame',saved['frame_accuracy'],'/768','maxerr',maxerr)
if __name__=='__main__':
 if len(sys.argv)!=2:raise SystemExit('usage: verify_r66_public.py <companion.zip>')
 check(Path(sys.argv[1]))
