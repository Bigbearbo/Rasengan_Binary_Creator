"""Teacher-to-student edge-mask transfer on the audited serial adder."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

SEEDS = list(range(20261120, 20261136))
ARMS = ["A", "B", "S", "C", "F"]
ROOT = Path(__file__).resolve().parent
N = 65536


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def teacher(up):
    spec = importlib.util.spec_from_file_location("borrow_source", up/"run_borrow.py")
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    core, encode, decode = old.load_s1()
    w1, b1, w2 = core.mats()
    assert w1.shape == (19, 18)
    ports = np.stack([old.old_port(file, 19)[0] for file in (old.CARRY, old.TWO)])
    expanded = old.extend((w1,b1,w2), (core.c("A"), core.c("B")), ports, old.FIXED)
    incoming = expanded.incoming.toarray()[-1]
    outgoing = expanded.outgoing.toarray()[:, -1]
    assert np.flatnonzero(outgoing).tolist() == [18] and outgoing[18] == 1
    names = [None] * 18
    for group, (offset, width) in core.pos.items():
        for j in range(width):
            names[offset+j] = f"{group}{j}" if width > 1 else group
    names.append("borrow")
    packet = [{"role": names[i], "sign": int(np.sign(incoming[i]))} for i in np.flatnonzero(incoming)]
    ids = np.arange(N)
    a,b = ids//256, ids%256
    board = encode(a,b).astype(np.int16)
    snapshots, codes, truth = [], [], []
    shifts = 1 << np.arange(18, dtype=np.int32)
    for k in range(8):
        snapshots.append(board)
        codes.append(board @ shifts)
        truth.append((a % (2 << k)) < (b % (2 << k)))
        hidden = (board @ w1.T + b1 >= 0).astype(np.int16)
        out = hidden @ w2.T
        assert np.all(out[:,-1] == int(k==7))
        assert np.all((out == 0) | (out == 1))
        board = out[:,:-1].astype(np.int16)
    assert np.array_equal(decode(board),a+b)
    return names, packet, np.array(snapshots,dtype=np.uint8), np.array(codes), np.array(truth)


def arrange(names, packet, ids, boards):
    # The student receives labels/roles in an independently permuted physical layout.
    # Training accumulation then follows canonical order across those physical addresses.
    perms = [np.random.default_rng(np.random.SeedSequence([s,901])).permutation(19) for s in SEEDS]
    blind = []
    train_boards = []
    permissions = []
    direction = []
    for i,s in enumerate(SEEDS):
        rng = np.random.default_rng(np.random.SeedSequence([s,902]))
        blind.append([f"A{rng.integers(8)}",f"B{rng.integers(8)}","borrow"])
        layout = [names[j] for j in perms[i]]
        actual = {name:slot for slot,name in enumerate(layout)}
        # Build first from physical space, then look the roles up in that space.
        x = np.zeros((8,64,19), dtype=np.float64)
        for c,name in enumerate(names[:-1]):
            x[:,:,actual[name]] = boards[:,ids[i],c]
        roles = [actual[n] for n in names]
        train_boards.append(x[:,:,roles[:-1]])
        mask_group = []
        sign_group = []
        for arm in ARMS:
            informed = arm in ("B","S","F")
            hints = [entry["role"] for entry in packet] if informed else blind[-1]
            mask = np.zeros(19,dtype=bool)
            for name in (names if arm=="A" else hints):
                mask[actual[name]] = True
            sign = np.zeros(19)
            if arm=="S":
                for edge in packet:
                    sign[actual[edge["role"]]] = edge["sign"]
            mask_group.append(np.append(mask[roles], True))
            sign_group.append(np.append(sign[roles], 0))
        permissions.extend(mask_group)
        direction.extend(sign_group)
    # Case cube is expanded only on the data side; each arm retains its own weights.
    train = np.repeat(np.stack(train_boards,axis=1),len(ARMS),axis=1)
    return perms, blind, train, np.array(permissions), np.array(direction)


def update_gradient(w,x,target):
    state = np.zeros_like(target)
    xs = []
    # Broadcast the per-model weights across its 64 training cases.
    for xt in x:
        pre = np.zeros_like(state)
        for j in range(18):
            pre += xt[:,:,j] * w[:,j,None]
        pre += state * w[:,18,None]
        pre += w[:,19,None]
        xs.append(np.concatenate((xt,state[:,:,None],np.ones((*state.shape,1))),axis=2))
        state = (pre >= 0).astype(float)
    error = state-target
    grad = np.zeros_like(w)
    for vector in reversed(xs):
        grad += (error[:,:,None] * vector).mean(axis=1)
        error = error * w[:,18,None]
    return grad


def score(w,codes,gold,examples):
    # All 2^18 possible old board states. Addition order matches the trainer exactly.
    lookup = np.array([0.])
    for edge in w[:18]:
        lookup = np.concatenate([lookup,lookup+edge])
    q = np.zeros(N)
    matched = np.ones(N,dtype=bool)
    for board,y in zip(codes,gold):
        q = (lookup[board] + q*w[18] + w[19] >= 0)
        matched &= q==y
    end = q==gold[-1]
    return {"train_endpoint": int(end[examples].sum()),
            "full_endpoint":int(end.sum()),"full_trace":int(matched.sum())}


def run(up, output, rawfile):
    names,packet,boards,codes,gold = teacher(up)
    old = json.loads((up/"pr137_results.json").read_text())
    ids = np.stack([np.random.default_rng(s).choice(N,64,replace=False) for s in SEEDS])
    assert np.array_equal(ids,old["ids_by_seed"])
    perms,blind,x,allowed,direction = arrange(names,packet,ids,boards)
    target = np.repeat(gold[-1][ids],len(ARMS),axis=0).astype(float)
    w = np.zeros((len(target),20))
    updates = np.zeros(len(w),int)
    early_updates = np.zeros(len(w),int)
    finite = np.ones(len(w),bool)
    trials = {arm:[] for arm in ARMS}
    rolls = {s:{} for s in SEEDS}
    fixed = np.array([arm=="F" for s in SEEDS for arm in ARMS])
    for step in range(257):
        if step in (0,64,256):
            for i,par in enumerate(w):
                arm = ARMS[i%len(ARMS)]
                j = i//len(ARMS)
                scores=score(par,codes,gold,ids[j]) if finite[i] else {}
                checkpoint={"weights_canonical":par.tolist() if finite[i] else None,
                            "actual_updates":int(updates[i]),"finite":bool(finite[i]),**scores}
                rolls[SEEDS[j]].setdefault(arm,{})[str(step)] = checkpoint
        if step==256:
            break
        grad = update_gradient(w,x,target)
        mask = allowed if step < 64 else (allowed | (~fixed[:,None]))
        next_w = w - 0.25 * np.where(mask,grad,0)
        if step < 64:
            next_w = np.where(direction*next_w < 0,0.,next_w)
        finite &= np.all(np.isfinite(next_w),axis=1)
        changed = finite & (next_w!=w).any(axis=1)
        updates += changed
        if step < 64:
            early_updates += changed
        w = np.where(finite[:,None],next_w,0)
    for i,s in enumerate(SEEDS):
        layout=[names[j] for j in perms[i]]
        for arm in ARMS:
            ckpt=rolls[s][arm]
            trials[arm].append({"seed":s, "checkpoints":ckpt})
            if arm == "F":
                controls=old["trials"]["straight"][i]["float"]
                assert [ckpt["256"]["weights_canonical"][k] for k in (0,8,18,19)] == controls["weights"]
                assert ckpt["256"]["full_trace"] == controls["sequence_correct"]
                assert ckpt["256"]["full_endpoint"] == controls["endpoint_correct"]
                assert ckpt["256"]["train_endpoint"] == controls["train_endpoint_correct_of_64"]
    metadata = [{"seed":s,"permuted_physical_roles":[names[k] for k in perms[j]],"blind_roles":blind[j],
                 "training_ids":ids[j].tolist()} for j,s in enumerate(SEEDS)]
    summary = {}
    for arm,records in trials.items():
        summary[arm] = {}
        for t in ("0","64","256"):
            per = [r["checkpoints"][t] for r in records]
            trace = [c.get("full_trace",0) for c in per]
            ends = [c.get("full_endpoint",0) for c in per]
            summary[arm][t]={"perfect_trace":sum(v==N for v in trace),
              "at_least_95_trace":sum(v*100>=N*95 for v in trace),
              "perfect_endpoint":sum(v==N for v in ends), "median_trace":float(np.median(trace)),
              "min_trace":min(trace),"max_trace":max(trace),
              "perfect_train":sum(c.get("train_endpoint")==64 for c in per),
              "nonfinite":sum(not c["finite"] for c in per)}
    data = np.stack([np.arange(N)//256,np.arange(N)%256,np.packbits(gold.T,axis=1,bitorder="little")[:,0]],axis=1)
    rawfile.write_bytes(data.astype(np.uint8).tobytes())
    result={"training_labels":"only A<B terminal", "seeds":SEEDS,
            "semantic_roles":names+["bias"],"unsigned_packet":[e["role"] for e in packet],
            "signed_packet":packet,"role_alignment":"mapped by supplied role names, physical addresses permuted",
            "reference":{"sum_9bit":N,"stop_schedule":N,"teacher_matched_F_all_four_weights":16,
                         "teacher_readout":"one private borrow wire; no student feedback to frozen S1"},
            "cost":{"training_batches_per_seed_per_arm":256,"training_cases_per_batch":64,
                    "hard_steps_per_case":8,"base_units":19,"appended_unit":1,
                    "early_and_final_free_counts_including_bias":{"A":[20,20],"B":[4,20],"S":[4,20],"C":[4,20],"F":[4,4]},
                    "notes":"The dense NumPy implementation uses 19 data multiplications plus one bias per example-step in all arms. Each sample proceeds for 8 rounds. No sparse wall-clock comparison. Per-condition effective nonzero and permitted weights differ."},
            "files_sha256":{p.name:digest(p) for p in [*sorted(up.glob("*.py")),*sorted(up.glob("*.json")),
                ROOT/"protocol.md", Path(__file__),rawfile]},"numpy_version":np.__version__,
            "pair_metadata":metadata,"summary":summary,"trials":trials}
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({a:v["256"] for a,v in summary.items()},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream",type=Path,default=ROOT/"upstream")
    parser.add_argument("--out",type=Path,default=ROOT/"results.json")
    parser.add_argument("--raw",type=Path,default=ROOT/"raw_internal.bin")
    args=parser.parse_args()
    run(args.upstream,args.out,args.raw)
