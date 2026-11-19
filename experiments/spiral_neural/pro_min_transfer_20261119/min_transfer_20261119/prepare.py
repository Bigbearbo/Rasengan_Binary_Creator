"""Import exact source files and record expected receiver outputs from locked PR133 ZIP."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np

BASE = Path(__file__).resolve().parent
EXPECTED = "c33c180362cec0e968fa704f3cf2dd55fbff5c36e348ad8e755b201c347cbed2"
PREFIX = "handfill_selector_20261118/"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    source = ap.parse_args().archive
    assert hashlib.sha256(source.read_bytes()).hexdigest() == EXPECTED
    dest = BASE / "inherited"
    dest.mkdir(exist_ok=False)
    with ZipFile(source) as z:
        assert z.testzip() is None
        names = ["hybrid_model.py", "handfilled_mux.npz", "data.json", "source_lock.json", "protocol.json"]
        names += [f"sources/receiver_seed{s}.npz" for s in (101,202,303)]
        names += [f"results/handfilled_frozen/seed{s}/checkpoints/step_0000.npz" for s in (101,202,303)]
        for name in names:
            path = dest / name
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(z.read(PREFIX + name))
        source_manifest = {}
        for seed in (101,202,303):
            source_manifest[str(seed)] = {}
            for panel in ("train","val","test","challenge"):
                name = f"results/source_cache/seed{seed}/{panel}.npz"
                with np.load(io.BytesIO(z.read(PREFIX+name)), allow_pickle=False) as cache:
                    source_manifest[str(seed)][panel] = {
                        k: hashlib.sha256(cache[k].tobytes()).hexdigest()
                        for k in ("words","pred_op","case_ids")
                    }
    (dest / "pr133_cache_hashes.json").write_text(json.dumps(source_manifest, indent=2)+"\n")

if __name__ == "__main__":
    main()
