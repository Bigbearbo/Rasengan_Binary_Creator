"""Publication figure from saved JSON only; zero model calls or training."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT=Path(__file__).resolve().parent


def main():
    summary=json.loads((ROOT/"results/summary.json").read_text(encoding="utf-8"))
    capacity=json.loads((ROOT/"results/component_capacity/summary.json").read_text(encoding="utf-8"))
    by_model={(m["arm"],m["seed"]):m for m in summary["models"]}
    seeds=(101,202,303)
    steps=np.asarray([0,16,64,128,256,512,1024,2048,4096])
    random_curves=np.asarray([[by_model[("random_train",s)]["validation"][str(t)]["complete_accuracy"] for t in steps] for s in seeds])
    warm_curves=np.asarray([[by_model[("handfilled_train",s)]["validation"][str(t)]["complete_accuracy"] for t in steps] for s in seeds])
    assert np.all(warm_curves==1)
    assert all(by_model[("random_train",s)]["challenge"]["complete_correct"]==936 for s in seeds)
    endpoints={(m["arm"],m["seed"],m["step"]):m["metrics"] for m in capacity["endpoints"]}
    errors=np.asarray([16384-endpoints[("handfilled_train",s,4096)]["complete_correct"] for s in seeds])
    assert errors.tolist()==[3,5,0]

    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.titlesize":13,
        "axes.labelsize":11,"axes.spines.top":False,"axes.spines.right":False,
        "axes.edgecolor":"#A8B0B8","axes.labelcolor":"#263442","xtick.color":"#465461",
        "ytick.color":"#465461","text.color":"#263442","svg.fonttype":"none"})
    fig=plt.figure(figsize=(13.2,6.6),facecolor="white")
    grid=fig.add_gridspec(1,2,width_ratios=(1.6,1),left=.065,right=.975,top=.79,bottom=.255,wspace=.25)
    left=fig.add_subplot(grid[0,0])
    right=fig.add_subplot(grid[0,1])
    seed_colors=("#9AB7D4","#6D9EC8","#427BA8")
    styles=("-","--",":")
    for seed,curve,color,style in zip(seeds,random_curves,seed_colors,styles):
        left.plot(steps,curve,color=color,linestyle=style,lw=1.15,marker="o",ms=3,
                  alpha=.85,label=f"Random: seed {seed}",zorder=2)
    left.plot(steps,random_curves.mean(axis=0),color="#1D4F77",lw=2.7,marker="o",ms=4,
              label="Random: 3-seed mean",zorder=3)
    left.plot(steps,warm_curves.mean(axis=0),color="#BE6A1E",lw=2.4,linestyle="-",
              label="Handfilled, then trained",zorder=4)
    left.axhline(.95,color="#AF3D48",lw=1.25,linestyle=(0,(4,3)),label="95% progress marker",zorder=1)
    left.set_xscale("symlog",linthresh=16,linscale=.6,base=2)
    left.set_xlim(-1,4700)
    left.set_xticks(steps,labels=[str(s) for s in steps])
    left.tick_params(axis="x",labelsize=9)
    left.set_ylim(0,1.055)
    left.set_yticks(np.linspace(0,1,6))
    left.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
    left.set_xlabel("Comparator updates (linear to 16; log₂ thereafter)",labelpad=9)
    left.set_ylabel("Whole MAX answer accuracy on validation")
    left.set_title("A   A 15-parameter decision learns quickly",loc="left",pad=24,fontweight="bold")
    left.text(0,1.035,"Actual learned decoder + fixed handfilled copy circuit",
              transform=left.transAxes,fontsize=10.5,color="#687581")
    left.grid(axis="y",color="#DFE5EA",lw=.7,zorder=0)
    left.text(.025,.315,"First ≥95%: 256 / 512 / 512 updates (seeds 101 / 202 / 303)",
              transform=left.transAxes,fontsize=10,color="#1D4F77")
    left.legend(loc="lower left",bbox_to_anchor=(.005,.015),ncol=2,frameon=False,
                fontsize=9.3,handlelength=2.3,columnspacing=1.45,labelspacing=.65)

    positions=np.arange(3)
    right.bar(positions,errors,width=.55,color="#CE884A",edgecolor="#A75C21",lw=.7,zorder=2)
    right.scatter([2],[0],marker="_",s=220,color="#A75C21",lw=2,zorder=3,clip_on=False)
    for pos,count in zip(positions,errors):
        right.text(pos,count+.17,f"{count:,} / 16,384\n({100*count/16384:.3f}% errors)",
                   ha="center",va="bottom",fontsize=10.3,color="#71471F",linespacing=1.4)
    right.set_xticks(positions,labels=[f"Seed {s}" for s in seeds])
    right.set_xlim(-.65,2.65)
    right.set_ylim(0,6.2)
    right.set_yticks(range(7))
    right.set_xlabel("Handfilled comparator after 4,096 updates",labelpad=9)
    right.set_ylabel("Wrong MAX answers out of 16,384 pairs")
    right.set_title("B   A few exact decisions change",loc="left",pad=24,fontweight="bold")
    right.text(0,1.035,"Component diagnostic: ideal bits; decoder excluded",
               transform=right.transAxes,fontsize=10.5,color="#687581")
    right.grid(axis="y",color="#DFE5EA",lw=.7,zorder=0)
    right.set_axisbelow(True)

    fig.text(.065,.948,"Handfilled structure makes a small learning problem",fontsize=19,
              fontweight="bold",ha="left",va="top")
    fig.text(.065,.895,"Three paired seeds · one fixed training budget · actual old-model word outputs",
              fontsize=12,color="#687581",ha="left",va="top")
    fig.text(.065,.137,"Raw-frame panels: all handfilled-then-trained models remain 100% on train, validation, reused test and fresh challenge.",
              fontsize=10.5,ha="left",va="top")
    fig.text(.065,.098,"Fresh challenge: every random-selector model scores 936/936. Panel B audits all 128×128 ideal operand pairs after training;",
              fontsize=10.5,ha="left",va="top")
    fig.text(.065,.059,"it measures comparator/copy function, not source-decoder generalization. Tie-selection changes do not count as MAX answer errors.",
              fontsize=10.5,ha="left",va="top")
    output=ROOT/"figures"
    output.mkdir(exist_ok=True)
    for extension in ("png","svg"):
        fig.savefig(output/f"handfill_selector_summary.{extension}",dpi=180,facecolor="white")
    plt.close(fig)
    print(json.dumps({"figure_png":str(output/"handfill_selector_summary.png"),
        "figure_svg":str(output/"handfill_selector_summary.svg"),"source":"Saved JSON only",
        "new_model_calls":0,"new_training_updates":0}))


if __name__=="__main__":
    main()
