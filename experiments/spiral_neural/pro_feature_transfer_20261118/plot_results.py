"""Post-training visualization; never selects or updates a model."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
models = json.loads((ROOT/'results/summary.json').read_text())['models']
status = json.loads((ROOT/'results/run_metadata.json').read_text())
assert status['status'] == 'completed'
arms = ['mature_hidden', 'random_hidden', 'raw_projection']
names = {'mature_hidden':'Mature features', 'random_hidden':'Random features', 'raw_projection':'Raw isometric projection'}
colors = {'mature_hidden':'#007C83', 'random_hidden':'#83909C', 'raw_projection':'#7950B5'}
seeds = [101,202,303]
steps = np.array([0,16,64,128,256,512,1024,2048,4096])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig, axes = plt.subplots(1,2,figsize=(12,5.3),gridspec_kw={'width_ratios':[1.18,1]},layout='constrained')
for arm in arms:
    rows = [next(m for m in models if m['arm']==arm and m['seed']==s) for s in seeds]
    val = np.array([[m['validation'][str(t)]['complete_accuracy']*100 for t in steps] for m in rows])
    axes[0].plot(steps,val.mean(0),color=colors[arm],lw=2.2,marker='o',markersize=3,label=names[arm])
    axes[0].fill_between(steps,val.min(0),val.max(0),color=colors[arm],alpha=.11)
for j,arm in enumerate(arms):
    scores = [next(m for m in models if m['arm']==arm and m['seed']==s)['test']['complete_accuracy']*100 for s in seeds]
    x = np.arange(3)+(j-1)*.25
    bars = axes[1].bar(x,scores,width=.23,color=colors[arm])
    for b,score in zip(bars,scores):
        axes[1].text(b.get_x()+b.get_width()/2,score+1.1,f'{score:.1f}',ha='center',va='bottom',fontsize=8)
for ax in axes:
    ax.axhline(95,color='#B34943',ls='--',lw=1,label='95% progress marker' if ax is axes[1] else None)
    ax.set_ylim(0,103)
    ax.grid(axis='y',alpha=.18)
    ax.set_axisbelow(True)
    ax.set_ylabel('Whole seven-bit answer correct (%)')
axes[0].set_title('Validation learning curves',loc='left',fontweight='bold')
axes[0].set_xlabel('New-head updates')
axes[0].set_xticks([0,1024,2048,3072,4096])
axes[0].legend(loc='lower right',frameon=False,fontsize=9)
axes[0].text(.02,.02,'Line: mean of 3 seeds; band: observed min-max',transform=axes[0].transAxes,fontsize=8,color='#53616A')
axes[1].set_title('Fresh test after the fixed budget',loc='left',fontweight='bold')
axes[1].set_xticks(np.arange(3),[f'Seed {s}' for s in seeds])
axes[1].set_xlabel('Paired source / head seeds')
baseline = models[0]['test']['copy_a_baseline']*100
axes[1].axhline(baseline,color='#596570',ls=':',lw=1.2,label=f'Always copy a or b: {baseline:.1f}%')
axes[1].legend(loc='upper left',bbox_to_anchor=(0,0.88),frameon=False,fontsize=9)
fig.suptitle('Can a small new head reuse mature features?\nMAX readout: 263 trainable parameters, 4,096 updates per model',fontsize=15,fontweight='bold')
(ROOT/'figures').mkdir(exist_ok=True)
fig.savefig(ROOT/'figures/feature_transfer_summary.png',dpi=180)
fig.savefig(ROOT/'figures/feature_transfer_summary.svg')
plt.close(fig)
print(json.dumps({'figure':'figures/feature_transfer_summary.png','model_selection':False,'new_training_updates':0}))
