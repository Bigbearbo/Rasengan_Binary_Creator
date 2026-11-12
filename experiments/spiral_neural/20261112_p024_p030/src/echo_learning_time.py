"""P028: fresh learning curves; stop on two train-only perfect rounds."""
from _archive_paths import ARCHIVE_ROOT, REPO_ROOT, SRC_DIR, RUNS_ROOT, PLOTS_ROOT
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import hashlib,json,time
from pathlib import Path
import numpy as np
import echo_teaching_comparison as base
OUT=RUNS_ROOT/'echo-learning-time-20261112'
MAX=10000

def probe(net,bank,rows):
    before=base.snapshot(net);whole=stop=0;bits=np.zeros(9,dtype=int)
    for value in bank:
        question,expected=rows[value];tokens=net.predict(question)
        stopped=tokens.endswith('S');answer=tokens[:-1] if stopped else tokens
        whole+=tokens==expected+'S';stop+=stopped and len(answer)==9
        bits+=[i<len(answer) and answer[i]==b for i,b in enumerate(expected)]
    assert all(np.array_equal(v,base.snapshot(net)[k]) for k,v in before.items())
    return {'whole_correct':int(whole),'total':len(bank),'bit_correct_by_position':bits.tolist(),
            'bit_accuracy':float(bits.sum()/(9*len(bank))),'stop_at_correct_position':int(stop)}

def update_stable(stable,score):return stable+1 if score['whole_correct']==score['total'] else 0

def checks():
    good={'whole_correct':192,'total':192};bad={'whole_correct':191,'total':192}
    assert [update_stable(0,good),update_stable(1,bad),update_stable(0,bad),update_stable(1,good)]==[1,0,0,2]
    rows,bank,_=base.x.material()
    net=base.Supervised(101);quick=probe(net,bank,rows);reference=base.evaluate(net,bank,rows)
    assert all(quick[k]==reference[k] for k in quick)
    return {'two_consecutive_train_only_checks':True,'imperfect_resets_streak':True,
            'probe_nonmutation_and_matches_full_evaluator':True}

def train(seed,arm,rows,bank,heldout):
    net=base.Supervised(seed) if arm=='ce_shuffle' else base.Reward(seed)
    rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(bank).tolist();index=0;trace=[];touched=set();stable=0
    curve=[{'presentations':0,'updates':0,**probe(net,bank,rows)}]
    start=time.perf_counter();reason='presentation_cap'
    for episode in range(1,MAX+1):
        value=order[index];question,expected=rows[value]
        if arm=='ce_shuffle':record=[value,net.lesson(question,expected)]
        else:
            tokens,rewards=net.episode(question,lambda pos,t:base.old.local_grade(expected,pos,t),rng)
            record=[value,tokens,rewards]
        trace.append(record);touched.add(value);index+=1
        if index==len(order):index=0;order=shuffle.permutation(bank).tolist()
        if episode%192==0 or episode==MAX:
            score=probe(net,bank,rows);curve.append({'presentations':episode,'updates':net.steps,**score})
            # Partial final round is diagnostic only, not a stability confirmation.
            if episode%192==0:
                stable=update_stable(stable,score)
                if stable>=2:reason='two_perfect_train_rounds';break
        if time.perf_counter()-start>120:reason='wall_time_cap';break
    seconds=time.perf_counter()-start
    if curve[-1]['presentations']!=len(trace):curve.append({'presentations':len(trace),'updates':net.steps,**probe(net,bank,rows)})
    assert not touched&set(heldout)
    for i in range(0,len(trace)-191,192):assert len({r[0] for r in trace[i:i+192]})==192
    # Heldout is first inspected AFTER stop decision. It never controls training.
    final_train=base.evaluate(net,bank,rows);final_held=base.evaluate(net,heldout,rows)
    assert all(curve[-1][k]==final_train[k] for k in ['whole_correct','total','bit_accuracy','bit_correct_by_position','stop_at_correct_position'])
    folder=OUT/f'{arm}-{seed}';folder.mkdir()
    final=base.snapshot(net);np.savez(folder/'state.npz',**final)
    (folder/'trace.json').write_text(json.dumps(trace));(folder/'curve.json').write_text(json.dumps(curve,indent=2))
    (folder/'probes.json').write_text(json.dumps({'train':final_train,'heldout':final_held},indent=2))
    # Replay training, every measured curve point and the stopping streak.
    replay=base.Supervised(seed) if arm=='ce_shuffle' else base.Reward(seed)
    rng=np.random.default_rng(seed+9100);shuffle=np.random.default_rng(seed+18000)
    order=shuffle.permutation(bank).tolist();index=0;replay_stable=0
    by_episode={r['presentations']:r for r in curve}
    assert probe(replay,bank,rows)=={k:v for k,v in by_episode[0].items() if k not in ('presentations','updates')}
    for n,record in enumerate(trace,1):
        value=record[0];assert value==order[index];question,expected=rows[value]
        if arm=='ce_shuffle':assert replay.lesson(question,expected)==record[1]
        else:
            tokens,rewards=replay.episode(question,lambda pos,t:base.old.local_grade(expected,pos,t),rng)
            assert [value,tokens,rewards]==record
        index+=1
        if index==len(order):index=0;order=shuffle.permutation(bank).tolist()
        if n in by_episode:
            score=probe(replay,bank,rows)
            assert {'presentations':n,'updates':replay.steps,**score}==by_episode[n]
            if n%192==0:
                replay_stable=update_stable(replay_stable,score)
                if replay_stable>=2:assert n==len(trace) and reason=='two_perfect_train_rounds'
    assert all(np.array_equal(v,base.snapshot(replay)[k]) for k,v in final.items())
    assert base.evaluate(replay,heldout,rows)==final_held
    first={}
    for label,threshold in [('90percent',.9),('95percent',.95),('100percent',1.)]:
        hit=next((i for i,r in enumerate(curve) if r['whole_correct']/r['total']>=threshold),None)
        first[label]=None if hit is None else {'previous_measured_presentations':curve[max(0,hit-1)]['presentations'],
                     'first_measured_presentations':curve[hit]['presentations'],'updates':curve[hit]['updates']}
    result={'arm':arm,'seed':seed,'presentations':len(trace),'unique_presented':len(touched),
            'complete_rounds':len(trace)//192,'token_updates':net.steps,'seconds_including_train_probes':seconds,
            'stop_reason':reason,'first_thresholds':first,
            'confirmed_perfect_pair':None if reason!='two_perfect_train_rounds' else [curve[-2]['presentations'],curve[-1]['presentations']],
            'train':base.trim(final_train),'heldout':base.trim(final_held),
            'all_actions_optimizer_learning_curve_and_stop_replay_equal':True}
    (folder/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True);rows,bank,heldout=base.x.material()
    plan={'id':'P028','seeds':base.x.SEEDS,'arms':['ce_shuffle','reward_shuffle'],
          'fixed_model_and_learning':'Exactly P027 learners,1171params, same192/64split,seeds/init/RNG/schedule. Fresh training. No repeat-blocked arm rerun; it did not learn in P027.',
          'measurement':'Every192presentations, greedy freegeneration on192TRAIN only. Stop after two consecutive full-round checks192/192. Recordfirst90/95/100percent crossing and confirmedperfectpair; interval width192 not exact first-ever mastery.',
          'caps':'10000presentations or120sec includingtrainprobes, no tuning or continuation aftercap. Final partialround probe cannotconfirm stability.',
          'heldout':'No heldout inspect until stopped; finalheldout result may differ fromtrainmastery. Not newblinddata or arbitrarylength.',
          'sources':{str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [__file__,base.__file__,base.old.__file__]}}
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    check=checks();(OUT/'checks.json').write_text(json.dumps(check,indent=2))
    runs=[]
    for arm in plan['arms']:
        for seed in plan['seeds']:
            runs.append(train(seed,arm,rows,bank,heldout));(OUT/'progress.json').write_text(json.dumps(runs,indent=2))
    (OUT/'compact.json').write_text(json.dumps({'plan':plan,'checks':check,'runs':runs},indent=2))

if __name__=='__main__':main()
