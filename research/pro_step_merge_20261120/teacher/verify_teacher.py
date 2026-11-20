"""Run the actual T3 threshold matrices on submitted little-endian student traces."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

import numpy as np
from scipy.sparse import csr_matrix

BASE = Path(__file__).resolve().parent
SOURCES = {
    "teach_adder.py": "b1158e5346aad0ac1c0cd47af92a62703940d9d860caecc717e6452873b360b1",
    "teach_rule.py": "2d9287ccf4bce01d47061663d3ab5ce9fd1c17d9dade7e83aa03adcc9663e7a8",
}
for name, digest in SOURCES.items():
    assert hashlib.sha256((BASE / "upstream" / name).read_bytes()).hexdigest() == digest
sys.path.insert(0, str(BASE / "upstream"))
# Upstream imports a Windows-only module for its optional slow backend.
# The matrix builder, encoder, decoder and the fast backend used below do not call it.
sys.modules.setdefault("mult_ctrl", types.ModuleType("mult_ctrl"))
import teach_adder as ta
import teach_rule as tr


def matrix_digest(mats):
    return hashlib.sha256(b"".join(np.asarray(a, dtype="<i8").tobytes() for a in mats)).hexdigest()


class RuleTeacher:
    def __init__(self):
        self.net = tr.build(8)   # Identical to T3's published default: allow all positive strides.
        self.mats = self.net.mats()
        self.bound = ta.bound(self.mats)
        assert self.bound < 2**15 and len(self.net.rows) == 405
        w1, bias, w2 = self.mats
        # Row sums remain within signed 16-bit on any Boolean intermediate board.
        self.w1 = csr_matrix(w1.astype(np.int16))
        self.bias = bias.astype(np.int16)
        self.w2 = csr_matrix(w2.astype(np.int16))

    def grade(self, a, b, drafts, native=False):
        board = tr.encode(self.net, a, b, drafts)
        if native:
            board, rounds, done, _, bad = ta.trace(self.mats, board, [0], 12)
            assert done.all() and bad == 0
        else:
            board = board.astype(np.int16)
            done = np.zeros(len(a), dtype=bool)
            rounds = np.zeros(len(a), dtype=np.uint8)
            for _ in range(12):
                live = np.flatnonzero(~done)
                if not len(live):
                    break
                features = self.w1 @ np.ascontiguousarray(board[live].T) + self.bias[:, None]
                output = self.w2 @ (features >= 0).astype(np.int16)
                assert output.min() >= 0 and output.max() <= 1
                board[live] = output[:-1].T
                done[live] = output[-1] == 1
                rounds[live] += 1
            assert done.all()
        err, ok, first, fields, nfe = tr.read(self.net, board)
        assert (err + ok == 1).all() and (nfe == err).all()
        return ok, first, fields, rounds


def lookup_outputs(width, idx_value):
    """An exact reference cell only for control-test construction."""
    side = 1 << width
    return np.asarray([idx_value(a, b, c) for a in range(side) for b in range(side) for c in range(2)], dtype=np.int16)


def draft_from_cells(a, b, fine, coarse, a_bank=0, b_bank=0, model=None):
    """Autonomous local lookup and self-fed carry, with an optional independently decoded policy."""
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    rows = np.zeros((n, 8, 18), dtype=np.uint8)
    pos = part = carry = 0
    for t in range(9):
        if model is None:
            action = 0 if pos == 8 else 2
        else:
            r = 8 - pos
            g = bank_code(a_bank, b_bank, pos)
            action = 0 if r <= model["s"] else (2 if r >= model["k"] and model["table"][g] else 1)
        if not action:
            if pos != 8:
                raise ValueError("early policy STOP")
            break
        if pos + action > 8 or t == 8:
            raise ValueError("invalid read")
        if action == 2 and not (((a_bank >> pos) ^ (a_bank >> (pos + 1))) & 1 == 0 and ((b_bank >> pos) ^ (b_bank >> (pos + 1))) & 1 == 0):
            raise ValueError("policy crossed an actual bank boundary")
        side = 1 << action
        inp = (((a >> pos) % side) * side + ((b >> pos) % side)) * 2 + carry
        cell = fine if action == 1 else coarse
        value = cell[inp]
        part = part | ((value % side) << pos)
        pos += action
        carry = value // side
        rows[:, t, pos] = 1
        rows[:, t, 9:17] = (part[:, None] >> np.arange(8)) & 1
        rows[:, t, 17] = carry
    else:
        raise AssertionError("policy failed to submit")
    return rows[:, :t], (part | (carry << 8))


def bank_code(a_bank, b_bank, pos):
    # Return a 0..15 LUT index. Exact bit order is asserted against the original
    # controller implementation when joint traces are requested.
    return (8 * ((a_bank >> pos) & 1) + 4 * ((a_bank >> (pos + 1)) & 1)
            + 2 * ((b_bank >> pos) & 1) + ((b_bank >> (pos + 1)) & 1))


def control_cases(teacher):
    rng = np.random.default_rng(2026112011)
    ids = rng.choice(65536, 256, replace=False)
    a, b = ids // 256, ids % 256
    coarse = lookup_outputs(2, lambda x, y, c: x + y + c)
    fine = lookup_outputs(1, lambda x, y, c: x + y + c)
    rows, final = draft_from_cells(a, b, fine, coarse)
    assert (final == a + b).all()
    fixtures = {"valid": (rows.copy(), 0), "carry": (rows.copy(), 2), "sum": (rows.copy(), 3),
                "early_stop": (rows[:, :2].copy(), 3), "duplicate_position": (rows.copy(), 2)}
    fixtures["carry"][0][:, 1, 17] ^= 1
    fixtures["sum"][0][:, 2, 9] ^= 1
    fixtures["duplicate_position"][0][:, 1, 3] = 1
    results = {}
    for name, (draft, want) in fixtures.items():
        sparse = teacher.grade(a, b, draft)
        original = teacher.grade(a, b, draft, native=True)
        for x, y in zip(sparse, original):
            assert np.array_equal(x, y)
        ok, first, flags, rounds = sparse
        assert (first == want).all() and bool(ok.all()) == (want == 0)
        results[name] = dict(cases=len(a), accepted=int(ok.sum()), first_error=want,
                             flag_counts=flags.sum(0).astype(int).tolist(),
                             original_dense_equals_integer_sparse=True)
    return results


def runtime_cells(checkpoint):
    """Independently reconstruct both exported local boolean functions from integer weights."""
    def fine(a, b, c):
        row = checkpoint["fine"][a + 2*b + 4*c]
        return int(row[0] > 0) + 2 * int(row[1] > 0)

    def coarse(a, b, c):
        coeff = checkpoint["weights"]
        if checkpoint["hardware"] == "lut":
            row = coeff[a + 4*b + 16*c]
            return sum((1 << j) for j, w in enumerate(row) if w > 0)
        assert checkpoint["hardware"] == "linear"
        features = [a & 1, a >> 1, b & 1, b >> 1, c, 1]
        return max(0, min(7, sum(f*w for f, w in zip(features, coeff, strict=True))))
    return lookup_outputs(1, fine), lookup_outputs(2, coarse)


def grade_cases(teacher, ids, fine, coarse, a_bank=0, b_bank=0, model=None):
    accepted = 0
    all_final = 0
    errors = np.zeros(9, dtype=np.int64)
    flags = np.zeros(3, dtype=np.int64)
    positions = None
    for start in range(0, len(ids), 2048):
        v = ids[start:start+2048]
        a, b = v // 256, v % 256
        draft, final = draft_from_cells(a, b, fine, coarse, a_bank, b_bank, model)
        path = draft[0, :, :9].argmax(axis=1).tolist()
        assert positions in (None, path)
        positions = path
        ok, first, fld, rounds = teacher.grade(a, b, draft)
        if start == 0:
            # Use the original unedited fast backend also on each model's first few records.
            native = teacher.grade(a[:32], b[:32], draft[:32], native=True)
            for expected, actual in zip(native, (ok, first, fld, rounds), strict=True):
                assert np.array_equal(expected, actual[:32])
        all_final += int((final == (a+b)).sum())
        accepted += int(ok.sum())
        assert (ok <= (final == (a+b))).all()
        errors += np.bincount(first.astype(np.int64), minlength=9)
        flags += fld.sum(axis=0)
    return {"pairs":len(ids), "accepted_all_rows":accepted, "correct_final_sum":all_final,
            "student_cursor_after_writes":positions, "student_writes":len(positions),
            "first_error_histogram_0_means_pass": errors.tolist(),
            "position_sum_carry_flags": flags.tolist()}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--arithmetic", type=Path, default=BASE.parent / "arithmetic_results.json")
    cli.add_argument("--policy", type=Path, default=BASE.parent / "policy" / "result.json")
    cli.add_argument("--output", type=Path, default=BASE / "teacher_results.json")
    args = cli.parse_args()

    study = json.loads(args.arithmetic.read_text())
    policies = json.loads(args.policy.read_text())
    rule = RuleTeacher()
    ar = np.arange(65536)
    test = np.random.default_rng(2026112012).choice(65536, 512, replace=False)
    groups = {}
    for trl in study["trials"]:
        seed = trl["seed"]
        for size in sorted(trl["checkpoints"], key=int):
            for arm in ("self_linear","self_lut","teacher_linear","teacher_lut"):
                cp = trl["checkpoints"][size][arm]
                fine, coarse = runtime_cells(cp)
                signature = tuple(coarse.tolist())
                group = groups.setdefault(signature, {"fine":fine,"coarse":coarse,"refs":[],"full":False})
                group["refs"].append((seed,arm,int(size),cp["score"]["trace_exact"]))
                group["full"] |= size == "64"
        cp = trl["scrambled_linear"]
        fine, coarse = runtime_cells(cp)
        group = groups.setdefault(tuple(coarse.tolist()), {"fine":fine,"coarse":coarse,"refs":[],"full":False})
        group["refs"].append((seed,"rotated_self_linear",64,cp["score"]["trace_exact"]))
        group["full"] = True

    sys.path.insert(0, str(BASE.parent))
    import arithmetic as original_arithmetic
    from policy import stride as original_policy
    crosschecks = 0
    for pos in range(7):
        for a_bits in range(4):
            for b_bits in range(4):
                a_bank, b_bank = a_bits << pos, b_bits << pos
                assert bank_code(a_bank,b_bank,pos) == original_policy.encode(a_bank,b_bank,pos,8)
                crosschecks += 1
    for trailing_state in (7,8):
        for a_bank in range(256):
            for b_bank in (0,128,255):
                assert bank_code(a_bank,b_bank,trailing_state) == original_policy.encode(a_bank,b_bank,trailing_state,8)
                crosschecks += 1
    num_cell_checks = 0
    for trl in study["trials"]:
        all_cp = [cp[arm] for cp in trl["checkpoints"].values()
                  for arm in ("self_linear","teacher_linear","self_lut","teacher_lut")]
        for cp in [*all_cp,trl["scrambled_linear"]]:
            for width, local in enumerate(runtime_cells(cp),start=1):
                side = 1 << width
                a,b,c = np.indices((side,side,2)).reshape(3,-1)
                digit,carry = original_arithmetic.student_step(cp,width,a,b,c)
                assert np.array_equal(digit+(carry<<width),local)
                num_cell_checks += len(local)
    checked = []
    for _, group in sorted(groups.items()):
        full = group["full"]
        res = grade_cases(rule, ar if full else test, group["fine"], group["coarse"])
        if full:
            assert all(x[3] == res["accepted_all_rows"] for x in group["refs"])
        checked.append({"full":full,"models":group["refs"],"packed_context_table":group["coarse"].tolist(),"t3":res})

    # Join the actually exported EC policy with the actually trained student's direct cells.
    m = policies["trials"][0]["models"]["EC"]
    distinct = {json.dumps(t["models"]["EC"],sort_keys=True) for t in policies["trials"]}
    assert len(distinct) == 1
    fine, coarse = runtime_cells(study["trials"][0]["checkpoints"]["64"]["self_linear"])
    mixed = [dict(layout_a=l,layout_b=0,**grade_cases(rule, ar, fine, coarse, l, 0, m)) for l in (0,2,4)]
    assert [x["student_cursor_after_writes"] for x in mixed] == [[2,4,6,8],[1,2,4,6,8],[2,3,5,7,8]]
    assert all(x["accepted_all_rows"] == len(ar) for x in mixed)
    source_hash = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.arithmetic, args.policy)}
    report = {"interface_crosschecks":{"bank_codes":crosschecks,"student_local_input_outputs":num_cell_checks}, "teacher": {"sources_sha256":SOURCES, "matrices_sha256":matrix_digest(rule.mats),
                          "hidden_units":len(rule.net.rows),"board_bits":rule.net.nin,
                          "integer_bound":rule.bound,"rule":"published default D=1..8; lower columns first",
                          "backend":"T3 build, encode, and read unchanged; signed int16 sparse with proven bounds; independently checked against native float32 dense"},
              "student_inputs_sha256":source_hash, "controls":control_cases(rule),
              "checks":{"submitted_arithmetic_checkpoints":sum(len(g["refs"]) for g in groups.values()),
                        "distinct_coarse_truth_functions":len(groups),
                        "full_domain_functions":sum(g["full"] for g in groups.values()),
                        "remaining_functions_sampled":int(len(groups)-sum(g["full"] for g in groups.values())),
                        "sample_size":len(test), "sample_seed":2026112012},
              "arithmetic_by_function":checked, "joint_ec_models":len(policies["trials"]),
              "joint_ec_variants":len(distinct),"joint_fixed_layouts":mixed}
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"checks":report["checks"],"joint":mixed,"controls":report["controls"]}))

if __name__ == "__main__":
    main()
