#!/usr/bin/env python3
"""Independent shared-set probe: handwired v0 vs nanomath on nanomath's held-out DeepMind questions.
No training; no hidden task-specific prompt engineering. Strict source provenance retained.
"""
import os, sys, json, time, random, hashlib, collections, traceback
from pathlib import Path
import subprocess

os.environ["OPENBLAS_NUM_THREADS"]="1"
os.environ["OMP_NUM_THREADS"]="2"
import torch
from huggingface_hub import hf_hub_download, snapshot_download

BASE=Path(__file__).resolve().parent
OUT=BASE/"compare_results.json"
MODULES = [
    ("arithmetic__add_or_sub","加減"),
    ("arithmetic__mul","乘"),
    ("arithmetic__div","除"),
    ("arithmetic__mixed","混合"),
    ("numbers__gcd","gcd"),
    ("algebra__linear_1d","一元一次"),
]
LIMIT = int(os.environ.get("PEER_LIMIT","10"))
SEED = 20261122

def load_inputs():
    path=Path(hf_hub_download(repo_id="rekhi/nanomath", filename="eval.json", local_dir=str(BASE/"nano")))
    blob=path.read_bytes()
    raw=json.loads(blob.decode("utf-8"))
    items=[]
    for en,cn in MODULES:
        pool=raw[en]
        indexes=sorted(random.Random(f"{SEED}-{en}").sample(range(len(pool)),min(LIMIT,len(pool))))
        for i in indexes:
            row=pool[i]
            items.append({"id":f"{en}-{i}","module":cn,"deepmind_module":en,
                          "question":row["question"],"answer":str(row["answer"])})
    return items, hashlib.sha256(blob).hexdigest()

def normalized_equal(answer,gold):
    from fractions import Fraction
    try:
        return Fraction(answer.strip())==Fraction(gold.strip())
    except (ValueError,ZeroDivisionError,TypeError):
        return "".join(answer.split())=="".join(gold.split())

def score_pred(pred,gold):
    if pred is None: return "refuse"
    return "correct" if normalized_equal(str(pred),str(gold)) else "wrong"

def run_handwired(items):
    print("Downloading handwired v0 from Hugging Face",flush=True)
    path=Path(snapshot_download(repo_id="Bigbearbo/handwired-left-brain-1",
       revision="15750436b2842f7afd6cef7a9323113b04a9c2bd",
       local_dir=str(BASE/"hwleft")))
    sys.path.insert(0,str(path))
    import eval as hw
    hw.load()
    hw.install()
    start=time.perf_counter()
    rows=[]
    for d in items:
        try:
            item=hw.run([d])[0]
            rows.append({**d,"state":item["result"],"pred":item.get("why",""),
                "structured":item.get("en"),"reason":item.get("why","")})
        except Exception as e:
            rows.append({**d,"state":"error","reason":repr(e),"pred":None})
    return {"model":"handwired-public-v0","seconds":round(time.perf_counter()-start,3),"items":rows}

def run_nanomath(items):
    print("Downloading nanomath checkpoint and public source",flush=True)
    ck=Path(hf_hub_download(repo_id="rekhi/nanomath", filename="final.pt",local_dir=str(BASE/"nano")))
    src=BASE/"MathLLM"
    if not src.exists():
        subprocess.run(["git","clone","--depth","1","https://github.com/Rekhii/MathLLM.git",str(src)],
                       check=True,stdout=subprocess.DEVNULL)
    sys.path.insert(0,str(src))
    from mathllm.config import Config
    from mathllm.model import GPT
    from mathllm.tokenizer import CharTokenizer
    cfg=Config(device="cpu",compile=False,dtype="float32")
    torch.set_num_threads(2)
    tok=CharTokenizer()
    model=GPT(cfg).to(cfg.device)
    snapshot=torch.load(ck,map_location="cpu",weights_only=False)
    model.load_state_dict(snapshot["model"])
    model.eval()
    start=time.perf_counter()
    rows=[]
    for i,d in enumerate(items):
        try:
            ids=tok.encode(d["question"])+[tok.SEP]
            if len(ids)>=cfg.block_size:
                pred=None
                why="input exceeds 256-char context"
            else:
                with torch.inference_mode():
                    out=model.generate(torch.tensor([ids],dtype=torch.long),max_new_tokens=48,
                                       eos_id=tok.EOS,greedy=True)
                seq=out[0,len(ids):].tolist()
                hit_eos=tok.EOS in seq
                if hit_eos: seq=seq[:seq.index(tok.EOS)]
                pred="".join(tok.itos[k] for k in seq)
                why=("" if hit_eos else "missing EOS, hit 48-token limit")
            rows.append({**d,"state":score_pred(pred,d["answer"]) if pred is not None else "refuse",
                         "pred":pred,"reason":why})
        except Exception as e:
            rows.append({**d,"state":"error","pred":None,"reason":repr(e)})
        if (i+1)%10==0: print("nanomath progress:",i+1,"/",len(items),flush=True)
    return {"model":"nanomath-final-checkpoint","seconds":round(time.perf_counter()-start,3),
           "actual_params":sum(p.numel() for p in model.parameters()),"items":rows}

def summarize(rows):
    b=collections.defaultdict(lambda:collections.Counter())
    for d in rows:
        b[d["deepmind_module"]][d["state"]]+=1
        b["ALL"][d["state"]]+=1
    return {k:dict(v) for k,v in b.items()}

def main():
    print("Python",sys.version,"Torch",torch.__version__,flush=True)
    items, data_sha=load_inputs()
    print("heldout data sha256",data_sha,"selected",len(items),flush=True)
    print("SAMPLE_IDS",*[d["id"] for d in items],sep="\n",flush=True)
    h=run_handwired(items); n=run_nanomath(items)
    for m in (h,n):
        m["summary"]=summarize(m["items"])
        print("RESULT",m["model"],m["seconds"],m["summary"],flush=True)
        print("EXAMPLES",m["model"],
          [(x["id"],x["state"],x.get("pred"),x.get("reason","")) for x in m["items"][:15]],flush=True)
    out={"protocol":"shared nanomath held-out subset; greedy; 48 token cap; exact rational/string normalization",
         "source":"rekhi/nanomath eval.json; no items selected by expected outcomes",
         "seed":SEED,"per_module":LIMIT,"n":len(items),"sha256_eval_json":data_sha,
         "cases":items,"systems":[h,n]}
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False))
    print("WROTE",OUT,flush=True)

if __name__=="__main__":
    main()
