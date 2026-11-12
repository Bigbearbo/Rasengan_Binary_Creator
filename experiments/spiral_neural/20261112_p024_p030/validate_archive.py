"""Offline integrity, publication screening and checkpoint inference validation."""
import sys
sys.dont_write_bytecode=True
import argparse,ast,gzip,hashlib,importlib,json,re
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'src'))

def read_json(path):
    if path.exists():return json.loads(path.read_text(encoding='utf-8-sig'))
    return json.loads(gzip.decompress(Path(str(path)+'.gz').read_bytes()))

def compact(name):return read_json(HERE/'evidence'/name/'compact.json')

def same(a,b):
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(same(v,b[k]) for k,v in a.items())
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return isinstance(b,(int,float)) and bool(np.isclose(a,b,rtol=1e-10,atol=1e-10,equal_nan=True))
    return a==b

def integrity():
    manifest=read_json(HERE/'artifact-manifest.json');verified=0;npz_count=0
    for row in manifest['files']:
        path=(HERE/row['path']).resolve();assert path.is_relative_to(HERE)
        data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256'],row['path'];verified+=1
    high_confidence_secrets=[re.compile(rb'sk-or-v1-[a-fA-F0-9]{40,}'),re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),
                             re.compile(rb'github_pat_[A-Za-z0-9_]{50,}'),re.compile(rb'[0-9]{8,12}:[A-Za-z0-9_-]{30,}'),
                             re.compile(rb'AIza[A-Za-z0-9_-]{30,}')]
    user_segment=rb'(?:[A-Za-z0-9_.-]|[\x80-\xff])+'
    machine_paths=re.compile(rb'(?:[A-Za-z]:[/\\]+Users[/\\]+'+user_segment+rb'|/home/'+user_segment+rb'|/Users/'+user_segment+rb'|[A-Za-z]:[/\\]+Windows[/\\]+Fonts)',re.I)
    for path in HERE.rglob('*'):
        if not path.is_file():continue
        assert not any(p.lower() in {'secrets','telegram-bridge','telegram-nvidia','.env'} for p in path.relative_to(HERE).parts)
        assert not any('cache' in p.lower() for p in path.relative_to(HERE).parts),'Cache is not a research artifact'
        data=path.read_bytes()
        if path.suffix=='.gz':data=gzip.decompress(data)
        if path.suffix=='.npz':
            with np.load(path,allow_pickle=False) as z:
                for key in z.files:
                    a=z[key];assert a.dtype.kind!='O'
                    if a.dtype.kind in 'fc':assert np.all(np.isfinite(a))
                    if a.dtype.kind in 'US':assert not machine_paths.search(str(a).encode('utf-8'))
            npz_count+=1
        elif path.suffix=='.png':
            assert not machine_paths.search(data),'Machine metadata in PNG'
        else:
            assert not any(pattern.search(data) for pattern in high_confidence_secrets),str(path.relative_to(HERE))
            assert not machine_paths.search(data),'Machine-home/font metadata in '+str(path.relative_to(HERE))
            if path.suffix=='.py':ast.parse(data.decode('utf-8-sig'))
    return {'manifest_files_verified':verified,'finite_nonpickle_checkpoints':npz_count,'high_confidence_secret_scan':'passed',
            'cache_path_exclusion':'passed','machine_home_and_font_path_scan':'passed','python_parse':'passed'}

def legacy_load(cls,seed,path):
    net=cls(seed)
    with np.load(path,allow_pickle=False) as z:
        net.p=[z[f'p{i}'].copy() for i in range(4)]
        for label in ['m','v']:
            if f'{label}0' in z:setattr(net,label,[z[f'{label}{i}'].copy() for i in range(4)])
        if 'hidden' in z:net.hidden=z['hidden'].copy()
        if 'steps' in z:net.steps=int(z['steps'])
        if 'baseline' in z:net.baseline=float(z['baseline'])
    return net

def checkpoint_checks():
    p24=importlib.import_module('echo_serial_stop');p25=importlib.import_module('echo_prefix_separator')
    direct=importlib.import_module('echo_prefix_direct');p26=importlib.import_module('echo_bit_feedback')
    p27=importlib.import_module('echo_teaching_comparison');p28=importlib.import_module('echo_learning_time')
    p29=importlib.import_module('echo_monotonic_curriculum');p30=importlib.import_module('p030_binary_continual')
    rows,train,test=p24.x.material();checks=[]
    # Compare the published dataset with the independent rank oracle.
    for value,(q,a) in rows.items():assert p29.encode(8,value)==(q,a)
    for r in compact('echo-serial-stop-20261112')['runs']:
        cls=p24.Serial if r['serial'] else p24.x.Policy
        net=legacy_load(cls,r['seed'],HERE/'evidence/echo-serial-stop-20261112'/r['name']/'state.npz')
        for values,key in [(train,'train_probe'),(test,'heldout_probe')]:
            actual=p24.evaluate(net,values,rows,r['serial']);actual.pop('records');assert same(actual,r[key])
        checks.append('P024/'+r['name'])
    for name,cls in [('echo-prefix-separator-20261112',p25.Prefix),('echo-prefix-direct-20261112',direct.Direct)]:
        for r in compact(name)['runs']:
            net=legacy_load(cls,r['seed'],HERE/'evidence'/name/f"seed{r['seed']}"/'state.npz')
            for values,key in [(train,'train_probe'),(test,'heldout_probe')]:
                actual=p25.evaluate(net,values,rows);actual.pop('records');assert same(actual,r[key])
            checks.append(name+'/'+str(r['seed']))
    for r in compact('echo-bit-feedback-20261112')['runs']:
        net=legacy_load(p26.Immediate,r['seed'],HERE/'evidence/echo-bit-feedback-20261112'/f"seed{r['seed']}"/'state.npz')
        for values,key in [(train,'train_probe'),(test,'heldout_probe')]:
            actual=p25.evaluate(net,values,rows);actual.pop('records');assert same(actual,r[key])
        checks.append('P026/'+str(r['seed']))
    for r in compact('echo-teaching-comparison-20261112')['runs']:
        cls=p27.Supervised if r['arm']=='ce_shuffle' else p27.Reward
        folder=HERE/'evidence/echo-teaching-comparison-20261112'/f"{r['arm']}-{r['seed']}"
        for filename,expected in [('state.npz',r['probes']),('equal-update-100000.npz',r['at_equal_100000_updates'])]:
            net=legacy_load(cls,r['seed'],folder/filename)
            for values,key in [(train,'train'),(test,'heldout')]:assert same(p27.trim(p27.evaluate(net,values,rows)),expected[key])
            checks.append('P027/'+folder.name+'/'+filename)
    for r in compact('echo-learning-time-20261112')['runs']:
        cls=p27.Supervised if r['arm']=='ce_shuffle' else p27.Reward
        folder=HERE/'evidence/echo-learning-time-20261112'/f"{r['arm']}-{r['seed']}"
        net=legacy_load(cls,r['seed'],folder/'state.npz')
        for values,key in [(train,'train'),(test,'heldout')]:assert same(p27.trim(p27.evaluate(net,values,rows)),r[key])
        checks.append('P028/'+folder.name)
    data=p29.dataset()
    for r in compact('echo-monotonic-ranks-20261112')['runs']:
        for s in r['stages']:
            n=s['n'];folder=HERE/'evidence/echo-monotonic-ranks-20261112'/f"{r['arm']}-{r['seed']}"/f'n{n}'
            net=legacy_load(p29.Net,r['seed'],folder/'state.npz')
            curve=read_json(folder/'curve.json');actual=p29.slim(p29.evaluate(net,n,data[n]['val'],data[n]['rows']))
            assert same(actual,curve[-1]['validation'])
            if n>=5:assert same(p29.slim(p29.evaluate(net,n,data[n]['test'],data[n]['rows'])),s['final_test'])
            checks.append('P029/'+folder.parent.name+f'/n{n}')
    def load30(path,seed):
        with np.load(path,allow_pickle=False) as z:
            net=p30.Model(seed,int(z['L']),int(z['H']))
            for label in ['p','m','v','birth']:setattr(net,label,[z[f'{label}{i}'].copy() for i in range(4)])
            net.t=int(z['t']);net.growth_rng.bit_generator.state=json.loads(str(z['growth_rng']))
        return net
    c30=compact('p030-binary-continual-20261112')
    stages=[]
    for r in c30['runs']:
        for s in r['stages']:stages.append((r['run'],r['seed'],s))
    for r in c30['scratch_controls']:stages.append((f"scratch_{r['profile']}-{r['seed']}",r['seed'],r['stage']))
    for name,seed,s in stages:
        p=p30.REGISTRY[s['profile']['name']];folder=HERE/'evidence/p030-binary-continual-20261112'/name/p.name
        net=load30(folder/'state.npz',seed);tr,va,te=p30.split(p)
        for values,key in [(tr,'train'),(va,'validation')]:assert same(p30.small(p30.metrics(net,p,values)),s['train_validation'][key])
        if te:assert same(p30.small(p30.metrics(net,p,te)),s['final_test'])
        checks.append('P030/'+name+'/'+p.name)
    # Real current checks for the relocated runtime and new boundary paths.
    contracts={'P027_CE_and_reward':p27.checks(),'P028_stopping':p28.checks(),'P029_oracle':p29.checks(data),'P030_binary_growth':p30.checks()}
    return {'checkpoint_metric_checks':len(checks),'checkpoints':checks,'current_contracts':contracts,
            'dataset_equivalence':'256 P021 rows equal independent n8 oracle','full_retraining_performed':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest-only',action='store_true');p.add_argument('--output',type=Path);args=p.parse_args()
    result={'status':'passed','integrity':integrity(),'numpy':np.__version__}
    if not args.manifest_only:result['inference_and_contracts']=checkpoint_checks()
    if args.output:
        path=args.output.resolve()
        if path.is_relative_to(HERE):raise ValueError('Validation output must not mutate immutable archived evidence')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'integrity':result['integrity'],
                      'checkpoint_metric_checks':result.get('inference_and_contracts',{}).get('checkpoint_metric_checks')},ensure_ascii=True))

if __name__=='__main__':main()
