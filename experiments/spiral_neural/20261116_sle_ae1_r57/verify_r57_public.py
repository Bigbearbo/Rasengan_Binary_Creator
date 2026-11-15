"""Read-only portable R57 evidence audit; stdlib only.
python verify_r57_public.py sle_ae1_r57_role_pair_holdout_20261116.zip
Does NOT run the neural model. Use archive's original runner for PyTorch/NumPy replay.
"""
import collections, hashlib, json, sys, zipfile
P = "r56_workspace/"
H = lambda b: hashlib.sha256(b).hexdigest()

def check(path):
    with zipfile.ZipFile(path) as z:
        get = lambda p: z.read(P + p)
        checks = json.loads(get("R57_PACKAGE_MANIFEST.json"))
        assert len(checks) >= 350
        for f, digest in checks.items():
            assert H(get(f)) == digest, f
        p = json.loads(get("r57_prereg.json"))
        r = json.loads(get("r57_outputs/results.json"))
        manifest = [json.loads(x) for x in get("r57_manifest.jsonl").splitlines()]
        rows = [json.loads(x) for x in get("r57_outputs/raw_results.jsonl").splitlines()]
        assert H(get("r57_manifest.jsonl")) == p["manifest_sha256"] == r["manifest_sha256"]
        assert H(get("r57_prereg.json")) == r["prereg_sha256"]
        assert H(get("r57_role_pair_frozen_holdout.py")) == p["runner_sha256"]
        assert H(get("r57_outputs/raw_results.jsonl")) == r["raw_sha256"]
        for f, digest in p["source_sha256"].items():
            assert H(get(f)) == digest, f
        def qbits(x):
            return ("01" + "010" + f"{x['r']:03b}" + "0"
                    + "".join(f"{x[k]:05b}0" for k in "abcd") + "111100")
        def truth(x):
            return "".join(f"{x[k]:05b}0" for k in "ab"[:x["r"]]) + "S"
        assert len(manifest) == 96 and len({x["Q"] for x in manifest}) == 96
        pairs = collections.defaultdict(list)
        for x in manifest:
            assert x["r"] in (1, 2)
            assert all(0 <= x[k] <= 29 for k in "abcd")
            assert len(x["Q"]) == 39 and x["Q"] == qbits(x)
            assert x["expected"] == truth(x)
            pairs[x["pair_id"]].append(x)
        assert len(pairs) == 48
        assert all(len(z) == 2
                   and {x["r"] for x in z} == {1, 2}
                   and len({(x["a"], x["b"], x["c"], x["d"]) for x in z}) == 1
                   for z in pairs.values())
        assert len(rows) == 1584
        seen = set()
        for x in rows:
            key = (x["arm"], x["seed"], x["Q"])
            assert key not in seen
            seen.add(key)
            assert x["arm"] in ("R52", "R55", "R56")
            assert x["seed"] in (101, 202, 303)
            assert x["exact"] == (x["actual"] == x["expected"])
            assert x["first"] == (x["actual"][:6] == x["expected"][:6])
            assert x["second_r2"] == ((x["actual"][6:12] == x["expected"][6:12])
                                       if x["r"] == 2 else None)
            assert set(x["actual"]) <= set("01S") and x["forwards"] >= 1
        for arm in ("R52", "R55", "R56"):
            for split, n in (("validation", 96), ("test", 192), ("retention", 240)):
                selected = [x for x in rows if x["arm"] == arm and x["split"] == split]
                assert len(selected) == n
                assert sum(x["exact"] for x in selected) == r["groups"][arm][split]["full"]
        assert r["joint_gate"] == "FAIL"
        assert sum(r["gates"].values()) == 4
        assert r["replay"]["torch"] == r["replay"]["numpy"] == 1584
        assert r["replay"]["sample_max_logit_abs_diff"] < 1e-5
        print("PASS R57: ", len(checks), "SHA, 1584 raw outputs; static audit only")

if __name__ == "__main__":
    check(sys.argv[1])
