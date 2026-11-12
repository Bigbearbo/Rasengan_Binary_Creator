"""Hash the original selected inputs without loading or executing old models."""
import argparse
import hashlib
import json
from pathlib import Path

from diagnose import input_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    results = {}
    for name, path in input_paths(args.workspace_root, manifest["protocol"]).items():
        data = path.read_bytes()
        current = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        assert current == manifest["files"][name], name
        results[name] = current
    assert len(results) == 25
    result = {"status": "PASS", "original_input_count": len(results),
              "all_match_frozen_inputs": True, "files": results,
              "model_forward_calls": 0, "optimizer_calls": 0}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key != "files"}))


if __name__ == "__main__":
    main()
