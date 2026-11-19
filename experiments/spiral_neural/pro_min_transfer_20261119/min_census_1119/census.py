"""Post-hoc, no-training census of 33,024 raw n7 frames with a+b<128 across four original opcodes."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[variable]="1"
import numpy as np
import codec

HERE=Path(__file__).resolve().parent
ARMS=("frozen","joint","staged","overwrite")  # last is a structural control

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def getdir(supplied, candidates, sentinel):
    for directory in ([supplied] if supplied else [])+candidates:
        if (directory/sentinel).is_file():
            return directory
    raise FileNotFoundError(str(sentinel))

def census(core_dir, staged_dir, output, verify):
    spec=importlib.util.spec_from_file_location("min_study_census",core_dir/"study.py")
    core=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    assert sha(HERE/"codec.py") == "67f71587892ff7d17f9cea207296cd35347a59c4e06e4545fee20b0bfdf5e265"
    truth=np.array([(a,b,op) for a in range(128) for b in range(128-a) for op in range(4)],dtype=np.uint8)
    ai,bi,ops=truth.T
    frames=[codec.encode(int(op),int(a),int(b),7) for a,b,op in truth]
    assert len(frames)==len(set(frames))==33024
    # Test the census raw generator against both original tools and all 14,392 previously archived rows.
    assert all(codec.parse_for_scoring(f,7)==(int(op),int(a),int(b)) for f,(a,b,op) in zip(frames,truth))
    lookup={(int(a),int(b),int(op)):i for i,(a,b,op) in enumerate(truth)}
    parent_rows=json.loads((core_dir/"inherited/data.json").read_text())["panels"]
    panel_ids={}
    split=np.zeros(len(truth),np.uint8)
    for i,(name,rows) in enumerate(parent_rows.items(),1):
        panel_ids[name]=i
        for r in rows:
            idx=lookup[(r["a"],r["b"],r["op"])]
            assert frames[idx]==r["frame_bits"] and split[idx]==0
            split[idx]=i
    raw=np.frombuffer("".join(frames).encode("ascii"),dtype=np.uint8).reshape(len(truth),34) - ord("0")
    assert int((split>0).sum())==14392
    ideal=core.bitwords(ai.astype(int),bi.astype(int))
    files={"inputs.npz":dict(truth=truth,raw_34_bits_packed=np.packbits(raw,axis=1),pr133_split=split)}
    stats={}
    for seed in core.SEEDS:
        source=core.prior.load_source(seed)
        decoded=core.prior.decode(source,raw)
        words=decoded["words"]
        operands_ok=np.all(words==ideal,axis=1)
        opcode_ok=decoded["pred_op"]==ops
        stats[str(seed)]={
            "correct_operand_pairs":int(operands_ok.sum()),"correct_opcodes":int(opcode_ok.sum()),
            "correct_simultaneous_operands_and_opcode":int((operands_ok&opcode_ok).sum()),"arms":{}
        }
        fields=dict(decoded_words=words,decoded_opcodes=decoded["pred_op"])
        actual_panel=core.prepare_panel((ai,bi,words))
        ideal_panel=core.prepare_panel((ai,bi,ideal))
        for arm in ARMS:
            if arm=="staged":
                checkpoint=staged_dir/f"results/seed{seed}/states.npz"
                end=512
            else:
                checkpoint=core_dir/f"results/{arm}_{seed}/states.npz"
                with np.load(checkpoint,allow_pickle=False) as source_states:
                    end=list(source_states["stages"]).index("min_512")
            with np.load(checkpoint,allow_pickle=False) as source_states:
                c,head=source_states["comparator"][end],source_states["adapter"][end]
            pred=core.answers(actual_panel,c,head,arm)
            ideal_pred=core.answers(ideal_panel,c,head,arm)
            fields[arm+"_actual"]=pred
            fields[arm+"_ideal"]=ideal_pred
            detail={"checkpoint_sha256":sha(checkpoint)}
            for task,j,target in (("max",2,np.maximum(ai,bi)),("min",3,np.minimum(ai,bi))):
                act_ok=pred[j]==target
                ideal_ok=ideal_pred[j]==target
                detail[task]={"actual_correct":int(act_ok.sum()),"ideal_correct":int(ideal_ok.sum()),
                              "both_wrong":int((~act_ok&~ideal_ok).sum()),
                              "actual_only_wrong":int((~act_ok&ideal_ok).sum()),
                              "ideal_only_wrong":int((act_ok&~ideal_ok).sum()),
                              "changed_actual_vs_ideal_answers":int((pred[j]!=ideal_pred[j]).sum()),
                              "correct_outside_all_four_pr133_panels":int((act_ok&(split==0)).sum())}
            stats[str(seed)]["arms"][arm]=detail
        files[f"seed{seed}.npz"]=fields
    summary={"scope":"Post-hoc census after inspecting the main and staged experiments, not independent evaluation, no optimization or task selection. Evaluates each output on all a,b in [0,127] satisfying a+b<128, all four original opcodes, at MIN step 512. The input generator uses codec.encode, raw frame interpretation uses only the original learned receiver. The ideal path is a diagnostic counterfactual. Some census inputs were used in upstream receiver or downstream training; this is bounded exhaustive functional verification.",
             "run":"pro_min_transfer_20261119_v1", "seeds":list(core.SEEDS),"per_seed_raw_rows":len(raw),
             "ordered_pairs":8256,"distinct_opcodes":list(codec.OP_IDS),
             "per_seed_pr133_frames_matched":int((split!=0).sum()),
             "per_seed_frames_outside_all_four_pr133_panels":int((split==0).sum()),
             "split_ids":{"outside":0,**panel_ids},
             "raw_packing":"MSB first, 34 bits per row plus 6 zero padding bits. truth columns a,b,opcode index; opcode index maps through distinct_opcodes.",
             "prediction_fields":"axis 0 in each {arm}_{actual,ideal} array: MAX left decision, MIN left decision, MAX numeric answer, MIN numeric answer.",
             "source_codec_sha256":sha(HERE/"codec.py"), "source_zip_sha256":"c33c180362cec0e968fa704f3cf2dd55fbff5c36e348ad8e755b201c347cbed2",
             "additional_fit_steps":0,"receiver_forward_rows":len(raw)*len(core.SEEDS),"results":stats}
    if not verify: output.mkdir(parents=True,exist_ok=False)
    for name,fields in files.items():
        if verify:
            with np.load(output/name,allow_pickle=False) as saved:
                assert set(saved.files)==set(fields) and all(np.array_equal(v,saved[k]) for k,v in fields.items())
        else: np.savez_compressed(output/name,**fields)
    if verify: assert json.loads((output/"summary.json").read_text())==summary
    else: (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"status":"PASS","mode":"verify" if verify else "record","receiver_rows":99072,
                      "numeric_answers_including_ideal":99072*4*2*2,"new_training_updates":0,
                      "matched_pr133_raw_rows":int((split!=0).sum())}))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--core",type=Path)
    parser.add_argument("--staged",type=Path)
    parser.add_argument("--output",type=Path,default=HERE/"results")
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    core_dir=getdir(args.core,[HERE.parent/"min_transfer_20261119",HERE.parent],"study.py")
    staged_dir=getdir(args.staged,[HERE.parent/"min_stage_1119",HERE.parent/"staged",HERE.parent/"supplement"],"staged.py")
    census(core_dir,staged_dir,args.output,args.verify)
