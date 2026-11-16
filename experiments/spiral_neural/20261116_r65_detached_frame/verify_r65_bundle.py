#!/usr/bin/env python3
"""Read-only independent replay for the R65 bundle (no torch or training).

Usage: python verify_r65_bundle.py PATH_TO_UNPACKED_r65_work
Requires numpy and Python >=3.9. Never changes the original files.
"""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def decode_prediction(logits):
    s = ""
    for t in logits.argmax(-1):
        s += "01S"[int(t)]
        if int(t) == 2:
            break
    return s

def main(root):
    root=Path(root)
    prereg=json.loads((root/"r65_prereg.json").read_text())
    assert sha(root/"r65_detached_frame.py")==prereg["source_sha256"]
    assert sha(root/"r65_manifest.jsonl")==prereg["manifest_sha256"]
    assert sha(root/"r64_reference/r64_outputs/raw_predictions.jsonl")==prereg["r64_reference_raw_sha256"]
    content=json.loads((root/"R65_SHA256SUMS.json").read_text())
    for filename,expected in content.items():
        assert sha(root/filename)==expected, filename
    corpus=read_jsonl(root/"r65_manifest.jsonl")
    assert len(corpus)==1472
    rows=[r for r in corpus if r["split"]!="train"]
    assert len(rows)==448
    X=np.array([[2*int(bit)-1 for bit in r["raw_bits"]] for r in rows],dtype=np.float32)
    original=read_jsonl(root/"r64_reference/r64_outputs/raw_predictions.jsonl")
    assert len(original)==2688
    ref={(r["seed"],r["arm"],r["id"]):r for r in original}
    current=read_jsonl(root/"r65_outputs/raw_predictions.jsonl")
    assert len(current)==1344
    byseed={}
    for seed in (101,202,303):
        predictions=[r for r in current if r["seed"]==seed]
        assert len(predictions)==448 and [r["id"] for r in predictions]==[r["id"] for r in rows]
        with np.load(root/f"r65_outputs/model_{seed}_detached_lambda1.npz") as f:
            w={name:f[name] for name in f.files}
        H=np.tanh(X@w["enc.weight"].T+w["enc.bias"])
        zs=(H@w["math.weight"].T+w["math.bias"]).reshape(-1,13,3)
        fs=(H@w["frame.weight"].T+w["frame.bias"]).reshape(-1)
        for i,row in enumerate(predictions):
            assert decode_prediction(zs[i])==row["math_pred"]
            assert abs(float(fs[i])-float(row["frame_logit"]))<1e-4
            assert row["math_pred"]==ref[(seed,"math_only_lambda0",row["id"])]["math_pred"]
        with np.load(root/f"r64_reference/r64_outputs/model_{seed}_math_only_lambda0.npz") as f:
            for name in ("enc.weight","enc.bias","math.weight","math.bias"):
                assert np.array_equal(w[name],f[name]), (seed,name)
        q=[r for r in predictions if r["split"]=="test"]
        legal=[r for r in q if r["kind"]=="valid"]
        joint=sum(ref[(seed,"joint_lambda1",r["id"])]["math_exact"] for r in legal)
        exact=sum(r["math_exact"] for r in legal)
        accepted=sum(r["frame_pred"] for r in legal)
        reject10=sum(not r["frame_pred"] for r in q if r["kind"]=="bad_10_unseen")
        byseed[seed]={"detached_math":exact,"joint_math":joint,"valid_accept":accepted,"unseen10_reject":reject10}
    results=json.loads((root/"r65_outputs/results.json").read_text())
    assert sum(z["detached_math"] for z in byseed.values())==149
    assert sum(z["joint_math"] for z in byseed.values())==165
    assert sum(z["valid_accept"] for z in byseed.values())==137
    assert sum(z["unseen10_reject"] for z in byseed.values())==188
    assert results["pass"] is False and sum(bool(v) for v in results["gates"].values())==7
    print("R65 read-only independent replay PASS: 1,344 outputs, 3 enc/math tensors exact, 40 SHA files")
    print(json.dumps(byseed,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    if len(sys.argv)!=2:
        sys.exit("usage: python verify_r65_bundle.py PATH_TO_UNPACKED_r65_work")
    main(sys.argv[1])
