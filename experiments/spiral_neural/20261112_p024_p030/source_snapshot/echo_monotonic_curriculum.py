"""P029 / upstream P028A+B: monotonic data-rank curriculum, no old-rank probes."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import csv,hashlib,importlib.util,json,time
from pathlib import Path
import numpy as np
import echo_teaching_comparison as base

ROOT=Path('D:/Codex用')
OUT=ROOT/'work/sle-research-review/echo-monotonic-ranks-20261112'
SOURCE=ROOT/'work/sle-research-review/rank-source-55d1037/source'
PROFILE='paper4_echo_op1_dataN_v1'
CAPS=[500,500,750,1000,1500,2000,3000,5000]
POINTS=[0,1,2,4,8,16,25,50,75,100,128,192,256,384,512,768,1000,2000,5000]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result);return result

parser=module('rank_parser',SOURCE/'experiments/spiral_parser/spiral_parser.py')

def encode(n,value):
    if not 1<=n<=8 or not 0<=value<2**n:raise ValueError('Rank/value out of scope')
    data=format(value,f'0{n}b')+'0';return '0100'+data,data

def parse(profile,n,bits):
    if profile!=PROFILE or not 1<=n<=8:raise ValueError('Unknown profile/rank')
    if len(bits)!=n+5 or not bits.startswith('0100'):raise ValueError('Wrong profile shape')
    op=parser.tokenize(bits,1,1,2);data=parser.tokenize(bits,n,1,4)
    if op['value']!=0 or data['end']!=len(bits):raise ValueError('Wrong operator/trailing bits')
    return data['value'],data['word']

def dataset():
    result={}
    for n in range(1,9):
        rows={value:encode(n,value) for value in range(2**n)}
        if n<=4:train=list(rows);val=train.copy();test=[];swap=None
        else:
            values=np.random.default_rng(29000+n).permutation(2**n).tolist();cut=3*2**n//4
            swap=None
            if 1 not in values[:cut]:
                i=values.index(1);swap=[values[0],1];values[0],values[i]=values[i],values[0]
            train=sorted(values[:cut]);val=sorted(values[cut:cut+2**n//8]);test=sorted(values[cut+2**n//8:])
        result[n]={'rows':rows,'train':train,'val':val,'test':test,'promotion_train_swap':swap}
    return result

class Net(base.Supervised):
    def __init__(self,seed):
        super().__init__(seed);self.active_n=None;self.anchors={}
    def one_target(self,text,target):
        prediction=super().one_target(text,target)
        if self.active_n==8 and self.steps%1000==0:self.anchors[self.steps]=base.snapshot(self)
        return prediction

def evaluate(net,n,values,rows):
    saved=base.snapshot(net);bit_counts=np.zeros(n+1,dtype=int);correct=stops=teacher=targets=0;loss=0.;records=[];calls=0
    for value in values:
        question,expected=rows[value];tokens=net.predict(question);calls+=len(tokens)
        stopped=tokens.endswith('S');answer=tokens[:-1] if stopped else tokens
        good=[i<len(answer) and answer[i]==b for i,b in enumerate(expected)];bit_counts+=good
        whole=tokens==expected+'S';timing=stopped and len(answer)==n+1
        correct+=whole;stops+=timing;tf=''
        for pos,target in enumerate(expected+'S'):
            h,_=net.read(question+'|'+expected[:pos]);z=(h@net.p[2]+net.p[3])[0].astype(np.float64)
            lp=z-np.logaddexp.reduce(z);index='01S'.index(target);pred='01S'[int(z.argmax())]
            tf+=pred;teacher+=pred==target;targets+=1;loss-=lp[index];calls+=1
        records.append([value,tokens,whole,timing,tf])
    assert all(np.array_equal(v,base.snapshot(net)[k]) for k,v in saved.items())
    return {'n':n,'total':len(values),'whole_correct':int(correct),'stop_correct':int(stops),
            'bit_correct_by_position':bit_counts.tolist(),'bit_accuracy':float(bit_counts.sum()/((n+1)*len(values))) if values else None,
            'teacher_correct':int(teacher),'teacher_targets':targets,'ce_mean':loss/targets if targets else None,
            'inference_calls':calls,'records':records}

def slim(p):return {k:v for k,v in p.items() if k!='records'}

def passed(n,metric):
    threshold=metric['total'] if n<=4 else int(np.ceil(.95*metric['total']))
    return metric['whole_correct']>=threshold and metric['stop_correct']>=threshold

def make_order(rng,values,n,first):
    order=rng.permutation(values).tolist()
    if first:
        value=0 if n==1 else 1
        order.remove(value);order.insert(0,value)
    return order

def checks(data):
    count=0
    for n,d in data.items():
        assert len(d['rows'])==2**n
        if n>=5:
            a,b,c=map(set,[d['train'],d['val'],d['test']])
            assert not(a&b or a&c or b&c) and a|b|c==set(d['rows']) and 1 in a
        for value,(q,a) in d['rows'].items():
            v,answer=parse(PROFILE,n,q);assert (v,answer)==(value,a) and encode(n,v)==(q,a)
            assert len(q)==n+5 and len(a)==n+1 and a.endswith('0') and len(q+'|'+a)==2*n+7<=23
            for pos,target in enumerate(a+'S'):
                assert (q+'|'+a[:pos]).split('|')==[q,a[:pos]]
                assert target==('S' if pos==len(a) else a[pos])
            count+=1
        if n>1:
            _,a=encode(n,1);assert a[n-1]=='1' and a[n:]=='0'
    fixtures=[(1,0,'010000','00'),(1,1,'010010','10'),(2,1,'0100010','010'),(2,2,'0100100','100'),(3,5,'01001010','1010')]
    for n,v,q,a in fixtures:assert encode(n,v)==(q,a) and parse(PROFILE,n,q)==(v,a)
    # Independent one-layer op2 profile, not an input to the main model.
    q='01'+'010'+'100';op=parser.tokenize(q,2,1,2);d=parser.tokenize(q,2,1,5)
    assert op['value']==1 and d['word']=='100'
    neg=''.join('1' if b=='0' else '0' for b in d['word'][:-1])+'0';assert neg=='010'
    rejected=0
    for profile,n,q in [('unknown',1,'010000'),(PROFILE,1,'010001'),(PROFILE,1,'0100000'),(PROFILE,2,'010000')]:
        try:parse(profile,n,q)
        except ValueError:rejected+=1
        else:raise AssertionError('Invalid profile/word accepted')
    rng=np.random.default_rng(9)
    for n,d in data.items():
        order=make_order(rng,d['train'],n,True)
        assert len(order)==len(set(order))==len(d['train']) and order[0]==(0 if n==1 else 1)
    net=Net(101)
    for n in range(1,9):
        for v in [0,2**n-1]:
            q,a=encode(n,v);net.read(q+'|'+a)
    # Stop at the largest supported prefix; distinguish STOP from syntax tail0.
    net.p[2][:]=0;net.p[3][:]=[0,0,50];assert net.predict(encode(8,0)[0])=='S'
    net.p[3][:]=[50,0,0];assert net.predict(encode(8,0)[0])=='0'*10
    m={'total':32,'whole_correct':30,'stop_correct':32};assert not passed(8,m)
    m['whole_correct']=31;assert passed(8,m)
    return {'oracle_roundtrips':count,'paper_fixtures':fixtures,'neg_profile_fixture':[q for q in ['01010100','010']],
            'invalid_rejected':rejected,'splits_and_one_per_round':True,'promotion_tail_trigger':True,
            'no_future_prefix_labels':True,'23slot_STOP_boundary':True,'validation_threshold_ceil':True}

def stage(net,n,arm,seed,d,run,initial_global,replay_curve=None):
    net.active_n=n;initial_state=base.snapshot(net);initial_steps=net.steps
    rng=np.random.default_rng(seed+18000+100*n)
    order=make_order(rng,d['train'],n,True);index=0;trace=[];curves=[];stable=0;first_pass=None;counts={v:0 for v in d['train']}
    cap=CAPS[n-1];points=set(p for p in POINTS if p<=cap)|{cap}
    rows=d['rows'];start=time.perf_counter();inference=0
    def measure(exposure):
        nonlocal inference
        train=evaluate(net,n,d['train'],rows)
        val=train if n<=4 else evaluate(net,n,d['val'],rows)
        inference+=train['inference_calls']+(0 if n<=4 else val['inference_calls'])
        result={'n':n,'presentations':exposure,'global_presentations':initial_global+exposure,'updates':net.steps,
                'train':slim(train),'validation':slim(val),'passed':passed(n,val)}
        curves.append(result);return result
    measure(0);reason='presentation_cap'
    for exposure in range(1,cap+1):
        value=order[index];question,expected=rows[value]
        assert len(question)==n+5
        prediction=net.lesson(question,expected);trace.append([n,value,prediction]);counts[value]+=1;index+=1
        if index==len(order):index=0;order=make_order(rng,d['train'],n,False)
        if exposure in points or exposure%len(d['train'])==0:
            measurement=measure(exposure)
            if measurement['passed']:
                if first_pass is None:first_pass=exposure
                stable+=1
            else:stable=0
            if stable>=3:reason='three_validation_passes';break
        if time.perf_counter()-start>120:reason='wall_time_cap';break
    training_seconds=time.perf_counter()-start
    if curves[-1]['presentations']!=len(trace):measure(len(trace))
    # Only inspect current-rank final test after promotion/failure decision.
    final_test=evaluate(net,n,d['test'],rows) if n>=5 else None
    before_test=base.snapshot(net)
    assert all(np.array_equal(before_test[k],base.snapshot(net)[k]) for k in before_test)
    after=base.snapshot(net)
    assert net.steps-initial_steps==len(trace)*(n+2)
    assert max(counts.values())-min(counts.values())<=1
    path=run/f'n{n}';path.mkdir()
    np.savez(path/'state.npz',**after)
    (path/'trace.json').write_text(json.dumps(trace));(path/'curve.json').write_text(json.dumps(curves,indent=2))
    (path/'final-test.json').write_text(json.dumps(final_test,indent=2))
    if final_test is not None:assert all(set(counts).isdisjoint(d[key]) for key in ['val','test'])
    summary={'n':n,'presentations':len(trace),'global_presentations':initial_global+len(trace),
             'updates_before':initial_steps,'updates_after':net.steps,'stage_updates':net.steps-initial_steps,
             'unique_presented':sum(v>0 for v in counts.values()),'train_size':len(d['train']),
             'exposure_min':min(counts.values()),'exposure_max':max(counts.values()),'first_pass':first_pass,
             'confirmation_points':[r['presentations'] for r in curves[-3:]] if stable>=3 else None,
             'stop_reason':reason,'training_and_probe_seconds':training_seconds,
             'probe_inference_calls':inference,'validation':curves[-1]['validation'],
             'final_test':None if final_test is None else slim(final_test),
             'test_type':'unseen_at_this_rank_fixed_split' if n>=5 else 'no_independent_test_all_words_taught',
             'first_question':rows[trace[0][1]][0],
             'initial_state_sha':hashlib.sha256(b''.join(v.tobytes() for v in initial_state.values())).hexdigest()}
    (path/'summary.json').write_text(json.dumps(summary,indent=2))
    return summary,trace,curves,initial_state,after

def run(seed,arm,data):
    run_dir=OUT/f'{arm}-{seed}';run_dir.mkdir();net=Net(seed);summaries=[];all_traces=[];all_curves=[];total=0;previous=base.snapshot(net)
    ranks=range(1,9) if arm=='curriculum' else [8]
    for n in ranks:
        assert all(np.array_equal(v,base.snapshot(net)[k]) for k,v in previous.items())
        summary,trace,curves,before,after=stage(net,n,arm,seed,data[n],run_dir,total)
        assert all(np.array_equal(v,before[k]) for k,v in previous.items())
        summaries.append(summary);all_traces+=trace;all_curves+=curves;total+=len(trace);previous=after
        print(json.dumps({'arm':arm,'seed':seed,**{k:summary[k] for k in ['n','presentations','first_pass','stop_reason']},
                          'validation':[summary['validation']['whole_correct'],summary['validation']['total']],
                          'test':None if summary['final_test'] is None else [summary['final_test']['whole_correct'],summary['final_test']['total']]}),flush=True)
        if summary['stop_reason']!='three_validation_passes':break
    # Full replay, preserving the same optimizer across every actual promotion.
    replay=Net(seed);replay_total=0;replay_checks=[]
    for summary in summaries:
        n=summary['n'];d=data[n];rng=np.random.default_rng(seed+18000+100*n)
        order=make_order(rng,d['train'],n,True);index=0;replay.active_n=n
        path=run_dir/f'n{n}';trace=json.loads((path/'trace.json').read_text());curve=json.loads((path/'curve.json').read_text())
        by_exposure={r['presentations']:r for r in curve};stable=0
        for exposure in range(len(trace)+1):
            if exposure:
                nn,value,prediction=trace[exposure-1];assert nn==n and value==order[index]
                assert replay.lesson(*d['rows'][value])==prediction
                index+=1
                if index==len(order):index=0;order=make_order(rng,d['train'],n,False)
            if exposure in by_exposure:
                a=evaluate(replay,n,d['train'],d['rows']);b=a if n<=4 else evaluate(replay,n,d['val'],d['rows'])
                actual={'n':n,'presentations':exposure,'global_presentations':replay_total+exposure,'updates':replay.steps,
                        'train':slim(a),'validation':slim(b),'passed':passed(n,b)}
                assert actual==by_exposure[exposure]
                if exposure:
                    stable=stable+1 if actual['passed'] else 0
                    if stable>=3:assert exposure==len(trace) and summary['stop_reason']=='three_validation_passes'
        saved=np.load(path/'state.npz');assert all(np.array_equal(v,saved[k]) for k,v in base.snapshot(replay).items())
        test=evaluate(replay,n,d['test'],d['rows']) if n>=5 else None
        assert test==json.loads((path/'final-test.json').read_text())
        replay_checks.append({'n':n,'all_actions_curve_optimizer_and_final_test_equal':True});replay_total+=len(trace)
    assert all(np.array_equal(v,base.snapshot(replay)[k]) for k,v in base.snapshot(net).items())
    anchors=[]
    for updates,state in net.anchors.items():
        assert all(np.array_equal(v,replay.anchors[updates][k]) for k,v in state.items())
        clone=Net(seed);clone.p=[state[f'p{i}'].copy() for i in range(4)]
        metric=evaluate(clone,8,data[8]['val'],data[8]['rows'])
        anchors.append({'updates':updates,'validation':slim(metric)})
        folder=run_dir/'n8-budget-checkpoints';folder.mkdir(exist_ok=True);np.savez(folder/f'{updates}.npz',**state)
    result={'arm':arm,'seed':seed,'stages':summaries,'highest_rank':summaries[-1]['n'],
            'reached_n8':summaries[-1]['n']==8,'passed_n8':summaries[-1]['n']==8 and summaries[-1]['stop_reason']=='three_validation_passes',
            'total_presentations':total,'total_updates':net.steps,
            'total_training_and_probe_seconds':sum(s['training_and_probe_seconds'] for s in summaries),
            'old_rank_training_or_probes_after_promotion':False,'replay':replay_checks,'n8_budget_anchors':anchors}
    (run_dir/'summary.json').write_text(json.dumps(result,indent=2));return result,all_curves

def main():
    OUT.mkdir(parents=True,exist_ok=True);data=dataset()
    plan={'id':'P029','upstream_work_order':'P028 at55d1037','user_override':'No old-rank training/probes/retention after promotion; no mixedlengthC; only A+B. Stop a failedseed, never decrease n.',
          'profile':PROFILE,'seeds':base.x.SEEDS,'rank_caps':CAPS,'stage_wall_cap_seconds':120,
          'checkpoints':'Given POINTS plus complete current training rounds and cap; zero is diagnostic only.3new-training-separated passes promotes.',
          'promotion':'n<=4 all legalwords100%; n>=5 heldout-validation whole+STOP>=95%. Preserve parameters and Adam. First newlypromoted questionv1 trainonly.',
          'model':'Unchanged1171param DirectMLP/CE teacherprefix; freegreedy evaluations. No extra n orposition labels.',
          'budget_comparison':'Count ALL lower-rank cost. Save n8-only exact1000update anchors; compare A/B only existing common globalupdate anchors. If no commonobservedbudget or A never reaches8, reportmissing; do not force trainingpastmastery.',
          'data':{n:{k:v for k,v in d.items() if k!='rows'} for n,d in data.items()},
          'sources':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,base.__file__,__import__('inspect').getfile(base.Direct),SOURCE/'docs/references/MLP_paper4_zh_original.md',SOURCE/'experiments/spiral_parser/spiral_parser.py']}}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    validation=checks(data);(OUT/'oracle-compact.json').write_text(json.dumps(validation,indent=2))
    results=[];curves=[]
    for arm in ['curriculum','direct8']:
        for seed in plan['seeds']:
            result,curve=run(seed,arm,data);results.append(result);curves.extend([{'arm':arm,'seed':seed,**r} for r in curve])
            (OUT/'progress.json').write_text(json.dumps(results,indent=2))
    comparisons=[]
    for seed in plan['seeds']:
        a=next(r for r in results if r['arm']=='curriculum' and r['seed']==seed)
        b=next(r for r in results if r['arm']=='direct8' and r['seed']==seed)
        aa={p['updates']:p for p in a['n8_budget_anchors']};bb={p['updates']:p for p in b['n8_budget_anchors']}
        comparisons.append({'seed':seed,'common_global_update_points':[
            {'updates':p,'curriculum_validation':aa[p]['validation'],'direct_validation':bb[p]['validation']} for p in sorted(aa.keys()&bb.keys())],
            'curriculum_entered_n8_after_updates':None if not a['reached_n8'] else a['stages'][-1]['updates_before'],
            'curriculum_total_updates':a['total_updates'],'direct_total_updates':b['total_updates']})
    table=[]
    for row in curves:
        table.append({k:row[k] for k in ['arm','seed','n','presentations','global_presentations','updates']}|
                     {'train_correct':row['train']['whole_correct'],'train_total':row['train']['total'],
                      'validation_correct':row['validation']['whole_correct'],'validation_total':row['validation']['total'],
                      'stop_correct':row['validation']['stop_correct'],'bit_accuracy':row['validation']['bit_accuracy'],
                      'teacher_ce':row['validation']['ce_mean'],'teacher_correct':row['validation']['teacher_correct'],
                      'teacher_targets':row['validation']['teacher_targets'],'passed':row['passed']})
    with (OUT/'curves.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    compact={'plan':plan,'oracle':validation,'runs':results,'matched_update_comparisons':comparisons}
    (OUT/'compact.json').write_text(json.dumps(compact,indent=2))
    print(json.dumps({'complete':True,'summaries':[{k:r[k] for k in ['arm','seed','highest_rank','passed_n8','total_presentations','total_updates']} for r in results]}))

if __name__=='__main__':main()
