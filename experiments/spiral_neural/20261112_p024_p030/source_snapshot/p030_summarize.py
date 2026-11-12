"""P030 evidence tables, existing-checkpoint forgetting examples and plots."""
import os,sys,json,csv
sys.dont_write_bytecode=True
from pathlib import Path
import p030_binary_continual as exp
import numpy as np

WORK=exp.OUT
OUT=exp.ROOT/'outputs/sle-research-review'

def load(path,seed):
    saved=np.load(path);net=exp.Model(seed,int(saved['L']),int(saved['H']))
    for label in ['p','m','v','birth']:setattr(net,label,[saved[f'{label}{i}'].copy() for i in range(4)])
    net.t=int(saved['t']);net.growth_rng.bit_generator.state=json.loads(str(saved['growth_rng']))
    return net

def totals(byop):return [sum(x['whole'] for x in byop.values()),sum(x['total'] for x in byop.values())]

def main():
    compact=json.loads((WORK/'compact.json').read_text());rows=[];stages=[];examples=[];curves=[]
    for run in compact['runs']:
        last=run['stages'][-1]
        rows.append({'run':run['run'],'last':last['profile']['name'],'passed':last['stop_reason']=='three_train_validation_passes',
                     'presentations':run['total_presentations'],'updates':run['total_updates'],'parameters':run['parameters'],
                     'last_train':totals(last['train_validation']['train']['by_op']),
                     'last_validation':totals(last['train_validation']['validation']['by_op']),
                     'last_test':None if last['final_test'] is None else totals(last['final_test']['by_op']),
                     'train_MACs':run['train_dense_MACs'],'inference_MACs':run['inference_dense_MACs'],
                     'parameter_optimizer_arrays_bytes':run['parameter_optimizer_arrays_bytes']})
        for s in run['stages']:
            stages.append({'run':run['run'],'phase':s['profile']['name'],'presentations':s['presentations'],'first_pass':s['first_pass'],
                           'parameters':s['parameters'],'reason':s['stop_reason'],
                           'train':totals(s['train_validation']['train']['by_op']),
                           'validation':totals(s['train_validation']['validation']['by_op']),
                           'test':None if s['final_test'] is None else totals(s['final_test']['by_op'])})
            path=WORK/run['run']/s['profile']['name']
            for r in json.loads((path/'curve.json').read_text()):
                for group in ['train','validation']:
                    for op,m in r[group]['by_op'].items():
                        curves.append({'run':run['run'],'phase':s['profile']['name'],'presentations':r['presentations'],
                                       'updates':r['updates'],'parameters':r['parameters'],'group':group,'op':op,
                                       'whole':m['whole'],'stop':m['stop'],'total':m['total'],'overflow':m['overflow'],
                                       'teacher_correct':m['teacher_correct'],'teacher_targets':m['teacher_targets'],
                                       'bit_correct':json.dumps(m['bit_correct']),'ce_mean':r[group]['ce_mean']})
        # Existing val/test cases only: actual Echo behavior before/after Neg.
        if any(s['profile']['name']=='2b_add_neg' for s in run['stages']):
            before=load(WORK/run['run']/'2a_echo_op2/state.npz',run['seed'])
            after=load(WORK/run['run']/'2b_add_neg/state.npz',run['seed'])
            p=exp.REGISTRY['2b_add_neg']
            for v in [5,6]:
                q=exp.encode(p,0,v);expected=exp.answer(0,3,v)+'S'
                examples.append({'run':run['run'],'value':v,'subset':'validation' if v==5 else 'test','Q':q,
                                 'expected':expected,'before_neg':before.generate(q)[0],'after_neg':after.generate(q)[0]})
    controls=[]
    for c in compact['scratch_controls']:
        continuous=next(s for r in compact['runs'] if r['policy']=='dynamic' and r['seed']==c['seed'] for s in r['stages'] if s['profile']['name']==c['profile'])
        controls.append({'seed':c['seed'],'phase':c['profile'],'continuous_presentations':continuous['presentations'],
                         'continuous_passed':continuous['stop_reason']=='three_train_validation_passes',
                         'scratch_presentations':c['stage']['presentations'],'scratch_passed':c['stage']['stop_reason']=='three_train_validation_passes',
                         'same_shape':[c['L'],c['H']],'scratch_test':totals(c['stage']['final_test']['by_op'])})
    result={'runs':rows,'stages':stages,'controls':controls,'echo_before_after_neg':examples,
            'total_continual_presentations':sum(r['total_presentations'] for r in compact['runs']),
            'total_continual_updates':sum(r['total_updates'] for r in compact['runs']),
            'total_control_presentations':sum(c['stage']['presentations'] for c in compact['scratch_controls']),
            'total_control_updates':sum(c['stage']['token_updates'] for c in compact['scratch_controls']),
            'all_replay_passed':all(r['all_trace_measurement_growth_and_optimizer_replay_equal'] for r in compact['runs']) and all(c['all_trace_measurement_and_optimizer_replay_equal'] for c in compact['scratch_controls'])}
    (WORK/'summary-table.json').write_text(json.dumps(result,indent=2))
    with (WORK/'learning-curves.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(curves[0]));writer.writeheader();writer.writerows(curves)
    os.environ['MPLCONFIGDIR']=str(WORK/'matplotlib-cache')
    sys.path.insert(0,str(exp.ROOT/'work/sle-research-review/plot-deps'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    colors={'dynamic':'#1565c0','fixed':'#00856a','bottleneck':'#b95014'}
    names=[r['run'] for r in compact['runs']]
    for run in compact['runs']:
        yy=[s['presentations'] for s in run['stages']];xx=list(range(len(yy)))
        axes[0,0].plot(xx,yy,'o-',color=colors[run['policy']],alpha=.65,label=run['run'])
    axes[0,0].set(title='A. Presentations per stage (cap=3000)',ylabel='Presentations',xticks=range(7),xticklabels=['E1','E2','E3','Op2','+Neg','+Zero','+END'])
    axes[0,0].legend(fontsize=7,ncol=3,loc='upper left')
    for policy,ax in [('dynamic',axes[0,1]),('fixed',axes[1,0])]:
        for seed in exp.SEEDS:
            subset=[r for r in curves if r['run']==f'{policy}-{seed}' and r['phase']=='2b_add_neg' and r['group']=='validation']
            for op,style in [('echo','-'),('neg','--')]:
                ss=[r for r in subset if r['op']==op]
                ax.plot([r['presentations'] for r in ss],[r['whole']/r['total'] for r in ss],style,label=f'{seed} {op}',alpha=.75)
        ax.set(title=f'{"B" if policy=="dynamic" else "C"}. {policy}: Neg stage validation (1 value/op)',xlabel='Neg-stage presentations',ylabel='Whole-answer accuracy',ylim=(-.04,1.08))
        ax.legend(fontsize=7,ncol=2,loc='lower right')
    x=np.arange(len(rows));vals=[r['last_train'][0]/r['last_train'][1] for r in rows]
    vv=[r['last_validation'][0]/r['last_validation'][1] for r in rows];tt=[r['last_test'][0]/r['last_test'][1] for r in rows]
    axes[1,1].bar(x-.25,vals,.25,label='Train');axes[1,1].bar(x,vv,.25,label='Validation');axes[1,1].bar(x+.25,tt,.25,label='Test')
    axes[1,1].set(title='D. Final reached stage: train vs held-out',ylabel='Whole-answer accuracy',xticks=x,xticklabels=names,ylim=(0,1.18))
    axes[1,1].tick_params(axis='x',rotation=55,labelsize=8);axes[1,1].legend(loc='upper right',fontsize=8,ncol=3)
    for ax in axes.flat:ax.grid(axis='y',alpha=.2)
    fig.suptitle('P030 pilot: pure binary input, continuous weights/Adam, delayed END',fontsize=14)
    fig.savefig(OUT/'P030-pilot-learning-curves.png',dpi=160);fig.savefig(OUT/'P030-pilot-learning-curves.svg');plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k not in ('stages','echo_before_after_neg')},ensure_ascii=True))

if __name__=='__main__':main()
