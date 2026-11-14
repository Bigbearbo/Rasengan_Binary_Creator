"""Recreate R19's fixed 168-case native-01 manifest from frozen R18 manifest.

Usage:
python gen_manifest.py ../r18/experiment/manifest.jsonl > manifest.jsonl
sha256sum manifest.jsonl
Expected SHA256: 972265d5f851727f3ce181b032032986374932e3bd8671f12b79722325b53edc

No neural forward. Source R18 PR #67; this standalone output code matches
the already frozen and executed R19 case list and does not create new cases.
"""
import json
import hashlib
import sys

def word(n):
    assert isinstance(n, int) and 0 <= n <= 29
    return f"{n:05b}0"

def question(r, a, b, c, d):
    assert r in (1, 2)
    s = "01" + "010" + f"{r:03b}" + "0"
    s += "".join(word(n) for n in (a, b, c, d))
    s += "111100"
    assert len(s) == 39
    return s

def answer(r, a, b):
    return word(a) + (word(b) if r == 2 else "") + "S"

def fixed_cases(previous):
    rows = [dict(x) for x in previous if x["split"] in ("seen_baseline", "taught_high")]

    def add(split, r, a, b, c, d):
        rows.append({"split": split, "r": r, "a": a, "b": b,
                     "c": c, "d": d, "Q": question(r, a, b, c, d),
                     "expected": answer(r, a, b)})

    for a in range(4):
        for c, d in ((1, 2), (2, 1)):
            add("val_b24", 2, a, 24, c, d)
    for a in range(4):
        for b in (6, 7, 10, 11, 12):
            add("test_mid_b", 2, a, b, 2, 3)
    for a in range(4):
        for b in (24, 25, 26, 27, 28):
            add("test_high_b", 2, a, b, 2, 3)
    for a in (20, 21, 22, 23):
        for b in (24, 25, 26, 27, 28):
            add("test_joint_ab", 2, a, b, 1, 2)
    for a in range(4):
        for b in (24, 25, 26, 27, 28):
            add("test_r1_stop", 1, a, b, 2, 3)

    assert len(rows) == 168
    assert len({r["Q"] for r in rows}) == 168
    for r in rows:
        assert r["Q"] == question(r["r"], r["a"], r["b"], r["c"], r["d"])
        assert r["expected"] == answer(r["r"], r["a"], r["b"])
    return rows

def main():
    assert len(sys.argv) == 2, "specify frozen R18 manifest.jsonl file"
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        previous = [json.loads(x) for x in f if x.strip()]
    rows = fixed_cases(previous)
    payload = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert digest == "972265d5f851727f3ce181b032032986374932e3bd8671f12b79722325b53edc", digest
    sys.stdout.write(payload)

if __name__ == "__main__":
    main()
