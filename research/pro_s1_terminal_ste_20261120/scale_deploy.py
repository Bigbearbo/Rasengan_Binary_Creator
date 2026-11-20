"""Post-hoc quantization: match the fitted cell on its input cube, without task labels."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

inputs = np.array([(*entry, 1) for entry in itertools.product((0, 1), repeat=3)])
def table(w):
    return (inputs @ w >= 0).astype(int)

def deploy(w):
    source = table(w)
    for shift in range(17):
        integers = np.rint(w * (1 << shift)).astype(int)
        if np.array_equal(table(integers), source):
            return {"scale": 1 << shift, "weights": integers.tolist(), "max_abs": int(abs(integers).max())}
    return None

if __name__ == "__main__":
    measurements = json.loads(Path(sys.argv[1]).read_text())
    output = {}
    for method in ("straight", "clipped", "straight_detached"):
        output[method] = [{ "seed": t["seed"], "deployment": deploy(np.array(t["float"]["weights"]))}
                          for t in measurements["trials"][method]]
    print(json.dumps(output, indent=2))
