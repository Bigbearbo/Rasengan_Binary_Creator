"""R24 independent fixed-checkpoint NumPy reproduction.
Usage: python r24_repro_numpy.py --r23 <R23.zip> --manifest manifest.jsonl
Optionally provide --raw raw_results.jsonl from R24 evidence ZIP to verify exact outputs.
"""
import argparse, base64, collections, importlib.util, json, tempfile, zipfile
from pathlib import Path
import numpy as np

def word(n): return f'{n:05b}0'
def encode(r,a,b,c,d):return '01'+'010'+f'{r:03b}0'+''.join(map(word,(a,b,c,d)))+'111100'

def main():
 p=argparse.ArgumentParser();p.add_argument('--r23',required=True);p.add_argument('--manifest',required=True);p.add_argument('--raw');a=p.parse_args()
 cases=[json.loads(s) for s in Path(a.manifest).read_text().splitlines()]
 assert len(cases)==80 and len({x['Q'] for x in cases})==80
 assert collections.Counter(x['split'] for x in cases)=={'calibration':32,'test':48}
 assert all(x['Q']==encode(x['r'],x['a'],x['b'],x['c'],x['d']) and x['expected']==word(x['a'])+'S' for x in cases)
 with zipfile.ZipFile(a.r23) as z:
  with tempfile.TemporaryDirectory() as tmp:
   py=Path(tmp)/'np_verify.py';py.write_bytes(z.read('r23_experiment/verify_numpy.py'))
   spec=importlib.util.spec_from_file_location('r23_numpy',py)
   m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   weights={}
   for seed in (101,202,303):
    for arm,prefix in (('R20_original','outputs_r20'),('R23_c2_lesson','r23_outputs')):
     rec=json.loads(z.read(f'{prefix}/weights_{seed}_dual.json'))
     weights[seed,arm]={k:np.frombuffer(base64.b64decode(v['little_endian_base64']),dtype='<f4').copy().reshape(v['shape']) for k,v in rec['tensors'].items()}
  saved={(v['seed'],v['arm'],v['Q']):v for v in map(json.loads,Path(a.raw).read_text().splitlines())} if a.raw else None
  acc=collections.defaultdict(list);nfw=0;matches=0;maxdiff=0.
  for seed in (101,202,303):
   for arm in ('R20_original','R23_c2_lesson'):
    w=weights[seed,arm]
    for x in cases:
     ans,cause,n=m.generate(x['Q'],w)
     logits=m.logits(x['Q'],x['expected'][:6],w)
     margin=float(logits[2]-max(logits[0],logits[1]))
     stop=bool(logits.argmax()==2)
     acc[seed,arm,x['split'],x['c']].append((stop,ans==x['expected'],margin))
     nfw+=n+1
     if saved is not None:
      y=saved[seed,arm,x['Q']]
      assert (ans,cause,n,stop)==(y['actual'],y['cause'],y['greedy_forwards'],y['STOP_correct'])
      diff=float(np.max(np.abs(logits-np.array(y['STOP_logits']))));assert diff<5e-5
      maxdiff=max(maxdiff,diff);matches+=1
  for seed in (101,202,303):
   for arm in ('R20_original','R23_c2_lesson'):
    for c in (0,2):
     rows=acc[seed,arm,'test',c]
     print(seed,arm,'c='+str(c),'STOP',sum(t[0] for t in rows),'/24','full',sum(t[1] for t in rows),'/24','mean_margin',round(float(np.mean([t[2] for t in rows])),5))
  print('INDEPENDENT NUMPY DONE',nfw,'forwards',nfw*10920,'MAC',matches,'raw matches; max logits error',maxdiff)

if __name__=='__main__':main()
