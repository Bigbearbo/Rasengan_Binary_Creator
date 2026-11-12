"""P029 fixed evidence aggregation and standalone scientific learning-curve plots."""
import os,sys,json
from pathlib import Path
ROOT=Path('D:/Codex用')
WORK=ROOT/'work/sle-research-review/echo-monotonic-ranks-20261112'
OUT=ROOT/'outputs/sle-research-review'
os.environ['MPLCONFIGDIR']=str(WORK/'matplotlib-cache')
sys.path.insert(0,str(ROOT/'work/sle-research-review/plot-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def main():
    compact=json.loads((WORK/'compact.json').read_text(encoding='utf-8'))
    assert len(compact['runs'])==6
    stages=[];runs=[];curves={};presentations=updates=0
    for run in compact['runs']:
        arm=run['arm'];seed=run['seed'];ranks=[s['n'] for s in run['stages']]
        assert ranks==(list(range(1,9)) if arm=='curriculum' else [8])
        for s in run['stages']:
            n=s['n'];curve=json.loads((WORK/f'{arm}-{seed}'/f'n{n}'/'curve.json').read_text())
            curves[arm,seed,n]=curve
            assert len(s['confirmation_points'])==3 and len(set(s['confirmation_points']))==3
            thresholds={}
            for threshold in [.5,.9,.95,1.]:
                hit=next((r['presentations'] for r in curve if r['validation']['whole_correct']/r['validation']['total']>=threshold),None)
                thresholds[str(threshold)]=hit
            at100=next((r for r in curve if r['presentations']==100),None)
            row={k:s[k] for k in ['n','presentations','global_presentations','updates_before','updates_after','stage_updates','unique_presented','train_size','first_pass','confirmation_points']}
            row.update(arm=arm,seed=seed,first_measured_fraction=thresholds,
                       at100=None if at100 is None else at100['validation'],
                       at100_note='measured' if at100 else 'promoted_before_100_no_return',
                       final_test=None if s['final_test'] is None else [s['final_test']['whole_correct'],s['final_test']['total']])
            stages.append(row)
        last=run['stages'][-1]
        runs.append({'arm':arm,'seed':seed,'total_presentations':run['total_presentations'],'total_updates':run['total_updates'],
                     'seconds_train_plus_probes':run['total_training_and_probe_seconds'],
                     'n8_presentations':last['presentations'],'n8_first_pass':last['first_pass'],
                     'n8_entry_updates':last['updates_before'],
                     'n8_validation':[last['validation']['whole_correct'],last['validation']['total']],
                     'n8_final_test':[last['final_test']['whole_correct'],last['final_test']['total']]})
        presentations+=run['total_presentations'];updates+=run['total_updates']
    result={'runs':runs,'stages':stages,'total_presentations':presentations,'total_updates':updates,
            'matched_update_comparisons':compact['matched_update_comparisons'],
            'training_python':'3.12.14','training_numpy':'2.3.5','plot_matplotlib':matplotlib.__version__,'plot_numpy':np.__version__}
    (WORK/'summary-table.json').write_text(json.dumps(result,indent=2))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    colors=['#1565c0','#00856a','#b95014'];seeds=[101,202,303]
    for seed,color in zip(seeds,colors):
        ss=[s for s in stages if s['arm']=='curriculum' and s['seed']==seed]
        axes[0,0].plot([s['n'] for s in ss],[s['presentations'] for s in ss],marker='o',color=color,label=f'Seed {seed}')
        for arm,style in [('curriculum','-'),('direct8','--')]:
            curve=curves[arm,seed,8]
            y=[r['validation']['whole_correct']/r['validation']['total'] for r in curve]
            label=f'{seed}: '+('curriculum' if arm=='curriculum' else 'direct n=8')
            axes[0,1].plot([r['presentations'] for r in curve],y,style,color=color,label=label)
            axes[1,0].plot([r['updates'] for r in curve],y,style,color=color,label=label)
    axes[0,0].axhline(100,color='#777',ls=':',lw=1)
    axes[0,0].set(title='A. Presentations needed at each rank',xlabel='Data rank n (k=1, operator unchanged)',ylabel='Stage presentations to promotion',xticks=range(1,9))
    axes[0,0].legend(loc='upper left')
    axes[0,1].set(title='B. n=8 validation vs local exposure',xlabel='n=8 presentations (earlier ranks excluded)',ylabel='Whole-answer accuracy',ylim=(-.02,1.03))
    axes[1,0].set(title='C. n=8 validation including earlier update cost',xlabel='Cumulative optimizer updates',ylabel='Whole-answer accuracy',ylim=(-.02,1.03))
    for ax in [axes[0,1],axes[1,0]]:ax.axhline(.95,color='#777',ls=':',lw=1)
    axes[0,1].legend(fontsize=8,loc='lower right')
    positions=np.arange(3);width=.35
    for arm,offset,color in [('curriculum',-width/2,'#395c86'),('direct8',width/2,'#8daac7')]:
        rr=[next(r for r in runs if r['arm']==arm and r['seed']==s) for s in seeds]
        bars=axes[1,1].bar(positions+offset,[r['total_updates'] for r in rr],width,label=arm,color=color)
        axes[1,1].bar_label(bars,labels=[f"{r['n8_final_test'][0]}/32 test" for r in rr],padding=3,fontsize=9)
    axes[1,1].set(title='D. Total training updates; labels = final test',xlabel='Seed',ylabel='All-rank optimizer updates',xticks=positions,xticklabels=seeds,ylim=(0,39000))
    axes[1,1].legend(loc='upper right',fontsize=8)
    for ax in axes.flat:ax.grid(axis='y',alpha=.18)
    fig.suptitle('P029: monotonic Echo ranks, no old-rank rehearsal or retention probes',fontsize=15)
    png=OUT/'P029-learning-curves.png';svg=OUT/'P029-learning-curves.svg'
    fig.savefig(png,dpi=160);fig.savefig(svg);plt.close(fig)
    print(json.dumps({'total_presentations':presentations,'total_updates':updates,'runs':runs,
                      'common_update_counts':[{ 'seed':c['seed'],'count':len(c['common_global_update_points'])} for c in compact['matched_update_comparisons']],
                      'png':str(png),'svg':str(svg)},ensure_ascii=True))

if __name__=='__main__':main()
