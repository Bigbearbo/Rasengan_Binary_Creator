"""Draw the learning curves from saved numerical scores; no optimizer calls."""
import sys, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import FixedLocator, FixedFormatter
root = Path(sys.argv[1])
output = Path(sys.argv[2])
main = json.loads((root/'min_transfer_20261119/results/metrics.json').read_text())
stage = {s:json.loads((root/f'min_stage_1119/results/seed{s}/metrics_by_step.json').read_text()) for s in (101,202,303)}
f = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
if f.exists():
    from matplotlib import font_manager
    font_manager.fontManager.addfont(str(f))
    plt.rcParams['font.family'] = FontProperties(fname=f).get_name()
plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,
                     'font.size':10,'axes.unicode_minus':False,'savefig.facecolor':'white'})
fig, axes = plt.subplots(1,3,figsize=(10.9,3.9),sharey=True)
fig.subplots_adjust(top=.76,bottom=.21,left=.075,right=.98,wspace=.11)
fig.text(.075,.921,'新課與舊課能否一起保住？',weight='bold',fontsize=17)
fig.text(.075,.843,'驗證集 2,096 題　｜　線為三次配對實驗平均，陰影為範圍',fontsize=10,color='#424d61')
for ax,(arm,label) in zip(axes,[('frozen','只訓練新接頭'),('joint','第一步就一起訓練'),('staged','接頭學會後才一起訓練')]):
    steps=list(range(513)) if arm=='staged' else [0,1,4,16,32,64,128,256,512]
    for key,color,style,name in [('max_correct','#783b8a','-','舊課 MAX'),('min_correct','#007768','--','新課 MIN')]:
        series=np.array([[stage[s]['val'][i][key] if arm=='staged' else main[f'{arm}_{s}'][f'min_{i:03}']['val'][key] for i in steps] for s in (101,202,303)])/2096*100
        ax.fill_between(steps,series.min(0),series.max(0),color=color,alpha=.12,lw=0)
        ax.plot(steps,series.mean(0),color=color,ls=style,lw=2,label=name,marker=None if arm=='staged' else 'o',ms=2)
    if arm=='staged':
        ax.axvline(55,color='#5c6777',lw=.9,ls=':')
        ax.text(48,36,'開始解凍',ha='right',fontsize=8,color='#56616f')
    ax.set_xscale('symlog',base=2,linthresh=16)
    ax.xaxis.set_major_locator(FixedLocator([0,16,64,256,512]))
    ax.xaxis.set_major_formatter(FixedFormatter(['0','16','64','256','512']))
    ax.set_ylim(-4,105); ax.set_yticks([0,25,50,75,100]); ax.set_xlim(-1,540);ax.tick_params(length=0,labelsize=9,pad=5)
    ax.grid(axis='y',color='#dde4e9',lw=.7);ax.set_axisbelow(True);ax.set_title(label,fontsize=12,pad=9)
axes[0].set_ylabel('整題正確率（%）',fontsize=9)
fig.text(.527,.055,'MIN 訓練更新次數（非等距刻度）',ha='center',fontsize=9)
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='upper right',bbox_to_anchor=(.98,.98),frameon=False,ncol=2,fontsize=9,handlelength=2.5,columnspacing=1)
fig.savefig(output,dpi=175);plt.close(fig)
