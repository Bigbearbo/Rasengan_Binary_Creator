"""Independently verify AE1 d-bit probe bundle. Usage: python verify_public_zip.py <archive.zip>."""
import base64, hashlib, json, sys, zipfile
import numpy as np
ARCHIVE='de9faa95e2ba8d178b0a52712a6aa0259894a04147d4894eab407b270ef48e4d'
PREFIX='sle_ae1_d_intervention_20261113/'
def sha(b):return hashlib.sha256(b).hexdigest()
def main(path):
    assert sha(open(path,'rb').read())==ARCHIVE,'archive SHA mismatch'
    with zipfile.ZipFile(path) as z:
        read=lambda name:z.read(PREFIX+name)
        manifest=read('SHA256SUMS').decode().splitlines()
        for line in manifest:
            digest,name=line.split('  ',1)
            assert sha(read(name))==digest,(name,'digest')
        spec=json.loads(read('PREREGISTRATION.json'))
        assert sha(read('probe_d.py'))==spec['runner_sha256']
        assert sha(read('verify_d_numpy.py'))==spec['independent_verifier_sha256']
        report=json.loads(read('RESULTS.json'))
        raw=read('raw_cases_d.jsonl')
        assert sha(raw)==report['raw_sha256']
        rows=[json.loads(s) for s in raw.decode().splitlines()]
        weights={}
        for seed in (101,202):
            for arm in ('frozen_c1_control','balanced_c'):
                tag='conjunction' if arm=='frozen_c1_control' else 'balanced_c'
                b=read(f'checkpoints/weights_seed{seed}_{tag}.json')
                assert sha(b)==spec['checkpoint_sha256'][f'{seed}_{arm}']
                data=json.loads(b); vals={}
                for key,v in data['tensors'].items():
                    vals[key]=np.frombuffer(base64.b64decode(v['little_endian_base64']),'<f4').copy().reshape(v['shape'])
                weights[seed,arm]=tuple(vals[k] for k in ('0.weight','0.bias','2.weight','2.bias'))
        total=0; seen=set(); d0={}
        for zrow in rows:
            seed,arm,a,b,c,d=(zrow[k] for k in ('seed','arm','a','b','c','d'))
            assert a in (4,5) and b in (26,27) and c in (2,3) and d in (0,1,2,4,8,16)
            key=(seed,arm,a,b,c,d)
            assert key not in seen;seen.add(key)
            q='010100100'+''.join(f'{v:05b}0' for v in (a,b,c,d))+'111100'
            target=f'{a:05b}0{b:05b}0S'
            assert len(q)==39 and q==zrow['Q'] and target==zrow['expected']
            w1,b1,w2,b2=weights[seed,arm]
            output=''; why='cap'
            for i in range(32):
                if len(q+output)>80:why='overflow';break
                x=np.zeros(160,np.float32)
                for j,bit in enumerate(q+output):x[j*2+int(bit)]=1.0
                h=np.tanh(w1@x+b1).astype(np.float32)
                output+='01S'[int(np.argmax(w2@h+b2))];total+=1
                if output.endswith('S'):why='stop';break
            assert (output,why,i+1)==(zrow['actual'],zrow['cause'],zrow['forward_calls'])
            if d==0:d0[seed,arm,a,b,c]=output
        assert len(rows)==len(seen)==192 and total==report['inference_forward_calls']==2496
        assert all(zrow['actual']==d0[zrow['seed'],zrow['arm'],zrow['a'],zrow['b'],zrow['c']] for zrow in rows)
        assert report['primary_gate_pass'] is True
        print('ZIP VERIFIED: 192/192 F32 neural answers, 2496 forwards, full source + checkpoint SHA, all d mutations invariant')
if __name__=='__main__':main(sys.argv[1])
