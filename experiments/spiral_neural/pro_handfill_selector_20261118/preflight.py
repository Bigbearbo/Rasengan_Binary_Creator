"""Small train-fixture-only numerical checks, zero optimizer updates."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from hybrid_model import (ROOT,SEEDS,KEYS,load_source,decode,init_comparator,load_mux,
    mux_forward,loss_grads,hybrid_forward)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    target=ROOT/"preflight.json"
    if target.exists():
        raise FileExistsError(target)
    data=json.loads((ROOT/"data.json").read_text(encoding="utf-8"))
    rows=data["panels"]["train"][:16]
    raw=np.asarray([[int(c) for c in r["frame_bits"]] for r in rows],dtype=np.float64)
    targets=np.asarray([r["a"]>=r["b"] for r in rows],dtype=np.float64)
    source_checks=[]
    for seed in SEEDS:
        original_sha=sha(ROOT/"sources"/f"receiver_seed{seed}.npz")
        source=load_source(seed)
        original={k:v.copy() for k,v in source.items()}
        decoded=decode(source,raw)
        assert decoded["words"].shape==(16,14)
        assert all(np.array_equal(source[k],v) for k,v in original.items())
        assert original_sha==sha(ROOT/"sources"/f"receiver_seed{seed}.npz")
        source_checks.append({"seed":seed,"training_fixture_rows":16,"source_unchanged":True})
        if seed==101:
            fixture_words=decoded["words"]
    params=init_comparator("random_train",101)
    value,grads=loss_grads(params,fixture_words,targets)
    errors=[]
    eps=1e-5
    for key in KEYS:
        for index in np.ndindex(params[key].shape):
            old=float(params[key][index])
            params[key][index]=old+eps
            positive=loss_grads(params,fixture_words,targets)[0]
            params[key][index]=old-eps
            negative=loss_grads(params,fixture_words,targets)[0]
            params[key][index]=old
            errors.append(abs((positive-negative)/(2*eps)-grads[key][index]))
    assert max(errors)<1e-7
    mux=load_mux()
    primitive=np.asarray(list(itertools.product([0,1],repeat=3)),dtype=np.uint8)
    words=np.column_stack((np.repeat(primitive[:,:1],7,axis=1),np.repeat(primitive[:,1:2],7,axis=1)))
    copy=mux_forward(mux,words,primitive[:,2])
    expected=np.repeat(np.where(primitive[:,2],primitive[:,0],primitive[:,1])[:,None],7,axis=1)
    assert np.array_equal(copy["output_bits"],expected)
    exact=hybrid_forward(init_comparator("handfilled_frozen",101),mux,fixture_words)
    pred_a=fixture_words[:,:7]@np.asarray([64,32,16,8,4,2,1])
    pred_b=fixture_words[:,7:]@np.asarray([64,32,16,8,4,2,1])
    assert np.array_equal(exact["output_bits"]@np.asarray([64,32,16,8,4,2,1]),np.maximum(pred_a,pred_b))
    manifest=json.loads((ROOT/"source_manifest.json").read_text(encoding="utf-8"))
    assert all(sha(ROOT/item["path"])==item["sha256"] for item in manifest["copied"])
    result={"schema":"handfill-selector-preflight-v1","status":"PASS","created_utc":datetime.now(timezone.utc).isoformat(),
        "source_checks":source_checks,"gradient":{"parameters_checked":15,"fixture_rows":16,"epsilon":eps,
            "max_absolute_error":max(errors),"loss":value},"mux_all_primitive_bit_combinations":8,
        "exact_comparator_on_actual_decoded_train_fixture":16,"locked_source_copies_checked":len(manifest["copied"]),
        "verification_work":{"source_forward_rows":48,"source_forward_mac":48*1248,
            "selector_gradient_forward_rows":31*16,"selector_gradient_forward_mac":31*16*14,
            "primitive_mux_rows":8,"primitive_mux_mac":8*42,"exact_hybrid_rows":16,"exact_hybrid_mac":16*56},
        "experimental_training_updates":0,"verification_optimizer_updates":0,"test_inference_rows":0,"challenge_inference_rows":0}
    target.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))


if __name__=="__main__":
    main()
